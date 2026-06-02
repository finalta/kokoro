#!/usr/bin/env python3
"""
RunPod Serverless Handler — Kokoro TTS
Supports: generate audio + word timestamps
"""

import runpod
import base64
import io
import os
import subprocess
import tempfile
import numpy as np

print("[Kokoro] Loading pipelines...")
from kokoro import KPipeline

_pipelines = {}

def get_pipeline(lang_code='a'):
    if lang_code not in _pipelines:
        _pipelines[lang_code] = KPipeline(lang_code=lang_code)
    return _pipelines[lang_code]

# Pre-warm
get_pipeline('a')
get_pipeline('b')
print("[Kokoro] Ready.")


def handler(job):
    inp     = job.get("input", {})
    text    = inp.get("text", "").strip()
    voice   = inp.get("voice", "af_heart")
    speed   = float(inp.get("speed", 1.0))
    fmt     = inp.get("format", "mp3")

    if not text:
        return {"error": "No text provided"}

    # Route to correct language pipeline
    # af_/am_ = American, bf_/bm_ = British
    lang_code = 'b' if voice.startswith('b') else 'a'
    pipeline  = get_pipeline(lang_code)

    audio_chunks = []
    timestamps   = []
    current_time = 0.0
    SAMPLE_RATE  = 24000

    for graphemes, phonemes, audio in pipeline(text, voice=voice, speed=speed):
        if audio is None:
            continue

        chunk_duration = len(audio) / SAMPLE_RATE
        audio_chunks.append(audio)

        # Build word-level timestamps from graphemes
        # graphemes is a sentence/phrase chunk — split into words
        if graphemes:
            words = graphemes.strip().split()
            if words:
                word_dur = chunk_duration / len(words)
                for i, word in enumerate(words):
                    timestamps.append({
                        "word":  word,
                        "start": round(current_time + i * word_dur, 3),
                        "end":   round(current_time + (i + 1) * word_dur, 3)
                    })

        current_time += chunk_duration

    if not audio_chunks:
        return {"error": "No audio generated"}

    combined = np.concatenate(audio_chunks)

    # Encode
    if fmt == 'wav':
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, combined, samplerate=SAMPLE_RATE, format='WAV')
        audio_b64 = base64.b64encode(buf.getvalue()).decode()
    else:
        # WAV → MP3 via ffmpeg
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            tmp_wav = f.name
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            tmp_mp3 = f.name
        try:
            import soundfile as sf
            sf.write(tmp_wav, combined, samplerate=SAMPLE_RATE, format='WAV')
            subprocess.run(
                ['ffmpeg', '-y', '-i', tmp_wav, '-b:a', '128k', '-ar', '44100', tmp_mp3],
                check=True, capture_output=True
            )
            with open(tmp_mp3, 'rb') as f:
                audio_b64 = base64.b64encode(f.read()).decode()
        finally:
            try: os.unlink(tmp_wav); os.unlink(tmp_mp3)
            except: pass

    return {
        "audio":      audio_b64,
        "format":     fmt,
        "duration":   round(current_time, 2),
        "timestamps": timestamps   # [{word, start, end}] — used by teleprompter
    }


runpod.serverless.start({"handler": handler})
