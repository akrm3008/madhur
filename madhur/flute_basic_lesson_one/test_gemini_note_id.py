"""
Test: How well can Gemini identify musical notes from raw audio?

This script records you playing a single note on the flute (or any instrument),
then runs THREE identification methods and compares results:

  1. PYIN (librosa)     — our local pitch detector, ground truth reference
  2. Gemini via text    — send PYIN result as text context, ask Gemini to interpret
  3. Gemini via audio   — send raw audio bytes directly to Gemini Live API

The goal: decide whether to trust Gemini's native audio understanding for
note identification, or whether we should always pass PYIN output as context.

Usage:
    python test_gemini_note_id.py
    python test_gemini_note_id.py --duration 3 --sa C4
    python test_gemini_note_id.py --rounds 5       # test 5 notes in a row
"""

import asyncio
import argparse
import time
import sys
import os

import numpy as np
import sounddevice as sd
import librosa

sys.path.insert(0, os.path.dirname(__file__))
from config import GEMINI_API_KEY, GEMINI_MODEL_LIVE, AUDIO_SAMPLE_RATE, SA_HZ
from google import genai
from google.genai import types


# ── Indian swara mapping ───────────────────────────────────────────────────────

SWARAS = {
    0: 'Sa', 1: 'Re♭', 2: 'Re', 3: 'Ga♭', 4: 'Ga',
    5: 'Ma', 6: 'Ma#', 7: 'Pa', 8: 'Dha♭', 9: 'Dha',
    10: 'Ni♭', 11: 'Ni',
}

def hz_to_swara(freq_hz, sa_hz=SA_HZ):
    if not freq_hz or np.isnan(freq_hz) or freq_hz <= 0:
        return None, None
    semitones = 12 * np.log2(freq_hz / sa_hz)
    nearest   = int(round(semitones)) % 12
    cents_dev = (semitones - round(semitones)) * 100
    return SWARAS[nearest], round(cents_dev, 1)


# ── Method 1: PYIN local pitch detection ──────────────────────────────────────

def identify_with_pyin(audio: np.ndarray, sr: int = AUDIO_SAMPLE_RATE, sa_hz: float = SA_HZ):
    """Run librosa PYIN on the recorded audio. Returns (note_name, hz, swara, cents_dev)."""
    f0, voiced, _ = librosa.pyin(audio, fmin=80, fmax=2000, sr=sr)
    voiced_f0 = f0[voiced]

    if len(voiced_f0) == 0:
        return None, None, None, None

    median_hz  = float(np.median(voiced_f0))
    note_name  = librosa.hz_to_note(median_hz)
    swara, dev = hz_to_swara(median_hz, sa_hz)

    return note_name, round(median_hz, 1), swara, dev


# ── Method 2: Gemini via text context (PYIN result passed as text) ─────────────

