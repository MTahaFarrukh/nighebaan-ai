# Viva sheet — Nigehbaan AI

Memorize the short answers. Numbers are from generated files; if you forget a digit, say “see FINAL_RESULTS.json” rather than guessing.

## A. One-minute implementation walkthrough

We detect `normal` / `abusive` / `scam` in Roman Urdu and code-mixed English. Text, URL, or file goes to FastAPI. Files become text via Whisper, OCR, or PDF extractors. Preprocessing normalizes spelling and masks phones, URLs, amounts. A voting ensemble of logistic regression and a calibrated SVM gives class probabilities. YAML rules R01–R11 fire as an expert knowledge base. A static URL model scores links without visiting them. The risk engine fuses `1-P(normal)`, rule scores, and URL probability, with an 0.85 floor for OTP-plus-link. The React app shows the result. WhatsApp is a thin client with consent; we demo the simulator because we did not pair a live dedicated account.

**Do say:** the transport is implemented with Baileys, but a live account was not paired or delivery verified. **Do not say:** hybrid is more accurate on the frozen test set (ML macro-F1 0.9216 vs hybrid 0.9140).

---

## B. Course / domain questions

### 1. Expert system vs machine learning vs hybrid

An expert system stores human knowledge (rules, weights) and infers with a transparent procedure. ML learns weights from labelled examples. Hybrid: ML for coverage on noisy Roman Urdu; rules for policy (OTP+URL must be high risk) and explanations.

### 2. Knowledge base vs inference engine

Knowledge: `rules.yaml` + abuse lexicon. Inference: `expert_rules.py` matches patterns; `risk_engine.py` combines scores and overrides. Changing a regex does not require retraining.

### 3. Certainty factors vs probabilities

Rule weights are heuristic certainties, clipped sums on scam/abuse axes. ML outputs calibrated-ish class probabilities (SVM is calibrated on train folds). Fusion is a weighted sum, not Bayes’ theorem over independent evidence. We do not claim probabilistic coherence.

### 4. Forward vs backward chaining

This is **forward**: observe text, fire matching rules, compute risk. We do not start from a goal hypothesis and search backward.

### 5. Why TF-IDF and character n-grams for Roman Urdu?

Roman Urdu spelling is unstable. Word 1–2 grams capture phrases (`paisay bhejo`); char 2–5 grams still match `nahi`/`nahin`. We did not fine-tune XLM-R (stretch, skipped).

### 6. Why not map sentiment “negative” to “abusive”?

Negative sentiment includes sadness and complaints. Abuse is harassment/hate. Mapping would poison the abusive class. UCI negative rows are **excluded**.

### 7. Train / val / test and seed 42

Deduplicate, then stratified 70/15/15, `random_state=42`. Validation for selection and ablations. Test used **once** (`final_evaluation.py`). Tuning on test would be leakage and we would fail our own spec.

### 8. Class imbalance

Train: 16,833 normal / 3,252 abusive / 454 scam. `class_weight="balanced"`. Macro-F1 treats classes equally, so it is the right headline metric. Scam **recall** matters operationally (missed scam is costly).

### 9. Precision vs recall for scams

Recall: of true scams, how many we catch (test ML 85/97 = 0.876). Precision: of predicted scams, how many are scams (0.955 ML test). Guardian alerts need high precision too; we only alert on **high** risk, but thresholds are not utility-calibrated.

### 10. Why is Naive Bayes at 0.39 macro-F1?

NB assumes token independence and was swamped by the majority class (scam recall 0.02 on validation). Linear models with balanced weights recover minority classes. Different TF-IDF caps mean it is not a pure algorithm ablation.

### 11. Why can hybrid F1 drop?

On test, four abusive rows become `scam` because high risk + scam-axis ≥ abuse-axis overrides ML. We added the “scam axis at least as strong as abuse” fix after two validation errors. Remaining overrides are the price of a safety policy.

### 12. Why keep rules if rules-only scam recall is 0.05?

Coverage is the ML job. Rules encode **institution-specific** templates and produce rule IDs a guardian can understand. The OTP+URL floor is a requirement, not a learned weight.

### 13. Why is URL macro-F1 0.996 not a miracle?

PhiUSIIL benign rows (as used) are almost all `www` + HTTPS + root. Hosts leak across random splits (2,515 val rows share train hostnames). Synthetic no-`www` stress FPR ≈ 1.0 on the deployed model. Candidates that reduced FPR failed recall gates and were not promoted.

### 14. Why never fetch URLs?

Safety (malware, tracking), ethics (do not “check” a victim’s link by visiting it), and reproducibility (static features only). Mention `tldextract`-style limits: subdomain count is approximate.

### 15. What is in SQLite?

High-risk metadata: id, timestamp, modality, label, risk, rule IDs, hashed sender if WhatsApp. **No text.**

### 16. Consent and guardian alerts

The owner opts in through `WHATSAPP_OWNER_OPT_IN`; the configured guardian is enabled from environment settings when the dedicated account connects. Obtain and document the guardian's informed agreement outside the app—the app does not verify it. There is no guardian command or `STOP` flow; disable owner opt-in and stop both services to stop monitoring. Guardian alerts are generic and contain neither message content nor sender ID. Rate limit: 3 reservations/hour per sender; identical payloads are suppressed for 24 hours.

### 17. Which WhatsApp transport shipped?

The bridge uses Baileys over WhatsApp Web's unofficial protocol; it does not launch Chromium. The bridge is implemented, but live pairing and delivery were not verified. Accounts can be banned, so use a dedicated demo account only. The official path would be Cloud API (out of scope).

### 18. Whisper Urdu limitation

Spoken Urdu often transcribes to Arabic script. We run Urdu-script rules and a transliteration bridge into the Roman model. Bridge is approximate. Smoke audio was English SAPI.

### 19. Cohen’s kappa

Agreement beyond chance for two annotators. Formula: \((\kappa = (p_o - p_e)/(1 - p_e))\). We **did not** compute a real kappa. Test-suite kappa is fake labels. Do not invent a number.

### 20. SMOTE?

Spec: `class_weight` first; SMOTE only as an experiment. We used balanced weights, not SMOTE as default.

### 21. Ensemble

Soft voting averages class probabilities of LR and calibrated SVM (top two validation models). Partial explanations use the LR component only.

### 22. Media pipeline safety

MIME/magic bytes, size, pages, pixels, duration, concurrency limit, temp delete. Tone without speech → 422, not “normal”.

### 23. Fairness

Identity terms should not fire R11. We did not publish per-dialect error rates. Spell-variant unit tests are the evidence we have.

### 24. Reproducibility

Pinned source hashes, split membership SHA-256, model manifests, `random_state=42`. Missing joblib → HTTP 503, never a silent heuristic.

### 25. If they ask “is it production ready?”

No. Unverified custom labels, URL confounding, no live WhatsApp, OCR misses, English-heavy scam proxy. It is a course-complete prototype with honest limits.

---

## C. File map if they open the laptop

| Topic | Path |
|---|---|
| API contract | `backend/app/schemas.py` |
| Risk formula | `backend/app/services/risk_engine.py` |
| Rules | `backend/app/resources/rules.yaml` |
| Preprocess | `backend/app/services/preprocess.py` |
| Frontend API | `frontend/src/api.ts` |
| Test numbers | `docs/FINAL_RESULTS.json` |
| Report | `report/Nigehbaan_AI_CCP_Report.md` |
