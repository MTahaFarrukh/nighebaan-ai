# Nigehbaan AI

**Multimodal Roman Urdu Scam and Abuse Detection with a Hybrid Expert System**

Complex Computing Project (CCP) technical report  
Course: CT-361 Artificial Intelligence and Expert Systems  
Department of Computer Science and Information Technology, NED University of Engineering and Technology  
November 2026

**Status of numbers.** Every table in this report is copied from generated artifacts under `docs/` (especially `FINAL_RESULTS.json`, `MODEL_COMPARISON_RESULTS.json`, `HYBRID_RESULTS.json`, `ABLATION_RESULTS.json`, `DATASET_INVENTORY.json`, `URL_MODEL.md`). No metric was typed from memory. Custom Roman Urdu scam labels remain **preliminary and human-unverified**. Cohen’s kappa is **not** reported ([KAPPA_STATUS.md](KAPPA_STATUS.md)).

---

## 1. Introduction, problem, and significance

Mobile messaging in Pakistan is routinely used for banking, government disbursements (BISP / Ehsaas), courier tracking, and family coordination. The same channel is used for phishing (OTP and CNIC harvesting), payment fraud (Easypaisa / JazzCash impersonation), lottery lures, relative-emergency scams, and abusive language. Much of this traffic is written in **Roman Urdu**: Urdu words spelled in Latin script, mixed with English, with unstable spelling (`nahi` / `nahin` / `nhi`). Off-the-shelf English spam filters and Arabic-script Urdu models both miss this register.

**Nigehbaan AI** is a local decision-support system that classifies a message as `normal`, `abusive`, or `scam`, and assigns a risk level `low`, `medium`, or `high` with an explanation. It does not block or delete messages. A human remains accountable.

**Inputs.** Pasted text; a single URL; or a file (image, PDF, audio, video) from which text is extracted.  
**Outputs.** Label, class probabilities, fired expert-rule IDs, masked flagged words, static URL findings (never fetched), risk score and level, latency, and warnings.

Two delivery channels share one FastAPI backend:

1. A React web application (Analyze, Dashboard, Model Lab, Settings, About).
2. An optional WhatsApp bridge for a **consenting dedicated demo account**, with guardian alerts that never contain message content. Live pairing was not completed for this submission; the Settings simulator exercises the same alert policy.

The work is significant for the course because it combines **supervised machine learning**, a **rule-based expert system**, evaluation discipline (baseline, tuning, ensemble, ablations, one-shot test), multimodal extraction, and explicit privacy constraints. It is a university prototype, not a production safety product.

### 1.1 Objectives

- Detect scam/phishing and abusive content in Roman Urdu and code-mixed English.
- Show a measurable improvement over a Naive Bayes baseline using multiple learners and a voting ensemble.
- Keep expert knowledge in data files (`rules.yaml`, lexicons), not hard-coded Python branches.
- Fuse ML, rules, and a static URL model with a documented risk formula.
- Visualize results and model metrics without storing user message text.

### 1.2 Non-goals

Login systems, payments, storing chat content, moderating other people’s accounts without consent, visiting submitted URLs, and fine-tuning large language models were out of scope.

---

## 2. Related work and datasets

Public Roman Urdu resources exist for **sentiment** and **hate speech**, not for financial scam SMS. Using sentiment “negative” as a proxy for abuse would confuse complaint language with harassment. The project therefore maps datasets conservatively and builds a **custom scam set** for the missing class.

### 2.1 Related work (positioning)

| Line of work | Relevance | Gap we address |
|---|---|---|
| English SMS spam (UCI SMS Spam Collection) | Template phishing, urgency, prize language | Language mismatch with Roman Urdu |
| Hate-speech datasets (RUHSOLD) | Abusive class in Roman Urdu | Not scam/phishing |
| UCI Roman Urdu sentiment | Everyday Roman Urdu texture | Negative ≠ abusive |
| Phishing URL feature models (PhiUSIIL and similar) | Static lexical URL cues | Must not fetch pages; source shortcuts can inflate scores |
| Commercial spam filters | Production scale | Closed, English-centric, not explainable for a course expert system |

