"""Bounded local CPU Whisper transcription; no transcript persistence."""

import logging
from functools import lru_cache
from pathlib import Path

from app.services.extractors import ExtractionError, ExtractionResult, bounded
from app.services.extractors.ffmpeg import convert, probe
from app.services.media_config import MAX_SECONDS, MODEL_DIR


@lru_cache(maxsize=1)
def model():
    try:
        from faster_whisper import WhisperModel

        logging.getLogger("faster_whisper").setLevel(logging.ERROR)
        direct = MODEL_DIR / "speech" / "small"
        source = str(direct) if (direct / "model.bin").exists() else "small"
        return WhisperModel(
            source,
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
            download_root=str(MODEL_DIR / "speech"),
            local_files_only=True,
        )
    except (ImportError, OSError, RuntimeError, ValueError):
        raise ExtractionError(
            "Speech model unavailable. Run the documented media setup command.", 503
        ) from None


def transcribe(path: str) -> ExtractionResult:
    """Auto-detect language; blank/no-speech input must not become a safe verdict."""
    segments, _info = model().transcribe(
        path, beam_size=3, vad_filter=True, condition_on_previous_text=False
    )
    texts = []
    for segment in segments:
        if segment.no_speech_prob < 0.6:
            texts.append(segment.text)
            bounded(" ".join(texts))
    return ExtractionResult(
        bounded(" ".join(texts)),
        None,
        [
            "Automatic transcription can miss or mishear words. Review the extracted preview."
        ],
    )


def extract(path: str) -> ExtractionResult:
    details = probe(path)
    if not details["audio"]:
        raise ExtractionError("No audio track was found.")
    wav = Path(path).parent / "speech.wav"
    convert(path, wav, ["-vn", "-t", str(MAX_SECONDS), "-ac", "1", "-ar", "16000"])
    try:
        return transcribe(str(wav))
    finally:
        wav.unlink(missing_ok=True)
