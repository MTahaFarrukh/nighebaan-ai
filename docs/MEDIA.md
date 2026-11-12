# Local media analysis

`POST /api/analyze/file` accepts multipart field `file`. Signature-detected PDF,
PNG/JPEG/WebP, WAV/MP3/OGG/Opus/FLAC/M4A, MP4/WebM are supported. Filenames are ignored.
The response extends AnalyzeResponse with modality, extracted_text (masked preview,
up to 5,000 characters), extraction_confidence (OCR only; not classification accuracy),
and warnings. The complete bounded extraction is analyzed, not just its preview.

## Processing

- PDF: PyMuPDF text first; pages without text rendered for EasyOCR.
- Images: bounded Pillow decode, EXIF orientation, grayscale and resize, local Urdu/English EasyOCR.
- Audio: local FFmpeg to mono 16 kHz WAV, faster-whisper small CPU/int8 with VAD and automatic language detection.
- Video: audio transcription plus at most six OCR frames, one per ten seconds. Short videos include an initial sample. Brief text between samples may be missed.
- Urdu script: original rules plus approximate transliteration cues; deduplicate rule IDs,
  feed transliteration to the existing text model. Small Urdu abuse lexicon is separate;
  coverage is limited, and missing vowels/context can cause errors.
- All modalities reuse text/rule/URL inference and record only high-risk metadata once.

## Limits and privacy

Defaults: 25 MB/file, 20 PDF pages, 60 seconds for audio/video, 16 million pixels,
30,000 extracted characters. Configured with MAX_UPLOAD_MB, MAX_PDF_PAGES,
MAX_VIDEO_SECONDS, MAX_IMAGE_PIXELS, MAX_EXTRACTED_CHARS. GET /api/settings exposes
upload/page/duration limits. Oversized files/extractions return 413, unsupported types
415, unreadable/no-text media 422, unavailable models 503, concurrent media requests 429.
A body cap runs before multipart parsing, including chunked requests. Multipart overhead
is separately bounded. Models are loaded lazily from local weights; requests do not download them.
Only one extraction runs per backend process. FFmpeg uses argument arrays, local protocols,
no shell, and a conversion timeout. Unknown duration is rejected before inference.
Framework upload handles are closed in finally. Original upload, WAV and video frames are
inside a TemporaryDirectory, removed on success and failure. Extracted content is never
written as a text file, logged, put in query caches, or added to database history.
The preview exists in request/browser memory only and masks configured abuse lexicon matches.

## Setup / reproduction

From backend, use the existing .venv Python. Install CPU Torch/torchvision first:

```powershell
uv pip install --python .venv/Scripts/python.exe torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe -m ml.setup_media --ocr
.venv/Scripts/python.exe -m ml.setup_media --speech
```

Weight cache: ignored models/media/. No system FFmpeg install is required; imageio-ffmpeg
supplies the local executable. The setup command alone downloads official model assets;
user media is never sent to a model provider. Retry only the failed model, not all training.
`python -m ml.make_media_demo` creates ignored synthetic PDF/PNG/tone/MP4 fixtures under
data/raw/media_demo. The tone is a negative test: it should return no readable speech,
not a fabricated safe prediction. An additional English speech fixture was synthesized
locally using Windows SAPI; no personal audio was recorded.

## Verified limits

Actual synthetic PDF, PNG and silent MP4 inference succeeded. PDF preserved the credential
and URL cues. OCR missed the URL in the synthetic image/video, producing medium rather than
high risk. These checks establish integration, not OCR accuracy or scam detection quality.
The masked preview and warnings make extraction errors reviewable. No media dataset accuracy
claim is made. Speech-weight setup encountered an interrupted connection/DNS error; consult
the latest HANDOFF section for actual installation and audio-check status.
Desktop/mobile visual QA remains blocked by the computer-use kernel initialization failure.


## Resumable speech setup

`ml.setup_media --speech` now uses `ml.download_speech` to fetch the official small model
at revision 536b0662742c02347bc0e980a01041f333bce120, validating the published SHA-256 before
promoting model.bin. Partial bytes stay under ignored models/media/speech/small for retries.
Completed assets are reused and fingerprint-checked. No alternate model or untrusted mirror is used.
API inference prefers this local directory and never downloads during an upload request.

Reproduce the synthetic spoken fixture on Windows with `powershell -File ml/make_speech_demo.ps1`.
Then `python -m ml.smoke_media` exercises real PDF, OCR, speech, audio+video and no-speech handling.
It writes aggregate status/rule/risk counts only to models/media_smoke.json, uses isolated history,
and does not print or save any extracted transcript. Do not interpret synthetic checks as accuracy.


## Completed runtime verification

Speech weights installed successfully through the pinned resumable downloader and verified
against the official SHA-256. `python -m ml.smoke_media` passed every synthetic case;
aggregate evidence is in backend/models/media_smoke.json. Spoken English audio and video
containing that audio produced readable text and risk results. A pure tone correctly returned
422 (no readable speech), rather than a normal/low verdict. OCR still missed the link in the
synthetic image/video; audio cues supplied the high risk in the spoken-video fixture.
This is not a real-world Roman Urdu speech or OCR accuracy evaluation. Browser visual QA,
realistic spelling/audio checks, URL false-positive work and alert calibration remain open.