Nigehbaan AI is a **hybrid** of a classical TF-IDF classifier and a forward, pattern-matching expert system. Deep transformers (for example XLM-R) were listed as an optional stretch and were not trained.

### 2.2 Dataset table

Official files were audited in memory on 2026-11-09 (`docs/DATASET_INVENTORY.json`). Public corpus text is not committed.

| Source | License | Published / audited rows | Original labels | Project mapping |
|---|---|---|---|---|
| UCI Roman Urdu Data Set | CC BY 4.0 | 20,229 rows | negative 5,286; neutral 8,929; positive 6,013; unknown 1 | Positive/neutral → `normal`. **Negative excluded** (not abusive) |
| RUHSOLD task 1 (train/val/test TSVs) | MIT | 7,209 + 801 + 2,003 | 0 abusive-family, 1 normal | 0 → `abusive`, 1 → `normal` |
| UCI SMS Spam Collection | CC BY 4.0 | 5,574 | ham 4,827; spam 747 | ham → `normal`, spam → `scam` (**English proxy**) |
| Custom Roman Urdu (project) | not assigned | Draft 800 (500 scam / 300 normal) | `normal` / `scam` | Retained; **human review pending** |
| UCI PhiUSIIL phishing URL | CC BY 4.0 | 235,795 raw; 234,687 usable | source 0 = phishing, 1 = legitimate | **Inverted:** phishing = 1, benign = 0 |

SMS spam is a **proxy** for scam, not a claim that English spam equals Pakistani mobile fraud. Custom items are LLM-assisted templates with placeholder numbers such as `03XX-XXXXXXX`. They are not real user messages.

### 2.3 Frozen text splits

Deduplicate first, then stratified 70/15/15 with `random_state=42`, plus a disjoint custom hold-out. Counts from `docs/FINAL_RESULTS.json`:

| Split | Rows | normal | abusive | scam |
|---|---:|---:|---:|---:|
| Train | 20,539 | 16,833 | 3,252 | 454 |
| Validation | 4,401 | 3,607 | 697 | 97 |
| Test (used once) | 4,402 | 3,608 | 697 | 97 |
| Custom hold-out | 16 | 6 | 0 | 10 |

The custom hold-out is far smaller than the specification target (400–600 scam + 300 hard negatives). Results on it are template-family scores, not prevalence estimates.

### 2.4 Frozen URL splits

Canonical URL deduplication and one conflicting-label group removal precede a stratified 70/15/15 split (`docs/URL_DATASET_INVENTORY.json`).

| Split | Rows | benign (0) | phishing (1) |
|---|---:|---:|---:|
| Train | 164,280 | 94,394 | 69,886 |
| Validation | 35,203 | 20,227 | 14,976 |
| Test (used once) | 35,204 | 20,228 | 14,976 |

Validation rows sharing a training hostname: **2,515**. Random URL splits are not unseen-brand evaluation.

---

## 3. Methodology and architecture

Figure 1 (`report/figures/fig1_architecture.svg`) is the methodology diagram required by the CCP brief.

The backend is the **single source of truth**. The WhatsApp process is a thin client: it forwards events and sends only alert strings the backend returns. Detection logic is not duplicated in Node.

**Pipeline for any modality**

1. Extract text if needed (Whisper, EasyOCR, PyMuPDF, ffmpeg keyframes). Temporary files are deleted in `finally` blocks.
2. Preprocess (Unicode, entity masks, Roman Urdu lexical map, optional stopwords).
3. Run in parallel conceptually: ML class probabilities; expert-rule flags; static URL probability if URLs were extracted.
4. Risk engine fuses scores, applies the credential+URL floor, maps thresholds, and may override the label to `scam`.
5. Return an explanation. For WhatsApp events, apply consent, rate limit, and dry-run policy.

```text
extract → preprocess → (ML  ‖  rules  ‖  URL) → risk engine → UI / alert decision
```

