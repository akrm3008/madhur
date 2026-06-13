"""
Live Flute Coach — Gemini-powered real-time bansuri feedback.

Two capture modes:
  --mode webcam   : Gradio browser webcam (no macOS permission issues)
  --mode screen   : captures your screen using mss (like AI Studio screen share)

Run:
  python live_flute_coach.py --lesson 1 --mode webcam
  python live_flute_coach.py --lesson 2 --mode screen
  python live_flute_coach.py --lesson 1 --mode webcam --live
"""

import asyncio
import json
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
    GEMINI_API_KEY, GEMINI_MODEL_LIVE, GEMINI_MODEL_POLLING,
    FRAME_INTERVAL_SEC, JPEG_QUALITY, SCREEN_MONITOR_INDEX,
    AUDIO_SAMPLE_RATE, LESSONS,
)
from prompts import get_live_system_prompt, get_frame_prompt


# ══════════════════════════════════════════════════════════════════════════════
# Frame encoding
# ══════════════════════════════════════════════════════════════════════════════

def encode_jpeg(frame_bgr: np.ndarray, quality: int = JPEG_QUALITY) -> bytes:
    _, buf = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes()


# ══════════════════════════════════════════════════════════════════════════════
# Screen capture (mss) — only used in screen mode
# ══════════════════════════════════════════════════════════════════════════════

class ScreenCapture:
    """Thread-safe screen capture using mss."""

    def __init__(self, monitor_index: int = SCREEN_MONITOR_INDEX):
        self._monitor_index = monitor_index
        self._frame = None
        self._lock  = threading.Lock()
        self._stop  = threading.Event()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[self._monitor_index]
                while not self._stop.is_set():
                    shot      = sct.grab(monitor)
                    frame_rgb = np.array(shot)
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_BGRA2BGR)
                    h, w = frame_bgr.shape[:2]
                    if w > 1280:
                        frame_bgr = cv2.resize(frame_bgr, (1280, int(h * 1280 / w)))
                    with self._lock:
                        self._frame = frame_bgr
                    time.sleep(0.1)
        except ImportError:
            print("mss not installed — run: pip install mss")

    def get_frame(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def stop(self):
        self._stop.set()


# ══════════════════════════════════════════════════════════════════════════════
# Pitch detection from microphone
# ══════════════════════════════════════════════════════════════════════════════

def check_pitch_from_mic(duration_sec: float = 0.5, sr: int = AUDIO_SAMPLE_RATE):
    """Record a short mic burst and return (pitch_hz, note_name) or (None, None)."""
    try:
        import sounddevice as sd
        import librosa
        audio     = sd.rec(int(duration_sec * sr), samplerate=sr,
                           channels=1, dtype='float32', blocking=True).flatten()
        f0, voiced, _ = librosa.pyin(audio, fmin=100, fmax=2000, sr=sr)
        voiced_f0 = f0[voiced]
        if len(voiced_f0) > 0:
            median_f0 = float(np.median(voiced_f0))
            return median_f0, librosa.hz_to_note(median_f0)
    except Exception:
        pass
    return None, None


# ══════════════════════════════════════════════════════════════════════════════
# Gemini Polling Coach
# ══════════════════════════════════════════════════════════════════════════════

class PollingCoach:
    """Send a frame to Gemini generateContent, get structured JSON back."""

    def __init__(self, lesson_num: str, model: str = GEMINI_MODEL_POLLING):
        self.client        = genai.Client(api_key=GEMINI_API_KEY)
        self.model         = model
        self.lesson_num    = lesson_num
        self.system_prompt = get_live_system_prompt(lesson_num)
        self.frame_prompt  = get_frame_prompt(lesson_num)

    def analyse_frame(self, frame_bgr: np.ndarray) -> dict:
        jpeg_bytes = encode_jpeg(frame_bgr)
        prompt = self.frame_prompt + "\n\nReturn ONLY valid JSON, no markdown fences."

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
                types.Part.from_text(text=prompt),
            ],
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.3,
                max_output_tokens=512,
            ),
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"feedback": raw, "lesson_passed": False, "next_action": ""}


