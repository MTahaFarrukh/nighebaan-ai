"""Pinned speech download integrity and resume tests, with no network."""

import hashlib
from io import BytesIO

import pytest
from ml import download_speech


class Response(BytesIO):
    status = 206

    def __init__(self, data, start):
        super().__init__(data)
        self.headers = {"Content-Range": f"bytes {start}-2/3"}


def prepare(monkeypatch, tmp_path):
    monkeypatch.setattr(download_speech, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(download_speech, "MODEL_BYTES", 3)
    monkeypatch.setattr(
        download_speech, "MODEL_SHA", hashlib.sha256(b"abc").hexdigest()
    )
    target = tmp_path / "speech/small"
    target.mkdir(parents=True)
    for name in ["config.json", "tokenizer.json", "vocabulary.txt"]:
        (target / name).write_text("{}")
    return target


def test_resume_and_verified_promotion(monkeypatch, tmp_path):
    target = prepare(monkeypatch, tmp_path)
    (target / "model.bin.partial").write_bytes(b"a")

    def retrieve(request, timeout):
        assert request.get_header("Range") == "bytes=1-"
        return Response(b"bc", 1)

    monkeypatch.setattr(download_speech.urllib.request, "urlopen", retrieve)
    assert download_speech.download() == target
    assert (target / "model.bin").read_bytes() == b"abc"
    assert not (target / "model.bin.partial").exists()
    assert download_speech.download() == target


def test_bad_digest_not_promoted(monkeypatch, tmp_path):
    target = prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(
        download_speech.urllib.request,
        "urlopen",
        lambda *args, **kwargs: Response(b"bad", 0),
    )
    with pytest.raises(ValueError, match="fingerprint"):
        download_speech.download()
    assert not (target / "model.bin").exists()
    assert (target / "model.bin.partial").exists()