### 3.1 Expert-system view (course mapping)

| Expert-system concept | Implementation |
|---|---|
| Knowledge base | `backend/app/resources/rules.yaml` (R01–R11) and abuse lexicon file |
| Working memory | Cleaned text, extracted URLs, ML probabilities |
| Inference | Deterministic regex/keyword matching (forward, data-driven) |
| Certainty factors | Rule weights in [0,1], summed per axis and clipped at 1 |
| Explanation facility | Fired rule descriptions + partial LR term cues |
| Separation of knowledge and inference | YAML/lexicons are data; `expert_rules.py` / `risk_engine.py` interpret them |

This is **not** a full production Rete engine. It is a transparent rule layer that examiners can open and edit without retraining.

### 3.2 Stack

Python 3.11, FastAPI, scikit-learn, SQLite (high-risk **metadata** only), React 18 + Vite + TypeScript, Node WhatsApp Web client (`whatsapp-web.js`). The original design mentioned Baileys; the implemented bridge uses WhatsApp Web in Chromium. Both are unofficial clients. A dedicated number is mandatory; personal accounts are forbidden.

---

## 4. Preprocessing

Implementation: `backend/app/services/preprocess.py`. Order is fixed and unit-tested with synthetic Roman Urdu variants (`docs/PREPROCESS_EXAMPLES.json`). Submitted URLs are **never fetched**.

1. NFKC Unicode normalization; strip controls.
2. Script detection: Urdu-letter ratio > 0.3 selects an Urdu-script path for rules.
3. Extract URL candidates **before** lowercasing.
4. Lowercase; mask email → `emailtoken`, URL → `urltoken`, money → `amounttoken`, phone → `phonetoken`.
5. Emoji → `emojitoken` plus a count feature.
6. Collapse repeated letters to at most two (`yaaaar` → `yaar`).
7. Lexical map (`normalization_map.json`): `achha`/`accha` → `acha`, `nahin`/`nhi` → `nahi`, `kia` → `kya`, and similar.
8. Drop punctuation except `!`/`?` counts kept as features.
9. Optional Roman Urdu stopword removal (**disabled** after ablation).
10. Handcrafted features for rules: length, uppercase ratio, digit ratio, URL flags.

Vectorization at training time: TF-IDF **word 1–2 grams** plus **character 2–5 grams** (`char_wb`). Character n-grams absorb spelling variation that word tokens miss. The saved sklearn `Pipeline` includes the vectorizer so inference matches training.

### 4.1 Before / after examples (synthetic only)

| Input (synthetic) | Expected cleaned form |
|---|---|
| `yaaaar ye to fraaud hai!!!` | `yaar ye to fraud hai` |
| `Achha nhi, kia abhi paise bhjo?` | `acha nahi kya abhi paisay bhejo` |
| `PKR 5,000 example.com/demo 03XX-XXXXXXX` | `amounttoken urltoken phonetoken` |
| `demo@example.com par reply karo` + emoji | `emailtoken par reply karo emojitoken` |

Urdu-script messages keep Urdu letters; rules also carry Urdu patterns. Whisper transcripts of spoken Urdu are typically Arabic script; a transliteration bridge is approximate.

Ablation note (validation, fixed LR): raw original text scored **0.9282** macro-F1 versus normalized **0.9263**. The report does **not** claim that the full normalizer improves this validation mixture. Stopword removal was slightly worse (0.9249); it stays off.

---

## 5. Models and expert system

### 5.1 Text classifiers

| Role | Model | Validation macro-F1 | Validation scam recall |
|---|---|---:|---:|
| Baseline | TF-IDF + Multinomial Naive Bayes | 0.3924 | 0.0206 |
| Improved | Logistic Regression (balanced, C selected on 5-fold train CV) | 0.9263 | 0.9485 |
| Improved | Linear SVM, calibrated on training folds only | 0.9325 | 0.9072 |
| Improved | Random Forest (balanced) | 0.9115 | 0.8866 |
| Selected | Equal-weight soft-voting **LR + SVM** | **0.9367** | 0.9381 |