# ══════════════════════════════════════════════════════════════════════════════
# Gemini Live Streaming Coach
# ══════════════════════════════════════════════════════════════════════════════

class LiveStreamCoach:
    """Gemini Live API — bidirectional WebSocket stream, sub-second latency."""

    def __init__(self, lesson_num: str, model: str = GEMINI_MODEL_LIVE):
        self.client        = genai.Client(api_key=GEMINI_API_KEY)
        self.model         = model
        self.lesson_num    = lesson_num
        self.system_prompt = get_live_system_prompt(lesson_num)
        self._q: queue.Queue = queue.Queue()
        self._running = False

    def get_latest_feedback(self) -> str | None:
        try:
            return self._q.get_nowait()
        except queue.Empty:
            return None

    def start(self, frame_getter):
        self._running = True
        self._frame_getter = frame_getter
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._stream())

    async def _stream(self):
        config = types.LiveConnectConfig(
            response_modalities=["TEXT"],
            system_instruction=types.Content(
                parts=[types.Part(text=self.system_prompt)]
            ),
        )
        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                # Send video frames, mic audio, and receive — all concurrently
                await asyncio.gather(
                    self._send_frames(session),
                    self._send_audio(session),
                    self._receive(session),
                )
        except Exception as e:
            self._q.put(f"[Live API error: {e}]")

    async def _send_frames(self, session):
        """Send a video frame every FRAME_INTERVAL_SEC."""
        while self._running:
            frame = self._frame_getter()
            if frame is not None:
                jpeg = encode_jpeg(frame, quality=70)
                await session.send_realtime_input(
                    video=types.Blob(data=jpeg, mime_type="image/jpeg")
                )
            await asyncio.sleep(FRAME_INTERVAL_SEC)

    async def _send_audio(self, session):
        """
        Stream raw microphone audio to Gemini in real-time.
        Gemini Live expects: mono PCM, 16kHz, 16-bit signed int (little-endian).
        We send ~100ms chunks continuously so Gemini can hear the flute as it plays.
        """
        try:
            import sounddevice as sd

            CHUNK_SAMPLES = int(AUDIO_SAMPLE_RATE * 0.1)   # 100ms per chunk = 1600 samples
            loop = asyncio.get_event_loop()

            def callback(indata, frames, time_info, status):
                # indata is float32 from sounddevice; convert to int16 PCM for Gemini
                pcm_int16 = (indata[:, 0] * 32767).astype(np.int16)
                pcm_bytes = pcm_int16.tobytes()
                # Schedule send on the async loop (callback runs in a separate thread)
                asyncio.run_coroutine_threadsafe(
                    session.send_realtime_input(
                        audio=types.Blob(
                            data=pcm_bytes,
                            mime_type=f"audio/pcm;rate={AUDIO_SAMPLE_RATE}"
                        )
                    ),
                    loop,
                )

            with sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=1,
                dtype='float32',
                blocksize=CHUNK_SAMPLES,
                callback=callback,
            ):
                # Keep stream open until stopped
                while self._running:
                    await asyncio.sleep(0.1)

        except ImportError:
            self._q.put("[Audio] sounddevice not installed — run: pip install sounddevice")
        except Exception as e:
            self._q.put(f"[Audio stream error: {e}]")

    async def _receive(self, session):
        async for msg in session.receive():
            if msg.text:
                self._q.put(msg.text)
            if not self._running:
                break


# ══════════════════════════════════════════════════════════════════════════════
# Gradio App
# ══════════════════════════════════════════════════════════════════════════════

