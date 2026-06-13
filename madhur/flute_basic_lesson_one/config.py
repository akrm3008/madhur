import os
from dotenv import load_dotenv

load_dotenv()

# ── Gemini model config ───────────────────────────────────────────────────────
# Set this to the latest live-capable Gemini model you have access to.
# For the Live (streaming) API, Google typically uses Flash variants.
# Check https://ai.google.dev/gemini-api/docs/models for the latest names.
#
# Examples (update as new models release):
#   "gemini-2.0-flash-live-001"         ← Live API, fast
#   "gemini-2.5-pro-preview-05-06"      ← latest Pro (non-live, polling mode)
#   "gemini-3.1-pro"                    ← set this once you confirm the name

GEMINI_MODEL_LIVE    = os.getenv("GEMINI_MODEL_LIVE",    "gemini-3.5-flash")
GEMINI_MODEL_POLLING = os.getenv("GEMINI_MODEL_POLLING", "gemini-3.1-pro-preview")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Capture settings ──────────────────────────────────────────────────────────
FRAME_INTERVAL_SEC   = 5.0     # how often to send a frame to Gemini (polling mode)
JPEG_QUALITY         = 80      # JPEG compression quality for frames
SCREEN_MONITOR_INDEX = 1       # 1 = primary monitor (mss index)

# ── Audio settings ────────────────────────────────────────────────────────────
AUDIO_SAMPLE_RATE    = 16000   # Hz — required by Gemini Live audio input
AUDIO_CHUNK_SEC      = 0.5     # seconds of audio per chunk sent to Live API

# ── Flute / lesson settings ───────────────────────────────────────────────────
# Sa frequency for your specific bansuri (change to match your flute)
SA_HZ = 440.0   # A4 — change to C4=261.63, G4=392.0, etc.

LESSONS = {
    "1": {
        "title":       "Lesson 1 — First Breath (no holes covered)",
        "description": "Blow across the blow hole with all holes open. Just produce any sound.",
        "expected_note": None,   # any note is fine, just check sound is produced
        "holes_expected": "open",
    },
    "2": {
        "title":       "Lesson 2 — Pa (all holes covered)",
        "description": "Cover all 6 holes and produce a clear Pa note.",
        "expected_note": "Pa",
        "holes_expected": "all_covered",
    },
}