Source: `docs/MODEL_COMPARISON.md` / `MODEL_COMPARISON_RESULTS.json`. Split: validation. Data review status: `preliminary_human_unverified`.

Tuning used stratified five-fold search on **train** with scoring = macro-F1 and `random_state=42`. SVM probabilities come from calibration on training folds, not from the test set. The Naive Bayes run used an uncapped TF-IDF vocabulary; later models capped word/char features (15k / 25k), so the baseline comparison is practical rather than an isolated classifier ablation.

**Why the baseline is weak.** The training mix is imbalanced (16,833 / 3,252 / 454). Multinomial NB independently over-predicts `normal` (validation scam recall 0.0206). Linear models with `class_weight="balanced"` recover minority recall. This jump is expected; it is not evidence of test leakage. Test data were held out until a later one-shot evaluation.

### 5.2 Expert rules (knowledge base)

`rule_score` on an axis is `min(1, sum of fired weights)`. Abuse (R11) is a separate axis. Fusion uses `max(scam_axis, abuse_axis)` so abuse and scam are not added into one pile.

| ID | Description | Weight | Axis |
|---|---|---:|---|
| R01 | Contains a link | 0.15 | scam |
| R02 | Shortened or suspicious host | 0.20 | scam |
| R03 | Urgency language | 0.15 | scam |
| R04 | Prize / lottery | 0.30 | scam |
| R05 | Credential / OTP request (with request verbs; safety negation excluded) | 0.35 | scam |
| R06 | Payment transfer | 0.25 | scam |
| R07 | Institutional impersonation | 0.20 | scam |
| R08 | Threat of block / FIR | 0.20 | scam |
| R09 | Unrealistic earnings | 0.25 | scam |
| R10 | Number-change / relative emergency | 0.25 | scam |
| R11 | Abusive lexicon | 0.30 | abuse |

R05 requires a request context (`bhejo`, `share`, …) and excludes clause-local advice such as “Never share your OTP.” Flagged abuse tokens are masked in the UI (`g***`). The lexicon is not printed in this report.

### 5.3 Risk engine

From `backend/app/config.py` defaults and `risk_engine.py` (TECH_DOC §9.2):

```
p_ml    = 1 - P(normal)
r_rules = max(scam_rule_score, abuse_rule_score)
r_url   = max P(phishing) over extracted URLs, if the URL model is available

with URL:    risk = 0.50 p_ml + 0.30 r_rules + 0.20 r_url
without URL: risk = 0.60 p_ml + 0.40 r_rules

if R05 and (has URL or R01): risk = max(risk, 0.85)

low < 0.35 ≤ medium < 0.70 ≤ high
```

Final label is ML argmax unless risk is **high** and the scam axis is positive and **at least as strong as** the abuse axis, in which case the label becomes `scam`. That extra predicate was added after a validation fix cycle: two abuse messages with incidental scam cues had been overridden (`docs/RULES_RISK.md`).

Weights were **not** replaced by a harmful-vs-normal F1 sweep. Spec defaults remain deployed. Guardian-alert calibration is still pending.

### 5.4 URL module

Features are static: length, host length, dots, approximate subdomains, digits, hyphens, `@`, IP-as-host, https, shortener, suspicious TLD, lexical keywords, path length, query arity, character entropy. Models compared on validation: LR 0.9957, RF 0.9960, **Gradient Boosting 0.9964** (selected). No HTTP, DNS, or page fetch.

A robustness audit found that **all source-labelled benign training URLs** in this extract have `www`, HTTPS, and root paths. Synthetic no-`www` / path stress therefore produced extreme false-positive rates on the deployed model (benign FPR ≈ 1.0 on those stresses; `docs/URL_ROBUSTNESS_RESULTS.json`). Candidates with augmentation failed the recall/FPR promotion gates and were **not** deployed. Live smoke: `https://example.com/demo` can score high. This is disclosed on the Analyze page. We do not whitelist demo domains to hide the behaviour.

### 5.5 Multimodal extractors

