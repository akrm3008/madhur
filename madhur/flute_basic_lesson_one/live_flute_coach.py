"""
Live Flute Coach — Gemini Live API, real-time video + audio.

Gemini receives a continuous stream of both webcam frames and mic audio
simultaneously via the Live API and responds with SPOKEN AUDIO feedback
played back in the Gradio UI automatically.

Run:
  python live_flute_coach.py --lesson 1 --mode webcam
  python live_flute_coach.py --lesson 2 --mode screen
"""

import asyncio
import io
import queue
import threading
import time
import wave
import argparse
import os
import sys

import cv2
import numpy as np
import gradio as gr
from google import genai
from google.genai import types

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    GEMINI_API_KEY, GEMINI_MODEL_LIVE,
    FRAME_INTERVAL_SEC, JPEG_QUALITY,
    SCREEN_MONITOR_INDEX, AUDIO_SAMPLE_RATE, LESSONS,
)
from prompts import get_live_system_prompt


# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

GEMINI_AUDIO_OUTPUT_RATE = 24000   # Hz — Gemini Live output is always 24kHz PCM


# ══════════════════════════════════════════════════════════════════════════════
# Utilities
# ══════════════════════════════════════════════════════════════════════════════

def encode_jpeg(frame_bgr: np.ndarray, quality: int = JPEG_QUALITY) -> bytes:
    _, buf = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes()


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = GEMINI_AUDIO_OUTPUT_RATE) -> bytes:
    """Wrap raw signed 16-bit PCM bytes in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)          # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# Screen capture — used in screen mode only
# ══════════════════════════════════════════════════════════════════════════════

class ScreenCapture:
    """Continuously grabs the primary monitor at ~10fps using mss."""

    def __init__(self, monitor_index: int = SCREEN_MONITOR_INDEX):
        self._monitor_index = monitor_index
        self._frame = None
        self._lock  = threading.Lock()
        self._stop  = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[self._monitor_index]
                while not self._stop.is_set():
                    shot = sct.grab(monitor)
                    bgr  = cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)
                    h, w = bgr.shape[:2]
                    if w > 1280:
                        bgr = cv2.resize(bgr, (1280, int(h * 1280 / w)))
                    with self._lock:
                        self._frame = bgr
                    time.sleep(0.1)
        except ImportError:
            print("mss not installed — pip install mss")

    def get_frame(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def stop(self):
        self._stop.set()


# ══════════════════════════════════════════════════════════════════════════════
# Live Stream Coach — Gemini Live API
# ══════════════════════════════════════════════════════════════════════════════

class LiveStreamCoach:
    """
    Maintains a persistent Gemini Live API WebSocket session.

    Streams concurrently:
      - Video frames  (from webcam or screen capture)
      - Mic audio     (raw 16kHz PCM, 100ms chunks — continuous, not broken)

    Gemini responds with SPOKEN AUDIO feedback.
    Each complete spoken response is queued as (sample_rate, np.ndarray)
    and played back in the Gradio UI automatically.
    """

    NUDGE_EVERY_N_FRAMES = 3

    def __init__(self, lesson_num: str, model: str = GEMINI_MODEL_LIVE):
        self.client        = genai.Client(api_key=GEMINI_API_KEY)
        self.model         = model
        self.lesson_num    = lesson_num
        self.system_prompt = get_live_system_prompt(lesson_num)
        self._q: queue.Queue = queue.Queue()
        self._running = False
        self._frame_getter = None

    def start(self, frame_getter):
        """Start the async streaming loop in a daemon thread."""
        self._running      = True
        self._frame_getter = frame_getter
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._running = False

    def get_latest_audio(self):
        """
        Non-blocking. Returns (sample_rate, np.ndarray) for gr.Audio, or None.
        """
        try:
            return self._q.get_nowait()
        except queue.Empty:
            return None

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._stream())

    async def _stream(self):
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=self.system_prompt)]
            ),
        )
        try:
            async with self.client.aio.live.connect(
                model=self.model, config=config
            ) as session:
                await asyncio.gather(
                    self._send_video(session),
                    self._send_audio(session),
                    self._receive(session),
                )
        except Exception as e:
            print(f"[Session error: {e}]")

    async def _send_video(self, session):
        """
        Send a video frame every FRAME_INTERVAL_SEC.
        Every NUDGE_EVERY_N_FRAMES frames, send a text turn asking Gemini
        to give the student spoken feedback based on what it has seen and heard.
        """
        frame_count = 0
        while self._running:
            frame = self._frame_getter()
            if frame is not None:
                jpeg = encode_jpeg(frame, quality=70)
                await session.send_realtime_input(
                    video=types.Blob(data=jpeg, mime_type="image/jpeg")
                )
                frame_count += 1

                if frame_count % self.NUDGE_EVERY_N_FRAMES == 0:
                    await session.send_client_content(
                        turns=types.Content(
                            role="user",
                            parts=[types.Part(
                                text="Based on the video and audio you have received, "
                                     "give the student spoken feedback now."
                            )]
                        ),
                        turn_complete=True,
                    )

            await asyncio.sleep(FRAME_INTERVAL_SEC)

    async def _send_audio(self, session):
        """
        Stream raw mic audio to Gemini continuously in 100ms PCM chunks.
        Format: mono, 16kHz, 16-bit signed PCM little-endian.
        """
        try:
            import sounddevice as sd
            CHUNK = int(AUDIO_SAMPLE_RATE * 0.1)   # 100ms = 1600 samples
            loop  = asyncio.get_event_loop()

            def callback(indata, frames, time_info, status):
                pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
                asyncio.run_coroutine_threadsafe(
                    session.send_realtime_input(
                        audio=types.Blob(data=pcm,
                                         mime_type=f"audio/pcm;rate={AUDIO_SAMPLE_RATE}")
                    ),
                    loop,
                )

            with sd.InputStream(samplerate=AUDIO_SAMPLE_RATE, channels=1,
                                 dtype='float32', blocksize=CHUNK, callback=callback):
                while self._running:
                    await asyncio.sleep(0.1)

        except ImportError:
            pass   # sounddevice not installed — video-only mode
        except Exception as e:
            print(f"[Mic error: {e}]")

    async def _receive(self, session):
        """
        Collect spoken audio chunks from Gemini.
        Accumulates PCM bytes until turn_complete, then queues the full
        response as (sample_rate, np.ndarray) for the Gradio audio player.
        """
        audio_buf = bytearray()
        async for msg in session.receive():
            if msg.data:
                audio_buf.extend(msg.data)
            if msg.server_content and msg.server_content.turn_complete:
                if audio_buf:
                    arr = np.frombuffer(bytes(audio_buf), dtype=np.int16)
                    self._q.put((GEMINI_AUDIO_OUTPUT_RATE, arr))
                    audio_buf = bytearray()
            if not self._running:
                break


# ══════════════════════════════════════════════════════════════════════════════
# Gradio App
# ══════════════════════════════════════════════════════════════════════════════

def build_gradio_app(capture_mode: str = "webcam"):
    """
    capture_mode : "webcam"  — browser camera (no macOS permission issues)
                   "screen"  — mss screen capture
    """
    lesson_choices = [
        f"Lesson {k} — {v['title'].split('—')[1].strip()}"
        for k, v in LESSONS.items()
    ]

    # ── Shared state ──────────────────────────────────────────────────────────
    _state = {
        "coach":        None,
        "latest_frame": None,
        "frame_lock":   threading.Lock(),
        "screen":       None,
        "running":      False,
    }

    def extract_lesson_num(choice: str) -> str:
        return choice.split("—")[0].strip().split()[-1]

    def get_latest_frame_bgr():
        with _state["frame_lock"]:
            f = _state["latest_frame"]
        if f is None:
            return None
        return cv2.cvtColor(f, cv2.COLOR_RGB2BGR) if capture_mode == "webcam" else f

    # ── Session control ───────────────────────────────────────────────────────

    def start_session(lesson_choice):
        lesson_num = extract_lesson_num(lesson_choice)

        if _state["coach"]:
            _state["coach"].stop()
        if _state["screen"]:
            _state["screen"].stop()

        if capture_mode == "screen":
            _state["screen"] = ScreenCapture()

        coach = LiveStreamCoach(lesson_num)
        coach.start(get_latest_frame_bgr)
        _state["coach"]   = coach
        _state["running"] = True

        lesson_info = LESSONS[lesson_num]
        return f"✅ Live session started — Lesson {lesson_num}", lesson_info["description"]

    def stop_session():
        _state["running"] = False
        if _state["coach"]:
            _state["coach"].stop()
            _state["coach"] = None
        if _state["screen"]:
            _state["screen"].stop()
            _state["screen"] = None
        return "Session stopped."

    # ── Frame intake (webcam mode) ────────────────────────────────────────────

    def store_webcam_frame(frame_rgb):
        if frame_rgb is not None:
            with _state["frame_lock"]:
                _state["latest_frame"] = frame_rgb

    # ── Audio feedback polling (timer) ────────────────────────────────────────

    def poll_feedback():
        """
        Called by Gradio timer every 0.5s.
        Returns (sample_rate, np.ndarray) for gr.Audio autoplay, or gr.update()
        if no new feedback is ready.
        """
        if not _state["running"] or not _state["coach"]:
            return gr.update()

        result = _state["coach"].get_latest_audio()
        if result is None:
            return gr.update()

        return result   # (GEMINI_AUDIO_OUTPUT_RATE, np.ndarray) → gr.Audio autoplays

    # ── Layout ────────────────────────────────────────────────────────────────
    with gr.Blocks(title="🎵 Live Bansuri Coach") as app:

        gr.Markdown(
            f"# 🎵 Live Bansuri Coach\n"
            f"**Gemini Live** `{GEMINI_MODEL_LIVE}`  |  Mode: `{capture_mode}`  |  "
            f"Video + Audio in → Spoken feedback out"
        )

        with gr.Row():
            lesson_selector = gr.Dropdown(
                choices=lesson_choices, value=lesson_choices[0],
                label="Select Lesson", scale=3,
            )
            start_btn = gr.Button("▶ Start", variant="primary", scale=1)
            stop_btn  = gr.Button("⏹ Stop",  variant="stop",    scale=1)

        with gr.Row():
            session_status = gr.Textbox(label="Status",      interactive=False, scale=2)
            lesson_desc    = gr.Textbox(label="Lesson Goal", interactive=False, scale=4)

        with gr.Row():
            with gr.Column(scale=3):
                if capture_mode == "webcam":
                    webcam_in = gr.Image(
                        sources=["webcam"],
                        streaming=True,
                        type="numpy",
                        label="Your Camera — allow access in browser",
                        height=420,
                    )
                else:
                    screen_out = gr.Image(
                        label="Screen Capture", type="numpy", height=420
                    )

            with gr.Column(scale=2):
                coach_audio = gr.Audio(
                    label="🎵 Coach Feedback",
                    autoplay=True,
                    interactive=False,
                )
                gr.Markdown(
                    "_Gemini will speak feedback every few seconds. "
                    "Make sure your speakers or headphones are on._"
                )

        # ── Wiring ────────────────────────────────────────────────────────────

        start_btn.click(
            fn=start_session,
            inputs=[lesson_selector],
            outputs=[session_status, lesson_desc],
        )
        stop_btn.click(fn=stop_session, outputs=[session_status])

        if capture_mode == "webcam":
            webcam_in.stream(
                fn=store_webcam_frame,
                inputs=[webcam_in],
                outputs=[],
                stream_every=0.5,
            )
        else:
            def refresh_screen():
                cap = _state.get("screen")
                if cap is None:
                    return None
                frame = cap.get_frame()
                if frame is None:
                    return None
                with _state["frame_lock"]:
                    _state["latest_frame"] = frame
                return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            screen_timer = gr.Timer(value=0.5)
            screen_timer.tick(fn=refresh_screen, outputs=[screen_out])

        # Timer polls coach queue — returns audio to gr.Audio which autoplays
        feedback_timer = gr.Timer(value=0.5)
        feedback_timer.tick(fn=poll_feedback, outputs=[coach_audio])

    return app


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Bansuri Coach")
    parser.add_argument("--lesson", default="1", choices=["1", "2"])
    parser.add_argument("--mode",   default="webcam", choices=["webcam", "screen"])
    parser.add_argument("--port",   type=int, default=7860)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Bansuri Coach — Lesson {args.lesson}")
    print(f"  Capture : {args.mode}")
    print(f"  Model   : {GEMINI_MODEL_LIVE}")
    print(f"  Input   : video frames + continuous mic audio")
    print(f"  Output  : spoken audio feedback (autoplay)")
    print(f"{'='*60}\n")

    app = build_gradio_app(capture_mode=args.mode)
    app.launch(
        server_port=args.port,
        share=False,
        inbrowser=True,
        theme=gr.themes.Soft(),
    )
