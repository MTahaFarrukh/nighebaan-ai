# SKILLS.md: Nigehbaan AI Playbooks

Reusable, step-by-step procedures for recurring tasks. Each skill says **when to use it, inputs, steps, and a done checklist**. Humans and AI agents should follow them. Always read `AGENTS.md` (rules) and `docs/TECH_DOC.md` (spec) first.

Index:
1. Add or edit an expert rule
2. Add a normalization entry / improve preprocessing
3. Add a dataset and merge it
4. Build the custom Roman Urdu scam set
5. Train and register a text model
6. Run ablations and error analysis
7. Add an API endpoint
8. Add a frontend page or component
9. Add a modality extractor
10. Handle a WhatsApp event and alert
11. Produce report artifacts
12. Debugging checklist
13. Cursor prompt template

---

## 1. Add or edit an expert rule
**When:** a scam pattern is missed, or a rule causes false positives.
**Inputs:** example messages (synthetic), desired behavior.
**Steps:**
1. Open `backend/app/resources/rules.yaml`. Each rule has `id`, `description`, `patterns`, `weight`, `axis` (`scam` or `abuse`).
2. Add patterns in all three forms where relevant: Roman Urdu spellings (include variants like `foran/furan`, `nahi/nhi`), English, Urdu script.
3. Use word boundaries in regex to avoid matching inside other words.
4. Choose a weight (0.10-0.35). Higher only for strong indicators (OTP/CNIC request, prize + link).
5. Add tests in `backend/tests/test_rules.py`: ≥2 positive examples (different spellings) and ≥2 negative examples (legit messages that look similar, e.g. a real delivery notice).
6. Run `pytest -q`. Re-run `python -m ml.evaluate` to check the hybrid risk metrics did not regress.
7. If the rule ID or weight changed, update the table in TECH_DOC 9.1.
**Done:** tests pass, hybrid macro-F1 not worse on validation, doc table updated.

---

## 2. Add a normalization entry / improve preprocessing
**When:** error analysis shows spelling variants hurting predictions.
**Steps:**
1. Collect variants from misclassified validation samples (never from the test set).
2. Add them to `backend/app/resources/normalization_map.json` as `"variant": "canonical"`. Keep canonical forms consistent (`acha`, `nahi`, `kya`, `hai`).
3. If you change a function in `services/preprocess.py`, keep it pure (string in, string out) and order-sensitive steps as listed in TECH_DOC section 7.
4. Add tests with before/after pairs, e.g. `"yaaaar ye to fraaud hai"` → expected normalized form.
5. Retrain (skill 5) and compare validation macro-F1 against the previous run in `experiments.csv`.
**Done:** tests pass, F1 not worse, before/after example saved for the report.

---

## 3. Add a dataset and merge it
**Inputs:** dataset link/file, license, label meanings.
**Steps:**
1. Download into `backend/data/raw/<name>/` (git-ignored). Do not commit data.
2. Record in `docs/DATASETS.md`: source link, download date, size, license, original labels, class counts.
3. Write a loader in `backend/ml/data_prep.py` that returns a DataFrame with columns `text, label, source, lang_hint`.
4. Map labels using the table in TECH_DOC 6.2. **Do not map sentiment negative → abusive.** Drop rows you cannot map confidently and count them.
5. Clean: drop null/empty, strip whitespace, **deduplicate across all sources** before splitting.
6. Write `data/processed/all.csv` and fixed splits (stratified 70/15/15, `random_state=42`) to `data/processed/{train,val,test}.csv`.
7. Print and save class counts per source and split (used in the report).
**Done:** loader is deterministic, counts documented, no leakage between splits (assert in code that train/val/test have no identical texts).

---

## 4. Build the custom Roman Urdu scam set
**Goal:** 400-600 scam + 300+ hard-negative normal messages, reviewed by humans.
**Steps:**
1. Create `data/raw/custom/custom_scam.csv` with columns: `text,label,theme,source,annotator`.
2. Themes to cover: prize/lottery, bank/OTP/CNIC, Easypaisa/JazzCash, BISP/Ehsaas, fake job/earning, courier/parcel, loan, crypto/investment, WhatsApp group invite, relative number-change.
3. Write ~10 hand-written seeds per theme with natural spelling variation and code-mixing. Expand using templates (slots for amounts, names, links) and, optionally, LLM-assisted variation. Set `source` honestly (`manual | template | llm_assisted`).
4. **Hard negatives:** legit messages that contain links, urgency, money words (real delivery updates, bank balance alerts, family chat about money). Label `normal`.
5. Use only fake placeholders: `03XX-XXXXXXX`, `example.com`-style or obviously fake domains, fake account numbers. **No real personal data.**
6. Two people label independently on a 100-item sample; compute Cohen's kappa (`sklearn.metrics.cohen_kappa_score`); discuss and fix disagreements.
7. Hold out 20% of the custom set as a separate "realistic test" (do not train on it).
**Done:** counts met, kappa recorded, source column filled, hold-out saved.