| Input | Method | Limits |
|---|---|---|
| Audio | ffmpeg → 16 kHz mono → faster-whisper `small` | size / duration caps |
| Image | EasyOCR English + Urdu | pixel cap |
| PDF | PyMuPDF; OCR if no text | page cap |
| Video | audio → Whisper; keyframes → OCR | 60 s default cap |

Synthetic PDF, image, spoken English audio, spoken video, and non-speech tone rejection were smoke-tested (`docs/MEDIA.md`). OCR missed a URL in a PNG/video fixture (medium instead of high). Realistic Urdu speech quality is unevaluated.

---

## 6. Results

Working targets in the spec were macro-F1 ≥ 0.80 and scam recall ≥ 0.85 **on test**, as aspirations, not promises. The frozen one-shot test (`docs/FINAL_RESULTS.json`, `evaluation_split: test`, `data_review_status: preliminary_human_unverified`) meets those numeric targets on the **proxy mixture**, with the caveats in §6.5.

### 6.1 Text test (n = 4,402)

| System | Macro-F1 | Accuracy | Scam P | Scam R | Scam F1 |
|---|---:|---:|---:|---:|---:|
| ML only (deployed ensemble) | 0.9216 | 0.9580 | 0.9551 | 0.8763 | 0.9140 |
| Hybrid (ML + rules + risk) | 0.9140 | 0.9571 | 0.9140 | 0.8763 | 0.8947 |

Per-class ML test F1: normal 0.9745, abusive 0.8762, scam 0.9140. Support: 3,608 / 697 / 97.

ML confusion (rows true, columns predicted: normal, abusive, scam):

```
3534  70   4
  99 598   0
  12   0  85
```

Hybrid confusion:

```
3534  70   4
  99 594   4
  12   0  85
```

Hybrid is **slightly worse** on macro-F1 because four abusive messages were labelled `scam` (the high-risk scam-axis override). Scam recall is unchanged (85/97). Hybrid is retained for **explainability** and the OTP+URL floor, not because it wins this test mixture.

Risk levels on the text test (hybrid): low 3,664; medium 644; high 94.

### 6.2 Custom hold-out (n = 16, synthetic templates)

Hybrid and ML both report macro-F1 **0.7922**, accuracy 0.8125, scam recall 0.90 (9/10), with two normal→scam errors and one scam→normal. There is no abusive support. This set is too small and too template-like for external claims.

### 6.3 URL test (n = 35,204)

| Metric | Value |
|---|---:|
| Macro-F1 | 0.9960 |
| Accuracy | 0.9961 |
| Benign recall | 0.9994 |
| Phishing recall | 0.9917 |

Confusion (true \ predicted benign, phishing): 20,215 / 13 ; 125 / 14,851.

These scores are **source-specific**. They coexist with known false positives on reserved and non-`www` URLs that do not resemble the benign training shortcut. Do not present 0.996 as live phishing accuracy.

### 6.4 Ablations (validation, fixed balanced LR)

| Variant | Train rows | Macro-F1 | Scam recall |
|---|---:|---:|---:|
| normalized word+char | 20,539 | 0.9263 | 0.9485 |
| word only | 20,539 | 0.9000 | 0.9588 |
| char only | 20,539 | 0.9125 | 0.9691 |
| stopwords removed | 20,539 | 0.9249 | 0.9485 |
| without SMS in training | 16,938 | 0.6259 | 0.0206 |
| raw original text | 20,539 | 0.9282 | 0.9381 |
| lexical map off | 20,539 | 0.9252 | 0.9485 |

Removing SMS from training collapses scam recall on a validation set that still contains SMS. That measures **domain match**, not Roman Urdu scam prevalence.

Hybrid validation (`docs/RULES_RISK.md`): ML-only and hybrid both 0.9367 macro-F1 and 0.9381 scam recall; rules-only 0.4290 macro-F1 and **0.0515** scam recall. Rules are a sparse knowledge layer, not a standalone classifier.

### 6.5 Error analysis (aggregate, no message text)

Categories, not examples:

