"""Generate clearly synthetic local fixtures for manual media demos."""

import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont


def create() -> Path:
    directory = Path(__file__).resolve().parents[1] / "data/raw/media_demo"
    directory.mkdir(parents=True, exist_ok=True)
    sample = "Foran OTP bhejo https://example.com"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 70), "SYNTHETIC DEMO - NOT A REAL MESSAGE", fontsize=12)
        page.insert_text((50, 120), sample, fontsize=16)
        document.save(directory / "synthetic-message.pdf")
    canvas = Image.new("RGB", (1500, 300), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("arial.ttf", 42)
    draw.text((35, 35), "SYNTHETIC DEMO", font=font, fill="black")
    draw.text((35, 130), sample, font=font, fill="black")
    canvas.save(directory / "synthetic-message.png")
    with wave.open(str(directory / "synthetic-tone.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(
            (np.sin(np.arange(32000) * 2 * np.pi * 440 / 16000) * 1000)
            .astype("<i2")
            .tobytes()
        )
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-nostdin",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(directory / "synthetic-message.png"),
            "-t",
            "2",
            "-vf",
            "scale=1280:-2",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(directory / "synthetic-message.mp4"),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    print("Synthetic PDF/image/tone/video fixtures generated; no real user data.")
    return directory


if __name__ == "__main__":
    create()
