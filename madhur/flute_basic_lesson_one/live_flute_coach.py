"""
Live Flute Coach — Gemini Live API, real-time video + audio.

UX flow:
  - Click the webcam button to start (it IS the start button)
  - Gemini speaks a short intro explaining the cycle
  - "🎵 Play now — Xs remaining" → student plays for PLAY_DURATION_SEC
  - "⏳ Analyzing…"              → nudge sent, Gemini generating audio
  - "🔊 Feedback playing"        → spoken feedback plays automatically
  - cycle repeats until webcam is stopped

Run:
  python live_flute_coach.py --lesson 1 --mode webcam
  python live_flute_coach.py --lesson 2 --mode screen
"""

import asyncio
import queue
import threading
import time
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
    SCREEN_MONITOR_INDEX, AUDIO_SAMPLE_RATE,
    PLAY_DURATION_SEC, LESSONS,
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


# ══════════════════════════════════════════════════════════════════════════════
# Screen capture — used in screen mode only
# ══════════════════════════════════════════════════════════════════════════════

class ScreenCapture:
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
    Uses one short-lived Gemini Live session per cycle to avoid keepalive
    timeout issues with long-running WebSocket connections.

    Cycle:
      intro    — fresh session: Gemini greets student, explains cycle
      play     — fresh session: stream video+audio for PLAY_DURATION_SEC
      analyzing— nudge sent within same session
      feedback — audio queued; session closes; sleep until audio done
      → repeat play/analyzing/feedback
    """

    def __init__(self, lesson_num: str, model: str = GEMINI_MODEL_LIVE):
        self.client        = genai.Client(api_key=GEMINI_API_KEY)
        self.model         = model
        self.lesson_num    = lesson_num
        self.system_prompt = get_live_system_prompt(lesson_num)
        self._q: queue.Queue = queue.Queue()
        self._running        = False
        self._frame_getter   = None
        self._phase          = "idle"
        self._phase_start    = 0.0

    def start(self, frame_getter):
        self._running      = True
        self._frame_getter = frame_getter
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._running = False

    def get_status(self) -> dict:
        return {
            "phase":   self._phase,
            "elapsed": time.time() - self._phase_start,
        }

    def get_latest_audio(self):
        try:
            return self._q.get_nowait()
        except queue.Empty:
            return None

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._main_loop())

    # ── Session config (reused for every session) ──────────────────────────────

    def _make_config(self):
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=self.system_prompt)]
            ),
        )

    # ── Single-session helpers ─────────────────────────────────────────────────

    async def _collect_audio_response(self, session) -> float:
        """
        Read messages from session until turn_complete, queue the audio.
        Returns duration in seconds (0 if no audio).
        """
        audio_buf = bytearray()
        async for msg in session.receive():
            if msg.data:
                audio_buf.extend(msg.data)
            sc = getattr(msg, "server_content", None)
            if sc and getattr(sc, "turn_complete", False):
                break
        if audio_buf:
            arr = np.frombuffer(bytes(audio_buf), dtype=np.int16)
            dur = len(arr) / GEMINI_AUDIO_OUTPUT_RATE
            print(f"[Coach] Queuing audio: {dur:.1f}s")
            self._phase       = "feedback"
            self._phase_start = time.time()
            self._q.put((GEMINI_AUDIO_OUTPUT_RATE, arr))
            return dur
        return 0.0

    async def _stream_mic_to_session(self, session):
        """Drain a thread-safe PCM queue and send to session."""
        while self._running:
            if not self._pcm_queue.empty():
                pcm = self._pcm_queue.get_nowait()
                await session.send_realtime_input(
                    audio=types.Blob(data=pcm,
                                     mime_type=f"audio/pcm;rate={AUDIO_SAMPLE_RATE}")
                )
            else:
                await asyncio.sleep(0.02)

    # ── Main loop: one session per cycle ──────────────────────────────────────

    async def _main_loop(self):
        # Shared queue for mic PCM — filled by sounddevice callback
        self._pcm_queue: queue.Queue = queue.Queue(maxsize=50)

        # Start mic capture in background (fills _pcm_queue)
        mic_thread = threading.Thread(target=self._mic_capture, daemon=True)
        mic_thread.start()

        try:
            # ── Intro session ─────────────────────────────────────────────────
            self._phase = "intro"
            self._phase_start = time.time()
            print("[Coach] Intro session…")
            try:
                async with self.client.aio.live.connect(
                    model=self.model, config=self._make_config()
                ) as session:
                    await session.send_client_content(
                        turns=types.Content(
                            role="user",
                            parts=[types.Part(
                                text=f"Greet the student warmly and tell them: play the bansuri "
                                     f"for {PLAY_DURATION_SEC} seconds, then you will give spoken "
                                     f"feedback, and the cycle repeats. Keep it to 2 sentences, "
                                     f"then say 'Ready? Begin!'"
                            )]
                        ),
                        turn_complete=True,
                    )
                    intro_dur = await self._collect_audio_response(session)
            except Exception as e:
                print(f"[Coach] Intro error: {e}")
                intro_dur = 0.0

            # Wait for intro audio to finish playing
            if intro_dur > 0:
                await asyncio.sleep(intro_dur + 1.0)

            # ── Feedback cycles ───────────────────────────────────────────────
            while self._running:
                self._phase       = "play"
                self._phase_start = time.time()
                print(f"[Coach] Play session — student plays for {PLAY_DURATION_SEC}s…")

                try:
                    async with self.client.aio.live.connect(
                        model=self.model, config=self._make_config()
                    ) as session:
                        # Stream video + mic audio for PLAY_DURATION_SEC
                        deadline = time.time() + PLAY_DURATION_SEC
                        mic_task = asyncio.create_task(
                            self._stream_mic_to_session(session)
                        )
                        while time.time() < deadline and self._running:
                            frame = self._frame_getter()
                            if frame is not None:
                                jpeg = encode_jpeg(frame, quality=70)
                                await session.send_realtime_input(
                                    video=types.Blob(data=jpeg, mime_type="image/jpeg")
                                )
                            await asyncio.sleep(FRAME_INTERVAL_SEC)
                        mic_task.cancel()

                        # Nudge Gemini for feedback
                        self._phase       = "analyzing"
                        self._phase_start = time.time()
                        await session.send_client_content(
                            turns=types.Content(
                                role="user",
                                parts=[types.Part(
                                    text=f"The student just played for {PLAY_DURATION_SEC} "
                                         "seconds. Based on what you saw and heard, "
                                         "speak feedback now."
                                )]
                            ),
                            turn_complete=True,
                        )

                        # Collect audio response (session closes cleanly after)
                        cycle_dur = await self._collect_audio_response(session)

                except Exception as e:
                    print(f"[Coach] Cycle error: {e}")
                    cycle_dur = 0.0

                # Wait for feedback audio to finish before next cycle
                if cycle_dur > 0:
                    await asyncio.sleep(cycle_dur + 1.0)

        finally:
            self._phase   = "idle"
            self._running = False

    def _mic_capture(self):
        """Fill _pcm_queue from sounddevice mic. Runs in its own thread."""
        try:
            import sounddevice as sd
            CHUNK = int(AUDIO_SAMPLE_RATE * 0.1)

            def callback(indata, frames, time_info, status):
                if self._running:
                    pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
                    try:
                        self._pcm_queue.put_nowait(pcm)
                    except queue.Full:
                        pass  # drop oldest if queue full

            with sd.InputStream(samplerate=AUDIO_SAMPLE_RATE, channels=1,
                                 dtype='float32', blocksize=CHUNK, callback=callback):
                while self._running:
                    time.sleep(0.1)

        except ImportError:
            pass
        except Exception as e:
            print(f"[Coach] Mic error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Gradio App
# ══════════════════════════════════════════════════════════════════════════════

def build_gradio_app(capture_mode: str = "webcam"):
    lesson_choices = [
        f"Lesson {k} — {v['title'].split('—')[1].strip()}"
        for k, v in LESSONS.items()
    ]

    _state = {
        "coach":        None,
        "latest_frame": None,
        "frame_lock":   threading.Lock(),
        "start_lock":   threading.Lock(),   # prevents double-start from rapid frames
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

        return LESSONS[lesson_num]["description"]

    def stop_session():
        _state["running"] = False
        if _state["coach"]:
            _state["coach"].stop()
            _state["coach"] = None
        if _state["screen"]:
            _state["screen"].stop()
            _state["screen"] = None
        return (
            gr.update(value="Session stopped. Start the webcam to begin again."),
            gr.update(value=""),
            gr.update(value=None),
        )

    # ── Frame intake ──────────────────────────────────────────────────────────

    def store_webcam_frame(frame_rgb, lesson_choice):
        """
        Called by Gradio every 0.5s while the webcam is active.
        IMPORTANT: never change component visibility here — DOM re-renders
        interrupt the stream. All components are always visible; we only
        update their values.
        Outputs: [lesson_desc, cycle_status, coach_audio]
        """
        if frame_rgb is None:
            return gr.update(), gr.update(), gr.update()

        with _state["frame_lock"]:
            _state["latest_frame"] = frame_rgb

        # ── First frame: auto-start session (value update only, no visibility) ─
        if not _state["running"]:
            with _state["start_lock"]:
                if not _state["running"]:
                    desc = start_session(lesson_choice)
                    return (
                        gr.update(value=desc),
                        gr.update(value="🎙 Starting…"),
                        gr.update(),
                    )

        # ── Every frame: update cycle status + deliver audio when ready ───────
        coach = _state["coach"]
        if not coach:
            return gr.update(), gr.update(), gr.update()

        status  = coach.get_status()
        phase   = status["phase"]
        elapsed = status["elapsed"]

        if phase == "intro":
            cycle_str = "🎙 Your coach is speaking…"
        elif phase == "play":
            remaining = max(0, PLAY_DURATION_SEC - elapsed)
            cycle_str = f"🎵 Play now — {remaining:.0f}s remaining"
        elif phase == "analyzing":
            cycle_str = "⏳ Analyzing your playing…"
        elif phase == "feedback":
            cycle_str = "🔊 Feedback playing"
        else:
            cycle_str = gr.update()

        audio = coach.get_latest_audio()
        if audio:
            sr, arr = audio
            print(f"[Frame] Delivering audio to browser: {len(arr)} samples @ {sr}Hz")
            return gr.update(), gr.update(value=cycle_str), (sr, arr)

        return gr.update(), gr.update(value=cycle_str), gr.update()

    # ── Layout ────────────────────────────────────────────────────────────────
    with gr.Blocks(title="🎵 Live Bansuri Coach") as app:

        gr.Markdown(f"# 🎵 Live Bansuri Coach\n**{GEMINI_MODEL_LIVE}**  |  `{capture_mode}` mode")

        with gr.Row():
            lesson_selector = gr.Dropdown(
                choices=lesson_choices, value=lesson_choices[0],
                label="Select Lesson", scale=4,
            )
            stop_btn = gr.Button("⏹ Stop", variant="stop", scale=1)

        lesson_desc  = gr.Textbox(label="Lesson Goal",     interactive=False, value="Select a lesson and start the webcam to begin")
        cycle_status = gr.Textbox(label="⏱ Current Phase", interactive=False, value="")

        with gr.Row():
            with gr.Column(scale=3):
                if capture_mode == "webcam":
                    webcam_in = gr.Image(
                        sources=["webcam"],
                        streaming=True,
                        type="numpy",
                        label="Click the camera button below to start your session",
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
                    type="numpy",
                    visible=True,   # always visible — avoids update timing issues
                )

        # ── Wiring ────────────────────────────────────────────────────────────

        if capture_mode == "webcam":
            # Session auto-starts on the first frame — no separate Start button needed.
            # store_webcam_frame returns visibility updates only on first frame.
            webcam_in.stream(
                fn=store_webcam_frame,
                inputs=[webcam_in, lesson_selector],
                outputs=[lesson_desc, cycle_status, coach_audio],
                stream_every=0.5,
                concurrency_limit=None,
            )
        else:
            start_btn = gr.Button("▶ Start", variant="primary", scale=1)
            start_btn.click(
                fn=lambda lc: (
                    gr.update(visible=True, value=start_session(lc)),
                    gr.update(visible=True),
                    gr.update(visible=True),
                ),
                inputs=[lesson_selector],
                outputs=[lesson_desc, cycle_status, coach_audio],
            )

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

        stop_btn.click(
            fn=stop_session,
            outputs=[lesson_desc, cycle_status, coach_audio],
        )

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
    print(f"  Cycle   : play {PLAY_DURATION_SEC}s → feedback → repeat")
    print(f"{'='*60}\n")

    app = build_gradio_app(capture_mode=args.mode)
    app.launch(
        server_port=args.port,
        share=False,
        inbrowser=True,
        theme=gr.themes.Soft(),
    )