- **Class imbalance and proxy scam labels.** Most `scam` training rows are English SMS. Roman Urdu scam behaviour is under-represented.
- **Unreviewed custom templates.** Family leakage (shared prefixes) can inflate hold-out scores.
- **Hybrid overrides.** Four test abuse rows became `scam` under the high-risk rule. Explainability has a precision cost on this mixture.
- **URL confounding.** Benign class in PhiUSIIL (as used) is entangled with `www`+HTTPS+root path.
- **OCR / ASR.** Missing URLs in images; English-only speech smoke tests.

Fairness across dialect/spelling was probed only via preprocessing unit tests, not a demographic error table. Neutral identity terms are not in the abuse list by design; a dedicated fairness slice was not computed.

---

## 7. User interface and WhatsApp integration

### 7.1 Web application

Five hash-routed pages:

| Page | Role |
|---|---|
| Analyze | Text / URL / File. Risk meter, rule chips, masked words, warnings, latency |
| Dashboard | High-risk **metadata** history (id, time, modality, label, risk, rule IDs). No text |
| Model Lab | Real validation metrics, confusion matrices, ablations from `/api/metrics/models` |
| Settings | Read-only thresholds, WhatsApp QR proxy, **Simulate WhatsApp** |
| About / Ethics | Privacy, limitations, human judgment |

API access is centralized in `frontend/src/api.ts` with types generated from OpenAPI.

### 7.2 WhatsApp (network / real-time requirement)

Implemented:

- Dedicated-account bridge (`whatsapp/`, `whatsapp-web.js` + headless Chromium).
- Authenticated backend events, owner opt-in, guardian confirmation command and `STOP`.
- Hashing of sender identifiers (`sha256(SALT + jid)`).
- Rate limit (three reservations per sender per hour) and 24-hour identical-alert suppression.
- Alert copy contains **reason categories**, never message bodies.
- Settings simulator for demos without pairing.

**Not completed for this submission:** pairing a dedicated live account and delivering a real guardian SMS. Examiners should use **Settings → Simulate WhatsApp alert**. Unofficial WhatsApp clients can violate terms of service; only a throwaway demo number is acceptable.

### 7.3 Demo screenshots

Live screenshots are captured at demonstration time using [DEMO_SCRIPT.md](DEMO_SCRIPT.md) (six scripted cases). They are omitted from Git so that no accidental personal data or QR material is committed. Generated scientific figures (architecture, bar charts, confusion matrices) are in `report/figures/`.

---

## 8. Ethics, privacy, and limitations

**Privacy.** No live message text, transcript, media, URL string, phone number, or CNIC is stored in the alert history. Temporary uploads are deleted. Abuse terms are masked. Secrets and WhatsApp auth directories are git-ignored.

**Transparency.** Each result lists rule IDs and an explanation. LR coefficient × TF-IDF cues are **partial** (linear component of a voting ensemble, not full SHAP).

**Accountability.** The system warns; it does not auto-block. Thresholds live in configuration. Dashboard rows are metadata for later discussion.

**Consent.** WhatsApp analysis is only for an opted-in linked account. Guardians opt in with a short-lived command and may send `STOP`.

**Limitations (must be stated in viva).**

1. Custom scam labels are unverified; kappa is absent.
2. Hybrid test macro-F1 is below ML-only.
3. URL 0.996 is not a real-world guarantee; `example.com` may look “phishy” to the deployed model.
4. English SMS is a scam proxy.
5. Urdu speech and OCR URL recovery are incomplete.
6. WhatsApp is unofficial and was not live-paired.
7. No claim that low risk means “safe to click.”

---

## 9. Challenges