def build_gradio_app(capture_mode: str = "webcam", use_live_api: bool = False):
    """
    capture_mode : "webcam"  — Gradio browser webcam (no macOS permission issues)
                   "screen"  — mss screen capture + timer
    use_live_api : False = polling (any model) | True = Live API (flash model only)
    """
    lesson_choices = [
        f"Lesson {k} — {v['title'].split('—')[1].strip()}"
        for k, v in LESSONS.items()
    ]

    # Module-level singleton coach (recreated on lesson change)
    _coach_cache: dict = {"coach": None, "lesson_num": None}
    _screen: dict      = {"capture": None}

    def get_coach(lesson_num: str) -> PollingCoach:
        if _coach_cache["coach"] is None or _coach_cache["lesson_num"] != lesson_num:
            _coach_cache["coach"]      = PollingCoach(lesson_num)
            _coach_cache["lesson_num"] = lesson_num
        return _coach_cache["coach"]

    def extract_lesson_num(choice: str) -> str:
        return choice.split("—")[0].strip().split()[-1]   # "Lesson 1 — ..." → "1"

    def format_pitch(pitch_hz, note_name) -> str:
        return f"{note_name}  ({pitch_hz:.1f} Hz)" if pitch_hz else "—"

    # ── WEBCAM mode: Gradio streams frames from browser ──────────────────────
    # No OpenCV camera open needed. Browser handles macOS permissions naturally.

    def process_webcam_frame(frame_rgb, lesson_choice, t_last, fb_last):
        """
        Called by Gradio's .stream() every FRAME_INTERVAL_SEC seconds.
        frame_rgb : numpy RGB array from browser webcam
        t_last    : gr.State — timestamp of last Gemini call
        fb_last   : gr.State — last feedback dict
        """
        now = time.time()
        fb  = fb_last or {}

        if frame_rgb is None:
            return (fb.get("feedback", "Point your camera at yourself playing the flute."),
                    fb.get("next_action", ""), "⏳ Waiting...", "—", t_last, fb)

        # Rate-limit: skip if called too soon (stream_every handles this but belt+braces)
        if now - t_last < FRAME_INTERVAL_SEC * 0.8:
            passed = fb.get("lesson_passed", False)
            return (fb.get("feedback", ""), fb.get("next_action", ""),
                    "✅ PASSED" if passed else "🎵 Keep going...", "—", t_last, fb)

        lesson_num = extract_lesson_num(lesson_choice)
        coach      = get_coach(lesson_num)

        # Gradio sends RGB; our encoder expects BGR
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        result    = coach.analyse_frame(frame_bgr)

        passed     = result.get("lesson_passed", False)
        status     = "✅ PASSED" if passed else "🎵 Keep going..."
        pitch_hz, note_name = check_pitch_from_mic()
        pitch_str  = format_pitch(pitch_hz, note_name)

        return (result.get("feedback", ""), result.get("next_action", ""),
                status, pitch_str, now, result)

    # ── SCREEN mode: mss grabs screen, timer triggers Gemini ─────────────────

    def start_screen_capture(lesson_choice):
        if _screen["capture"]:
            _screen["capture"].stop()
        _screen["capture"] = ScreenCapture()
        lesson_num  = extract_lesson_num(lesson_choice)
        lesson_info = LESSONS[lesson_num]
        return f"✅ Screen capture started", lesson_info["description"]

    def stop_screen_capture():
        if _screen["capture"]:
            _screen["capture"].stop()
            _screen["capture"] = None
        return "Stopped."

    def analyse_screen_frame(lesson_choice):
        cap = _screen["capture"]
        if cap is None:
            return None, "Press Start to begin.", "", "⏳", "—"

        frame = cap.get_frame()
        if frame is None:
            return None, "Capturing screen...", "", "⏳", "—"

        lesson_num = extract_lesson_num(lesson_choice)
        coach      = get_coach(lesson_num)
        result     = coach.analyse_frame(frame)

        passed      = result.get("lesson_passed", False)
        status      = "✅ PASSED" if passed else "🎵 Keep going..."
        pitch_hz, note_name = check_pitch_from_mic()
        pitch_str   = format_pitch(pitch_hz, note_name)
        display     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        return display, result.get("feedback", ""), result.get("next_action", ""), status, pitch_str

    # ── Layout ────────────────────────────────────────────────────────────────
    with gr.Blocks(title="🎵 Live Bansuri Coach") as app:

        gr.Markdown(
            "# 🎵 Live Bansuri Coach\n"
            f"**Gemini** `{'Live API — ' + GEMINI_MODEL_LIVE if use_live_api else 'Polling — ' + GEMINI_MODEL_POLLING}`"
            f"  |  Mode: `{capture_mode}`"
        )

        with gr.Row():
            lesson_selector = gr.Dropdown(
                choices=lesson_choices, value=lesson_choices[0],
                label="Select Lesson", scale=3,
            )
            if capture_mode == "screen":
                start_btn = gr.Button("▶ Start Screen Capture", variant="primary", scale=1)
                stop_btn  = gr.Button("⏹ Stop", variant="stop", scale=1)

        lesson_desc    = gr.Textbox(label="Lesson Goal", interactive=False)
        session_status = gr.Textbox(label="Status",      interactive=False)

        with gr.Row():
            # ── Webcam mode ───────────────────────────────────────────────────
            if capture_mode == "webcam":
                with gr.Column(scale=3):
                    # gr.Image with sources=["webcam"] uses the BROWSER camera
                    # — no OpenCV, no macOS permission headaches
                    webcam_in = gr.Image(
                        sources=["webcam"],
                        streaming=True,
                        type="numpy",
                        label="Your Camera (live — allow camera access in browser)",
                        height=400,
                    )
                    lesson_selector.change(
                        fn=lambda c: LESSONS[extract_lesson_num(c)]["description"],
                        inputs=[lesson_selector],
                        outputs=[lesson_desc],
                    )

            # ── Screen mode ───────────────────────────────────────────────────
            else:
                with gr.Column(scale=3):
                    screen_out = gr.Image(
                        label="Screen Capture", type="numpy", height=400
                    )

            # ── Shared feedback panel ─────────────────────────────────────────
            with gr.Column(scale=2):
                lesson_status_box = gr.Textbox(label="📊 Lesson Status",      interactive=False)
                pitch_display     = gr.Textbox(label="🎼 Detected Pitch (mic)", interactive=False)
                feedback_box      = gr.Textbox(label="💬 Gemini Feedback",
                                               interactive=False, lines=6)
                next_action_box   = gr.Textbox(label="➡ Next Action",          interactive=False)

        # ── Wire up webcam streaming ──────────────────────────────────────────
        if capture_mode == "webcam":
            t_last   = gr.State(value=0.0)
            fb_last  = gr.State(value={})

            webcam_in.stream(
                fn=process_webcam_frame,
                inputs=[webcam_in, lesson_selector, t_last, fb_last],
                outputs=[feedback_box, next_action_box, lesson_status_box,
                         pitch_display, t_last, fb_last],
                stream_every=FRAME_INTERVAL_SEC,   # call fn at most every N seconds
                time_limit=None,
            )

        # ── Wire up screen capture + timer ────────────────────────────────────
        else:
            start_btn.click(
                fn=start_screen_capture,
                inputs=[lesson_selector],
                outputs=[session_status, lesson_desc],
            )
            stop_btn.click(fn=stop_screen_capture, outputs=[session_status])

            timer = gr.Timer(value=FRAME_INTERVAL_SEC)
            timer.tick(
                fn=analyse_screen_frame,
                inputs=[lesson_selector],
                outputs=[screen_out, feedback_box, next_action_box,
                         lesson_status_box, pitch_display],
            )

    return app


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Bansuri Coach")
    parser.add_argument("--lesson", default="1", choices=["1", "2"])
    parser.add_argument("--mode",   default="webcam", choices=["webcam", "screen"])
    parser.add_argument("--live",   action="store_true",
                        help="Use Gemini Live API. Default: polling.")
    parser.add_argument("--port",   type=int, default=7860)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Bansuri Coach — Lesson {args.lesson}")
    print(f"  Capture mode : {args.mode}")
    print(f"  Gemini mode  : {'Live API' if args.live else 'Polling'}")
    print(f"  Model        : {GEMINI_MODEL_LIVE if args.live else GEMINI_MODEL_POLLING}")
    print(f"{'='*60}\n")

    app = build_gradio_app(capture_mode=args.mode, use_live_api=args.live)
    app.launch(
        server_port=args.port,
        share=False,
        inbrowser=True,
        theme=gr.themes.Soft(),    # moved here from gr.Blocks() — fixes Gradio 6 warning
    )
