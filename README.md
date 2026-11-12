# Nigehbaan AI

Local Roman Urdu scam/phishing and abusive-message analysis using a trained LR/SVM
ensemble, static URL model and expert rules. React frontend + FastAPI backend.

## Start the existing Windows demo

From the repository root:

```powershell
powershell -File scripts/start-demo.ps1
```

Open http://localhost:5173/#/analyze. The launcher reuses running services, opens new
processes hidden, and disables API access logging. It does not retrain or download models.
If another app occupies the ports, resolve the conflict rather than killing unknown processes.

## What works

- Text and URL analysis with risk scores, fired rules and explanations.
- Local image/PDF/voice/video extraction, masked preview and warnings.
- Dashboard of high-risk metadata only, Model Lab with real validation metrics,
  read-only Settings, About/Ethics.
- No input text, transcript, filenames, URLs or phone numbers saved in history.
- No submitted URLs visited. Media temporary files cleaned after processing.

WhatsApp is not connected and no guardian alerts are sent. Its integration remains bonus work.
Models are experimental; validation results are not final test or real-world safety guarantees.

## Fresh setup

Python 3.11 and Node are required. Models and source data are intentionally not committed.
Read docs/HANDOFF.md before training: completed local runs must not be repeated.

```powershell
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python.exe -m pip install -r requirements.txt
cd ../frontend
npm ci
npm run gen:types
```

For an existing demo on another local checkout, copy the trusted `text_clf.joblib`
and `url_clf.joblib` together with their matching `.manifest.json` files into
`backend/models/`. The ignored synthetic draft is also required to reconstruct
the exact text partitions. Keep those artifacts local.

Media weights/setup: docs/MEDIA.md. Text/URL model provenance: docs/MODEL_COMPARISON.md,
docs/URL_MODEL.md and docs/URL_ROBUSTNESS_RESULTS.json. Missing inference models return503;
no pretend predictions are substituted. To run services manually:

```powershell
# backend directory
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
# frontend directory, separate terminal
npm run dev
```

## Verify

```powershell
# backend
.venv/Scripts/python.exe -m pytest -q
# frontend
npm run gen:types
npm run typecheck
npm run lint
npm run build
```

API schema: http://localhost:8000/docs. Source contracts: backend/app/schemas.py and
backend/app/dashboard_schemas.py. Frontend API types are generated, not hand-maintained.

Demo steps and honest limitations: docs/DEMO.md. Exact continuation: docs/HANDOFF.md.
