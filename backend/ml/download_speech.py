"""Resumable, pinned official small Whisper asset setup; no user data involved."""

import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from app.services.media_config import MODEL_DIR

REVISION = "536b0662742c02347bc0e980a01041f333bce120"
BASE = f"https://huggingface.co/Systran/faster-whisper-small/resolve/{REVISION}/"
MODEL_BYTES = 483546902
MODEL_SHA = "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download() -> Path:
    """Keep partial weights between attempts; promote only exact verified bytes."""
    target = MODEL_DIR / "speech" / "small"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "tokenizer.json", "vocabulary.txt"):
        path = target / name
        if not path.exists():
            with urllib.request.urlopen(BASE + name, timeout=30) as response:
                data = response.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024:
                raise ValueError("Unexpected metadata size.")
            if name.endswith(".json"):
                json.loads(data)
            path.write_bytes(data)
    model = target / "model.bin"
    if model.exists():
        if digest(model) != MODEL_SHA:
            raise ValueError("Existing model fingerprint mismatch.")
        return target
    partial = target / "model.bin.partial"
    for attempt in range(3):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset == MODEL_BYTES:
            break
        request = urllib.request.Request(
            BASE + "model.bin",
            headers={
                "Range": f"bytes={offset}-",
                "User-Agent": "Nigehbaan-media-setup/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                append = response.status == 206 and offset > 0
                if append and not response.headers.get("Content-Range", "").startswith(
                    f"bytes {offset}-"
                ):
                    raise ValueError("Invalid resumed download range.")
                if not append:
                    offset = 0
                with partial.open("ab" if append else "wb") as output:
                    reported = offset // (50 * 1024 * 1024)
                    while chunk := response.read(1024 * 1024):
                        offset += len(chunk)
                        if offset > MODEL_BYTES:
                            raise ValueError("Unexpected model size.")
                        output.write(chunk)
                        output.flush()
                        if offset // (50 * 1024 * 1024) > reported:
                            reported = offset // (50 * 1024 * 1024)
                            print(
                                f"Speech weight download: {offset // (1024 * 1024)} MB",
                                flush=True,
                            )
            if offset == MODEL_BYTES:
                break
        except (OSError, urllib.error.URLError):
            print(
                f"Model transfer interrupted; partial bytes retained (attempt {attempt + 1}).",
                flush=True,
            )
            time.sleep(2)
    if (
        not partial.exists()
        or partial.stat().st_size != MODEL_BYTES
        or digest(partial) != MODEL_SHA
    ):
        raise ValueError(
            "Speech weights incomplete or fingerprint mismatch; retry setup."
        )
    partial.replace(model)
    (target / "manifest.json").write_text(
        json.dumps(
            {
                "source": BASE,
                "revision": REVISION,
                "sha256": MODEL_SHA,
                "bytes": MODEL_BYTES,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return target
