"""Local ffmpeg conversion and duration checks, with no shell or remote protocols."""

import math
import subprocess
from pathlib import Path

import av
import imageio_ffmpeg

from app.services.extractors import ExtractionError
from app.services.media_config import MAX_PIXELS, MAX_SECONDS

av.logging.set_level(av.logging.PANIC)


def probe(path: str) -> dict:
    """Reject unknown or excessive duration before decoding/model work."""
    try:
        with av.open(path, options={"protocol_whitelist": "file,pipe"}) as container:
            durations = (
                [float(container.duration) / av.time_base] if container.duration else []
            )
            streams = list(container.streams)
            durations.extend(
                float(stream.duration * stream.time_base)
                for stream in streams
                if stream.duration and stream.time_base
            )
            if not durations or any(
                not math.isfinite(value) or value <= 0 for value in durations
            ):
                raise ExtractionError("Media duration could not be verified.")
            duration = max(durations)
            if duration > MAX_SECONDS:
                raise ExtractionError(
                    "Audio/video duration exceeds the configured limit.", 413
                )
            if any(
                stream.type == "video" and stream.width * stream.height > MAX_PIXELS
                for stream in streams
            ):
                raise ExtractionError(
                    "Video dimensions exceed the allowed pixel limit.", 413
                )
            return {
                "duration": duration,
                "audio": any(s.type == "audio" for s in streams),
                "video": any(s.type == "video" for s in streams),
            }
    except ExtractionError:
        raise
    except (av.FFmpegError, OSError, ValueError):
        raise ExtractionError("The audio/video container could not be read.") from None


def convert(path: str, destination: Path, arguments: list[str]) -> None:
    """Suppress decoder stderr so uploaded content cannot reach logs."""
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        path,
        *arguments,
        "-y",
        str(destination),
    ]
    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        raise ExtractionError("Media conversion failed or timed out.") from None
