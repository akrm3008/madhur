# Live Bansuri Coach

A real-time Indian classical flute (bansuri) teaching app powered by the **Gemini Live API**. It watches you play via webcam, listens through your microphone, and speaks feedback through your speakers — like a teacher sitting next to you.

## How it works

- Your **webcam** streams video frames to Gemini (posture, finger holes, embouchure)
- Your **microphone** streams continuous audio to Gemini (note pitch, tone quality, breath)
- Gemini responds with **spoken audio feedback** every few seconds, played back automatically in the browser

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get a Gemini API key

Go to [aistudio.google.com](https://aistudio.google.com) → **Get API key** → create a new key.

### 3. Create a `.env` file

```bash
cp .env.example .env   # or create it manually
```

Edit `.env`:

```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL_LIVE=gemini-3.1-flash-live-preview
```

> **Never commit your `.env` file.** It is gitignored by default.

### 4. Run the app

```bash
python live_flute_coach.py --lesson 1 --mode webcam
```

The Gradio UI opens in your browser automatically. Allow camera access when prompted.

## Lessons

| Lesson | Goal | Pass condition |
|--------|------|---------------|
| 1 — First Breath | Blow across the blow hole with **all holes open** | Any pitched sound is produced |
| 2 — Pa Note | Cover **all 6 holes** and produce a clear Pa note | Pa audible, tone clean |

## CLI options

```
--lesson 1 or 2      Select which lesson to practice (default: 1)
--mode webcam        Use browser webcam — recommended, no permission issues (default)
--mode screen        Capture your primary monitor instead of webcam
--port 7860          Gradio server port (default: 7860)
```

## Testing Gemini note identification

To evaluate how accurately Gemini identifies notes from raw audio vs a local pitch detector (PYIN):

```bash
python test_gemini_note_id.py --rounds 5 --sa C4
```

This records you playing single notes and compares three methods:
1. **PYIN** (librosa) — local pitch detector, used as ground truth
2. **Gemini via text** — PYIN result passed as text context
3. **Gemini native audio** — raw PCM sent directly to the Live API

## Project structure

```
live_flute_coach.py      Main app — Gemini Live session + Gradio UI
prompts.py               System prompts for each lesson
config.py                Model names, audio/video settings, lesson metadata
test_gemini_note_id.py   Script to benchmark Gemini note identification accuracy
00_quickstart.ipynb      Interactive notebook walkthrough
requirements.txt         Python dependencies
.env                     Your API key (gitignored, never committed)
```

## Requirements

- Python 3.10+
- Microphone and speakers/headphones
- Webcam (or use `--mode screen`)
- Gemini API key with access to a live-capable model