def identify_with_gemini_text(note_name: str, hz: float, sa_hz: float = SA_HZ):
    """
    Pass the PYIN-detected note to Gemini as text and ask it to map to a swara.
    Tests whether Gemini can do the Sa-relative mapping correctly.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
A pitch detector found the note: {note_name} ({hz:.1f} Hz).
The tonic Sa for this piece is: {librosa.hz_to_note(sa_hz)} ({sa_hz:.1f} Hz).

Question: What Indian classical swara is this note?
Give ONLY a JSON response like:
{{"swara": "Pa", "octave": "madhya", "cents_deviation": +5.2, "confidence": "high"}}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",   # fast model fine for text-only
        contents=[types.Part.from_text(text=prompt)],
    )
    raw = response.text.strip().strip("```json").strip("```").strip()
    try:
        import json
        return json.loads(raw)
    except Exception:
        return {"raw_response": response.text}


# ── Method 3: Gemini via raw audio (Live API) ──────────────────────────────────

async def identify_with_gemini_audio(audio: np.ndarray, sr: int = AUDIO_SAMPLE_RATE, sa_hz: float = SA_HZ):
    """
    Send raw audio bytes directly to Gemini Live API.
    Ask Gemini to identify the note and swara purely from what it hears.
    This tests Gemini's native audio understanding — no PYIN hint given.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Convert float32 → int16 PCM
    pcm_int16 = (audio * 32767).astype(np.int16)
    pcm_bytes = pcm_int16.tobytes()

    system_prompt = f"""
You are a music analysis assistant with expert knowledge of Indian classical music.
The tonic Sa for this piece is the note {librosa.hz_to_note(sa_hz)} ({sa_hz:.1f} Hz).
When you hear audio, identify:
1. The Western note name and approximate frequency
2. The Indian classical swara relative to Sa
3. Whether the note is steady or wavering
4. Tone quality: clear / airy / breathy / squeaky

Always respond as JSON:
{{
  "western_note": "G4",
  "estimated_hz": 392.0,
  "swara": "Pa",
  "octave": "madhya",
  "cents_deviation": 0,
  "note_steady": true,
  "tone_quality": "clear",
  "confidence": "high",
  "notes": "any extra observations"
}}
"""

    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=types.Content(parts=[types.Part(text=system_prompt)]),
    )

    result = {"error": "No response received"}

    try:
        async with client.aio.live.connect(model=GEMINI_MODEL_LIVE, config=config) as session:
            # Send the audio as a single blob
            await session.send_realtime_input(
                audio=types.Blob(
                    data=pcm_bytes,
                    mime_type=f"audio/pcm;rate={sr}"
                )
            )

            # Signal end of turn so Gemini knows to respond
            await session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text="I just played a single note on the bansuri flute. What note is it? Respond as JSON.")]
                ),
                turn_complete=True,
            )

            # Collect response (with timeout)
            full_response = ""
            async for msg in session.receive():
                if msg.text:
                    full_response += msg.text
                if msg.server_content and msg.server_content.turn_complete:
                    break

            raw = full_response.strip().strip("```json").strip("```").strip()
            import json
            try:
                result = json.loads(raw)
            except Exception:
                result = {"raw_response": full_response}

    except Exception as e:
        result = {"error": str(e)}

    return result


# ── Recording helper ───────────────────────────────────────────────────────────

def record_note(duration_sec: float = 2.0, sr: int = AUDIO_SAMPLE_RATE) -> np.ndarray:
    """Record from microphone for duration_sec seconds. Returns float32 mono array."""
    print(f"\n🎵 Recording in 3...")
    time.sleep(1)
    print("   2...")
    time.sleep(1)
    print("   1... PLAY NOW!")
    audio = sd.rec(int(duration_sec * sr), samplerate=sr, channels=1,
                   dtype='float32', blocking=True).flatten()
    print(f"   ✓ Recorded {duration_sec}s")
    return audio


# ── Print comparison table ─────────────────────────────────────────────────────

def print_comparison(round_num, pyin_result, gemini_text_result, gemini_audio_result):
    note_name, hz, swara_pyin, cents = pyin_result

    print(f"\n{'═'*60}")
    print(f"  Round {round_num} — Results Comparison")
    print(f"{'═'*60}")

    if note_name is None:
        print("  ⚠  PYIN: No pitched sound detected. Was the flute playing?")
        return

    print(f"\n  Method 1 — PYIN (local, ground truth):")
    print(f"    Note   : {note_name}  ({hz} Hz)")
    print(f"    Swara  : {swara_pyin}  ({cents:+.1f} cents)")

    print(f"\n  Method 2 — Gemini via text context (PYIN note passed as text):")
    if "swara" in gemini_text_result:
        print(f"    Swara  : {gemini_text_result.get('swara')}")
        print(f"    Octave : {gemini_text_result.get('octave')}")
        print(f"    Confidence: {gemini_text_result.get('confidence')}")
        match = "✅ MATCH" if gemini_text_result.get("swara") == swara_pyin else "❌ MISMATCH"
        print(f"    vs PYIN: {match}")
    else:
        print(f"    Raw: {gemini_text_result}")

    print(f"\n  Method 3 — Gemini native audio (raw PCM sent to Live API):")
    if "swara" in gemini_audio_result:
        print(f"    Note   : {gemini_audio_result.get('western_note')}  (~{gemini_audio_result.get('estimated_hz')} Hz)")
        print(f"    Swara  : {gemini_audio_result.get('swara')}")
        print(f"    Steady : {gemini_audio_result.get('note_steady')}")
        print(f"    Tone   : {gemini_audio_result.get('tone_quality')}")
        print(f"    Confidence: {gemini_audio_result.get('confidence')}")
        match_swara = "✅ MATCH" if gemini_audio_result.get("swara") == swara_pyin else "❌ MISMATCH"
        match_note  = "✅ MATCH" if gemini_audio_result.get("western_note", "").startswith(note_name.replace("♯","#").replace("♭","b")) else "❌ MISMATCH"
        print(f"    Swara vs PYIN : {match_swara}")
        print(f"    Note  vs PYIN : {match_note}")
        if gemini_audio_result.get("notes"):
            print(f"    Notes  : {gemini_audio_result.get('notes')}")
    elif "error" in gemini_audio_result:
        print(f"    Error: {gemini_audio_result['error']}")
    else:
        print(f"    Raw: {gemini_audio_result}")

    print()


