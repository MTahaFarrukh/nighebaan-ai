"""Install official OCR/Whisper weights locally, outside user requests."""

import argparse

from app.services.media_config import MODEL_DIR


def setup(ocr: bool, speech: bool) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if ocr:
        import easyocr

        easyocr.Reader(
            ["ur", "en"],
            gpu=False,
            model_storage_directory=str(MODEL_DIR / "ocr"),
            download_enabled=True,
            verbose=False,
        )
        print("OCR weights ready.", flush=True)
    if speech:
        from faster_whisper import WhisperModel
        from ml.download_speech import download

        WhisperModel(
            str(download()),
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
            download_root=str(MODEL_DIR / "speech"),
        )
        print("Speech weights ready.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--speech", action="store_true")
    args = parser.parse_args()
    try:
        setup(args.ocr or not args.speech, args.speech or not args.ocr)
    except Exception:  # noqa: BLE001 - report setup failures without dumping download credentials
        parser.exit(
            1,
            "Media setup failed. Retry the selected model setup; no user media was processed.\n",
        )
