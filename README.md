# Nigehbaan AI

Hybrid scam / phishing / abusive-message detector for Roman Urdu (university AIES project).

Combines a **stub ML classifier** with a **rule-based expert system**, exposed via FastAPI and a React web UI. WhatsApp (Baileys) integration is planned later.

## Structure

```
nigehbaan-ai/
  backend/     FastAPI API + services + ML stubs
  frontend/    Vite + React + TypeScript + Tailwind
  whatsapp/    Baileys integration (placeholder)
  notebooks/   Experiments
  report/      Project report assets
```

## Backend (Python 3.11)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs  
Health: http://localhost:8000/api/health

### Tests

```bash
cd backend
pytest
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173  

Optional: set `VITE_API_URL` in `frontend/.env` (default `http://localhost:8000`).

## API (stub)

| Method | Path | Body |
|--------|------|------|
| GET | `/api/health` | — |
| POST | `/api/analyze/text` | `{"text": "..."}` |
| POST | `/api/analyze/url` | `{"url": "..."}` |

ML models are **stubs** — replace `backend/app/services/classifier.py` and `backend/ml/train.py` when real training is ready.