# ── Main ───────────────────────────────────────────────────────────────────────

async def run_test(rounds: int, duration: float, sa_note: str):
    sa_hz = librosa.note_to_hz(sa_note)
    print(f"\n🎼 Gemini Note Identification Test")
    print(f"   Rounds   : {rounds}")
    print(f"   Duration : {duration}s per note")
    print(f"   Sa (tonic): {sa_note}  ({sa_hz:.1f} Hz)")
    print(f"   Live model: {GEMINI_MODEL_LIVE}")
    print(f"\n   Play different notes each round to build up a comparison table.")

    scores = {"pyin_total": 0, "gemini_text_match": 0, "gemini_audio_match": 0}

    for r in range(1, rounds + 1):
        print(f"\n--- Round {r}/{rounds} ---")
        print("    Get ready to play ONE note and hold it steady.")

        audio = record_note(duration_sec=duration)

        # Method 1: PYIN
        pyin_result = identify_with_pyin(audio, sa_hz=sa_hz)
        note_name, hz, swara_pyin, cents = pyin_result

        if note_name is None:
            print("  No pitch detected. Skipping round.")
            continue

        scores["pyin_total"] += 1

        # Method 2: Gemini text
        print("  Asking Gemini (text context)...")
        gemini_text_result = identify_with_gemini_text(note_name, hz, sa_hz)

        # Method 3: Gemini audio (Live API)
        print("  Sending audio to Gemini Live API...")
        gemini_audio_result = await identify_with_gemini_audio(audio, sa_hz=sa_hz)

        # Track matches
        if gemini_text_result.get("swara") == swara_pyin:
            scores["gemini_text_match"] += 1
        if gemini_audio_result.get("swara") == swara_pyin:
            scores["gemini_audio_match"] += 1

        print_comparison(r, pyin_result, gemini_text_result, gemini_audio_result)

    # ── Final summary ──────────────────────────────────────────────────────────
    total = scores["pyin_total"]
    if total > 0:
        print(f"\n{'═'*60}")
        print(f"  SUMMARY — {total} notes tested")
        print(f"{'═'*60}")
        print(f"  Gemini (text context) accuracy : {scores['gemini_text_match']}/{total} = {100*scores['gemini_text_match']//total}%")
        print(f"  Gemini (native audio) accuracy : {scores['gemini_audio_match']}/{total} = {100*scores['gemini_audio_match']//total}%")
        print()
        if scores["gemini_audio_match"] / total >= 0.8:
            print("  ✅ Gemini audio is reliable — trust it natively in the live coach.")
        elif scores["gemini_audio_match"] / total >= 0.5:
            print("  ⚠  Gemini audio is moderate — pass PYIN result as hint text alongside audio.")
        else:
            print("  ❌ Gemini audio is unreliable — always pass PYIN note as text context,")
            print("     or implement tool use so Gemini can call the pitch detector explicitly.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Gemini note identification")
    parser.add_argument("--rounds",   type=int,   default=3,    help="Number of notes to test")
    parser.add_argument("--duration", type=float, default=2.5,  help="Recording duration per note (seconds)")
    parser.add_argument("--sa",       type=str,   default="C4", help="Tonic Sa note e.g. C4, G4, A4")
    args = parser.parse_args()

    asyncio.run(run_test(rounds=args.rounds, duration=args.duration, sa_note=args.sa))