1. **Missing Roman Urdu scam corpus.** Building 400–600 reviewed scams with two annotators exceeded the time available. The team chose honesty (unverified draft) over fabricated kappa.
2. **Label ontology.** Sentiment, hate speech, and fraud are different tasks. Refusing to map “negative” to “abusive” reduced training volume and prevented a scientifically invalid shortcut.
3. **Imbalance.** Scam is ~2% of the frozen train split. Balancing weights and SMS augmentation help the proxy task and can mislead if read as field prevalence.
4. **URL source shortcuts.** High validation F1 coexisted with almost certain false positives on simple path/`www` stresses. Promotion gates correctly **rejected** “fixed” models that lost phishing recall.
5. **Unofficial messaging APIs.** Baileys vs WhatsApp Web vs Cloud API is a ToS and reliability problem, not just an engineering preference.
6. **Multimodal error modes.** Extraction failures look like model failures (OCR dropping a URL lowers risk).
7. **Expert-system credit.** Rules-only scam recall of 0.05 on validation is easy to attack in viva. The defence is that rules encode **policy** (OTP+link must be high risk) and **explanations**, while ML covers coverage.

---

## 10. Conclusion, future work, and references

Nigehbaan AI is a complete **local prototype**: Roman Urdu preprocessing, a documented Naive Bayes baseline, tuned linear/ensemble models, an eleven-rule expert knowledge base, a static URL model, multimodal extractors, a React interface, and a privacy-preserving alert policy. On the frozen text test the ensemble reaches macro-F1 **0.9216** and scam recall **0.876**. The hybrid layer does not beat that F1; it is justified by floors, rule IDs, and inspectable knowledge.

It is **not** a finished safety product. The marks-critical remaining research work is human review (kappa), independently labelled URLs, Urdu ASR quality, and a live dedicated-number demo if the department requires network monitoring beyond the simulator.

**Future work.** (1) Two-annotator custom set and a new corpus version—without retuning on the consumed test split. (2) URL features that are not confounded with `www`/HTTPS/root, using reviewed hard negatives, still without fetching. (3) Official WhatsApp Cloud API if a business account is approved. (4) Stronger Urdu OCR/ASR. (5) Guardian-threshold calibration on a utility metric, not generic F1.

### References (datasets and implementation sources)

1. Sharf, Z. & Rahman, H. A. Roman Urdu Data Set. UCI Machine Learning Repository. CC BY 4.0.  
2. Shakeel, H. et al. RUHSOLD: Roman Urdu Hate Speech. GitHub, MIT license, commit inventoried in `DATASET_INVENTORY.json`.  
3. Almeida, T. A. & Hidalgo, J. M. G. SMS Spam Collection. UCI. CC BY 4.0.  
4. Prasad, A. & Chandra, S. (2024). PhiUSIIL Phishing URL (Website) Dataset. UCI. CC BY 4.0.  
5. Project specification: `docs/TECH_DOC.md`, evaluation artifacts under `docs/`.  
6. Pedregosa et al. Scikit-learn: Machine Learning in Python. JMLR, 2011.

### Appendix A — Figure index

| File | Content | Source JSON |
|---|---|---|
| `figures/fig1_architecture.svg` | System diagram | TECH_DOC §3 |
| `figures/fig2_text_val_macro_f1.svg` | Text model comparison | MODEL_COMPARISON_RESULTS.json |
| `figures/fig3_hybrid_val_macro_f1.svg` | ML / rules / hybrid | HYBRID_RESULTS.json |
| `figures/fig4_ablation_val_macro_f1.svg` | LR ablations | ABLATION_RESULTS.json |
| `figures/fig5_text_test_ml_confusion.svg` | Test CM, ML | FINAL_RESULTS.json |
| `figures/fig6_text_test_hybrid_confusion.svg` | Test CM, hybrid | FINAL_RESULTS.json |
| `figures/fig7_url_test_confusion.svg` | URL test CM | FINAL_RESULTS.json |
| `figures/fig8_train_class_counts.svg` | Train imbalance | FINAL_RESULTS.json |

Regenerate with `python -m ml.make_figures` from `backend`.

### Appendix B — Reproduction (no retraining)

```powershell
powershell -File scripts/start-demo.ps1
# backend tests
cd backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ml.make_figures
```

Do not rerun `ml.train_improved`, `ml.train_url`, or `ml.final_evaluation`. Those runs are frozen.
