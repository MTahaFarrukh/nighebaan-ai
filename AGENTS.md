# AGENTS.md: Nigehbaan AI

Instructions for AI coding agents (Cursor, Claude, etc.) working in this repo. Humans: read it too, it is our working agreement.

## Project in 3 lines
Nigehbaan AI detects scam/phishing and abusive **Roman Urdu** messages (text, URL, and voice/image/PDF/video converted to text) using **ML + a rule-based expert system**, shown in a **React** web app and delivered as **WhatsApp (Baileys)** alerts to the user and a guardian.
**Read `docs/TECH_DOC.md` before making any non-trivial change.** It is the spec. Use `SKILLS.md` for step-by-step playbooks.
This is a university project (CT-361 AI & Expert Systems): correctness, explainability and reproducibility matter more than cleverness.

## Stack
- Backend: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy + SQLite, scikit-learn
- Frontend: React 18 + Vite + TypeScript + Tailwind + Recharts + TanStack Query
- WhatsApp service: Node 20 + `@whiskeysockets/baileys`

## Commands
```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest -q

# ML
python -m ml.data_prep && python -m ml.train_text && python -m ml.train_url && python -m ml.evaluate

# Frontend
cd frontend && npm install && npm run dev          # http://localhost:5173
npm run typecheck && npm run lint && npm run build
npm run gen:types                                   # regenerate TS types from backend OpenAPI

# WhatsApp service
cd whatsapp && npm install && npm run dev
```

## Repo map (where things go)
- `backend/app/routers/`: thin HTTP layer only (validation, call a service, return a schema)
- `backend/app/services/`: all logic (`preprocess`, `classifier`, `expert_rules`, `url_features`, `risk_engine`, `alert_policy`, `extractors/*`)
- `backend/app/resources/`: data-like config (`rules.yaml`, `normalization_map.json`, lexicons). **Rules and lexicons are data, not code.**
- `backend/ml/`: offline training and evaluation scripts. Never imported by API request handlers.
- `backend/models/`: generated artifacts (git-ignored except `.gitkeep`)
- `frontend/src/api.ts`: the only place that calls the backend
- `whatsapp/`: thin client; **no detection logic here**, the backend decides

## Golden rules

### Privacy (non-negotiable)
1. **Never store, log, print or commit message text, transcripts, media, phone numbers or CNICs.** This includes debug prints, test fixtures with real data, and exception messages. Log IDs, hashes, rule IDs, scores only.
2. Sender identifiers are stored only as `sha256(SALT + jid)`.
3. Temp files from uploads are deleted in a `finally` block.
4. WhatsApp analysis only for consenting accounts. Guardian alerts never include message content.
5. Never put secrets, tokens, or WhatsApp auth state in git. Update `.gitignore` if you add a new secret path.
6. Do not print or hard-code the abusive lexicon in logs/UI; mask flagged words (e.g. `g***`).

### Contracts (do not break silently)
1. `backend/app/schemas.py` is the API contract. If you change it: update `docs/TECH_DOC.md` section 11, run `npm run gen:types`, fix the frontend, update tests, all in the same PR.
2. `backend/models/metrics.json` format is defined in TECH_DOC 8.5. The frontend Model Lab reads it.
3. The risk formula and thresholds are defined in TECH_DOC 9.2 and configured in `config.py`. Change them only with a reason noted in the PR.
4. Label set is exactly `normal`, `abusive`, `scam`. Risk levels are exactly `low`, `medium`, `high`.

### ML integrity
1. Deduplicate before splitting. Fixed `random_state=42`. **The test set is used once** for final numbers; tune on validation or cross-validation only.
2. Never map sentiment "negative" to "abusive".
3. Every reported number must be reproducible by a script in `backend/ml/`. No numbers typed by hand into docs.
4. Save the whole sklearn Pipeline (vectorizer + model) so inference matches training.
5. Do not claim accuracy figures you did not compute.

### Safety
1. **Never visit or fetch URLs** found in messages. URL analysis is static only.
2. Validate upload MIME type, size (`MAX_UPLOAD_MB`) and video duration (`MAX_VIDEO_SECONDS`).
3. No `eval`/`exec` on user input; no shell commands built from user strings (use argument lists for ffmpeg).
4. Alerts default to `DRY_RUN=true`.

## Code style
- **Python:** type hints everywhere, small pure functions, docstrings (1-3 lines), `ruff`/`black` formatting, no wildcard imports, no global mutable state except lazily loaded models (load once, reuse).
- **TypeScript:** `strict` mode, no `any`, functional components + hooks, API types from generated file only, handle loading/error/empty states on every data view.
- **Naming:** `snake_case` Python, `camelCase` TS variables, `PascalCase` components, kebab-case file names for non-components.
- Comments explain **why**, not what. No dead code, no commented-out blocks.
- Keep files focused (< ~300 lines). Split instead of growing.

## How to work (agent workflow)
1. **Restate the task** in one or two lines and list the files you will touch.
2. For anything bigger than a small fix, outline a short plan first and wait for confirmation if requirements are ambiguous.
3. Make the **smallest change** that satisfies the task. Do not refactor unrelated code or add features not in `docs/TECH_DOC.md`.
4. Write or update tests with the change (see testing below).
5. Run the relevant commands (tests, typecheck, lint, build) and **fix failures before reporting done**. If you could not run something, say so explicitly.
6. Finish with a short summary: what changed, how to verify, any follow-ups or risks.
7. If the spec and the request conflict, point it out and ask rather than guessing.

## Testing requirements
- New/changed preprocessing function → unit test with realistic Roman Urdu spelling variants.
- New/changed rule → one positive and one negative test in `tests/test_rules.py`.
- New endpoint → contract test (status codes, schema, error cases).
- Risk engine / alert policy changes → tests for thresholds, overrides, rate limit, consent.
- Use only synthetic/placeholder text in tests (fake numbers like `03XX-XXXXXXX`).

## Git conventions
- Branches: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`; merge via PR into `dev`; `main` stays demo-ready.
- Commits: conventional (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), imperative, one logical change each.
- Never commit: `data/raw`, `data/processed`, `models/*.joblib`, `.env`, `whatsapp/auth*`, `node_modules`, `.venv`.

## Definition of done
- [ ] Works locally end to end for the touched feature
- [ ] Tests added/updated and `pytest -q` passes
- [ ] `npm run typecheck && npm run lint && npm run build` pass (if frontend touched)
- [ ] No message content in logs, fixtures or commits
- [ ] Contracts and docs updated if changed
- [ ] Summary written (what, how to verify, risks)

## Out of scope (ask before doing)
Login/auth systems, payments, storing message content, mobile apps, new datasets/models not in the spec, replacing Baileys, deploying to cloud, adding heavy dependencies.

## Priority order when time is short
M0-M6 (scaffold → data → preprocessing → models → rules/risk → URL) come **before** multimodal and WhatsApp. The project must be complete and demoable without WhatsApp.
