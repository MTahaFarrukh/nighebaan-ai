"""Combine bounded audio transcription and sampled video-frame OCR."""

from pathlib import Path

from app.services.extractors import (
    ExtractionResult,
    audio,
    bounded,
    image,
)
from app.services.extractors.ffmpeg import convert, probe
from app.services.media_config import MAX_SECONDS


def extract(path: str) -> ExtractionResult:
    details = probe(path)
    if not details["video"]:
        return audio.extract(path)
    texts, notes = (
        [],
        [
            "Video OCR samples one frame every 10 seconds; brief on-screen text may be missed."
        ],
    )
    if details["audio"]:
        result = audio.extract(path)
        texts.append(result.text)
        notes.extend(result.warnings)
    frame_pattern = Path(path).parent / "frame-%03d.png"
    convert(
        path,
        frame_pattern,
        [
            "-an",
            "-t",
            str(MAX_SECONDS),
            "-vf",
            "fps=1/10:round=up:start_time=0,scale=1280:1280:force_original_aspect_ratio=decrease",
            "-frames:v",
            "6",
        ],
    )
    for frame in sorted(Path(path).parent.glob("frame-*.png")):
        try:
            result = image.extract(str(frame))
            if result.text not in texts:
                texts.append(result.text)
            notes.extend(result.warnings)
            bounded("\n".join(texts))
        finally:
            frame.unlink(missing_ok=True)
    return ExtractionResult(bounded("\n".join(texts)), None, list(dict.fromkeys(notes)))