LLM-assist prompt (use outside the repo, review every output):
```
Generate 20 short WhatsApp-style SCAM messages in Roman Urdu (Pakistan) about <THEME>.
Vary spelling (acha/achha, nahi/nhi), tone, and length (5-40 words). Mix in some English words.
Use fake placeholders for phone numbers, links and amounts. Output as CSV: text,theme.
```

---

## 5. Train and register a text model
**Steps:**
1. Load splits from `data/processed/`.
2. Build a `Pipeline`: preprocessing (as a transformer or pre-step) → `FeatureUnion(TfidfVectorizer(word 1-2), TfidfVectorizer(char_wb 2-5))` → classifier.
3. Train the baseline (`MultinomialNB`) first and save its metrics. Never skip the baseline.
4. Tune LR / LinearSVC (wrap in `CalibratedClassifierCV` for probabilities) / RF with `RandomizedSearchCV`, stratified 5-fold, `scoring="f1_macro"`, `class_weight="balanced"`.
5. Build a soft-voting ensemble from the best 2-3 models.
6. Evaluate on **validation** for selection. Evaluate on **test once** at the end for final numbers.
7. Append every run to `backend/models/experiments.csv` (timestamp, model, params, val macro-F1).
8. Save `models/text_clf.joblib` (full pipeline), `models/label_map.json`, and `models/metrics.json` in the format of TECH_DOC 8.5.
9. Check the API loads it: `pytest tests/test_model_smoke.py`.
**Done:** reproducible with one command, metrics.json written, API prediction works, baseline vs improved table available.

---

## 6. Run ablations and error analysis
**Steps:**
1. Implement each ablation in TECH_DOC 8.3 as a flag in `ml/evaluate.py` (e.g. `--no-normalize`, `--word-only`, `--char-only`, `--no-rules`).
2. Run all, write results to `metrics.json` under `ablations` (name + rows).
3. Export misclassified **validation** samples per class to `notebooks/errors_<date>.csv`. Redact anything that looks like a phone number or CNIC.
4. Tag each error with a cause: spelling, short text, sarcasm, code-mixing, missing rule, label noise.
5. Turn the top 3 causes into concrete fixes (skills 1 and 2), then re-run.
6. Save 2-3 illustrative before/after examples and the final charts to `report/figures/`.
**Done:** ablation table complete, at least one fix cycle documented.

---

## 7. Add an API endpoint
**Steps:**
1. Define request/response models in `backend/app/schemas.py` (Pydantic v2). Reuse the common result object.
2. Create the router function in `routers/<area>.py`: validate → call a service → return schema. No logic in the router.
3. Put the logic in `services/`. Load models lazily and reuse them.
4. Handle errors with the standard JSON error shape and correct status codes (400/413/415/422).
5. Add contract tests with `httpx` + `TestClient`: success, validation error, edge cases (empty text, huge text, wrong file type).
6. Update TECH_DOC section 11.2 table, run `npm run gen:types` in `frontend/`.
7. If the endpoint touches message content, re-check the privacy rules in AGENTS.md (no logging of content).
**Done:** tests pass, docs and types updated, appears in `/docs` (Swagger).

---

## 8. Add a frontend page or component
**Steps:**
1. Add the route in the router config and a nav link; keep pages in `src/pages/`, reusable parts in `src/components/`.
2. Fetch data only via `src/api.ts` + TanStack Query hooks, using generated types.
3. Implement **loading, error, and empty** states.
4. Use Tailwind; keep the risk color convention: low = green, medium = amber, high = red, and pair color with text/icon (accessibility).
5. Charts with Recharts; keep chart data mapping in a small helper so it is testable.
6. Show flagged words masked as provided by the API; never render raw abusive lexicon beyond what the API returns.
7. Run `npm run typecheck && npm run lint && npm run build`; test at mobile and desktop widths.
**Done:** all three states handled, responsive, build passes.

---

## 9. Add a modality extractor
**Steps:**
1. Create `services/extractors/<kind>.py` exposing `extract(path: str) -> ExtractionResult(text, confidence, warnings)`.
2. Enforce limits before heavy work: file size, page count, video duration. Validate MIME via magic bytes, not just file extension.
3. Use ffmpeg with an **argument list** (no shell string). Convert audio to 16 kHz mono wav.
4. Load Whisper/EasyOCR lazily once; CPU-friendly settings (`faster-whisper` small, int8).
5. Delete temp files in `finally`.
6. For Whisper Urdu-script output: run the Urdu-script lexicon rules, and apply best-effort transliteration before ML (see TECH_DOC 10.2). Add a warning string when transliteration was used.
7. Register the kind in `/analyze/file` dispatch; add tests with tiny synthetic fixtures (a 2-second generated tone, a small generated image with text).
**Done:** limits enforced, temp cleanup verified, warnings surfaced in the API response.

---

## 10. Handle a WhatsApp event and alert
**Backend (`/whatsapp/event`):**
1. Verify `X-API-Key`. Reject if missing/invalid.
2. Check consent for this account; if absent, return `should_alert=false` without analyzing.
3. Extract text (if media) → run the standard analysis pipeline.
4. Apply `alert_policy`: risk ≥ `ALERT_THRESHOLD`, rate limit, dedupe by content hash (store only the hash).
5. Store the alert row (no text). Return result + `should_alert`, `alert_user_text`, `alert_guardian_text`.

**WhatsApp service (`whatsapp/`):**
1. On `messages.upsert`: ignore own messages, status broadcasts and groups (default).
2. Map message type → payload; download media to memory/temp and forward.
3. If `should_alert` and not `DRY_RUN`: send the user alert and guardian alert exactly as returned.
4. On disconnect: reconnect with backoff; never crash-loop; log connection state only.

**Alert text templates (backend-generated):**
- User: `⚠️ Is message mein scam/risk ke nishanat hain (risk: HIGH). Wajah: <reason categories>. Link par click na karein, OTP/PIN share na karein.`
- Guardian: `⚠️ Aap ke protected contact ko ek high-risk message mila (sender: ***1234). Wajah: <reason categories>. Message ka matn share nahi kiya gaya.`

**Done:** works in dry-run and with the real dedicated number; simulator endpoint `/simulate/whatsapp` gives the same result; no content in logs.

---

## 11. Produce report artifacts
**Steps:**
1. Generate figures from `metrics.json` via a script (`ml/make_figures.py`): model comparison bars, confusion matrices, ablation chart, class distribution. Save to `report/figures/`.
2. Architecture diagram: export the Mermaid from TECH_DOC section 3 to PNG/SVG.
3. Screenshots: Analyze (scam example, normal example, file upload), Dashboard, Model Lab, WhatsApp alert (blur numbers).
4. Fill the report outline (TECH_DOC 16) with numbers copied **from generated files**, not typed by hand.
5. Include: dataset table, preprocessing before/after, baseline vs improved vs hybrid table, kappa, limitations, ethics.
**Done:** every table/figure traceable to a script or file.

---

## 12. Debugging checklist
- **Prediction looks random:** confirm the same preprocessing is applied at train and inference (the saved pipeline must include it). Check label order via `label_map.json`.
- **Great val score, bad real-world:** look for duplicates/leakage across splits; check the custom hold-out.
- **Scam class never predicted:** class imbalance; check `class_weight`, the custom set size, and rule overrides.
- **CORS error in browser:** `ALLOWED_ORIGINS` and the dev port.
- **Types mismatch in frontend:** re-run `npm run gen:types` after backend schema changes.
- **Whisper slow/out of memory:** use `small` + int8, trim audio, enforce duration cap.
- **OCR garbage:** grayscale + upscale; try `en` only for Latin screenshots.
- **Baileys disconnects/logged out:** delete the local auth folder, re-pair with QR; if repeated, use `DRY_RUN` and the simulator for the demo.
- **Logs show message text:** stop, remove the log line, and check history before committing (privacy rule).

---

## 13. Cursor prompt template
Use this shape for any task so the agent stays inside the spec:

```
Read AGENTS.md, docs/TECH_DOC.md (sections: <N, N>) and SKILLS.md (skill <N>).

TASK: <one clear sentence>

SCOPE:
- Files to create/change: <paths>
- Do NOT touch: <paths / features>

REQUIREMENTS:
- <bullet list, referencing TECH_DOC sections>

ACCEPTANCE:
- <tests that must pass / behavior to verify>
- Run: pytest -q  (and npm run typecheck && npm run build if frontend changed)

Before coding, restate the plan in 5 lines. After coding, summarize changes, how to verify, and risks.
Never log or store message content. Do not add features outside the spec.
```
