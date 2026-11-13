# Agent handoff - current state

Repo: D:/AIES-Project/nighebaan-ai. Branch: feat/data-prep.
All changes remain LOCAL and uncommitted. Preserve them. No PR/merge; only origin/main exists.
Read AGENTS.md, TECH_DOC.md and this handoff. Update this file as work progresses.

## Completed
- M1 ingestion/split code, official-source inventory, 800-item custom synthetic draft and review tools.
- Custom review is blank; user authorized preliminary development/training without manual labels.
- Public corpus text is fetched/processed ONLY in memory. Do not save it or log examples.
- M2 normalizer/features/serializable sklearn adapter implemented. See PREPROCESSING.md.
- M3 preliminary NB baseline trained: models/nb_preliminary_001; macro-F1 0.39240699394266326.
- M4 preliminary model comparison completed: models/m4_preliminary_001.
- LR/SVM/RF tuned on five training folds; SVM calibrated on training only.
- Top-two LR/SVM soft-voting ensemble selected. Reload/probability integrity verified.
- Same source fingerprints and every partition membership matched M3 before training.
- No test/custom-holdout evaluation. All scores are preliminary validation, human-unverified.

## Artifacts and commands
- Selected full model: backend/models/m4_preliminary_001/text_clf.joblib (ignored).
- Results: docs/MODEL_COMPARISON_RESULTS.json and docs/MODEL_COMPARISON.md.
- Source pinning: docs/DATASET_INVENTORY.json; split hashes: model run data_manifest.json.
- Baseline inputs: 20539 train / 4401 val; test and custom holdout remain unevaluated.
- Public corpus CSVs do NOT exist locally; do not assume data/processed has train.csv.
- Reconstruct via ml.train_preliminary.prepare_partitions(); verify against frozen manifest.
- Resume command from backend: .venv/Scripts/python.exe -u -m ml.train_improved --output models/m4_preliminary_001
- Run is already COMPLETE. Do not rerun training. Read stored results first.
- Runner fingerprint guards resumption; changed code/config requires a new run directory.
- Model search caps TF-IDF at 15k word/25k char; NB was uncapped. Not an isolated classifier ablation.
- Run-local experiments.csv validation values refer to the selected model in each family, not each CV candidate.

## Exact next work
1. API integration COMPLETE: trusted local artifact promoted to backend/models/text_clf.joblib.
   Manifest fingerprint verified before lazy joblib loading; class probabilities aligned by classes_.
   Full raw-input pipeline includes ModelInputSanitizer with training-time frozen lexical map.
   Missing/corrupt artifact returns HTTP 503, not heuristic text predictions. Empty cleaned input -> 422.
   Text explanations/UI identify preliminary ensemble; URL endpoint explicitly remains heuristic.
2. M4 preprocessing/feature/SMS ablations COMPLETE: seven fixed balanced-LR variants.
   See docs/ABLATIONS.md and docs/ABLATION_RESULTS.json. Original raw text was recovered
   in memory by (source, normalized text) mapping; no raw models/text were persisted.
   Deployed ensemble is unchanged. Rules-only/hybrid comparison remains M5 work.
3. M5 rules/risk + validation threshold tuning, M6 URL model, M8 frontend, then M7/M9.
Model comparison, API integration and seven M4 ablations are complete for preliminary data. Final reviewed-data evaluation remains pending. Never tune on test.

## Environment / verification
Python not on PATH: backend/.venv/Scripts/python.exe (3.11).
From backend: .venv/Scripts/python.exe -m pytest -q.
Run Ruff from REPO ROOT (import classification differs if invoked from backend):
set UV_CACHE_DIR to a temp cache; uv tool run --from ruff ruff check <paths>.
M4 core suite passed 71 tests; added resume test passed separately; final suite result below.
Frontend npm ci/build previously passed. Node/npm available. Preview localhost:5173 and
backend localhost:8000 were launched hidden; check health before restarting any process.
D: writes require sandbox escalation. One M4 write approval timed out; smaller retry succeeded.
No personal text/phone logs, no corpus/model commits, no URLs fetched from message text.
No fabricated human review/kappa. User wants continuity without repeating setup.

Final M4 comparison verification: 72 tests passed; Ruff lint/format and git diff --check passed. Selected ensemble reload verified. Existing Starlette/httpx deprecation warning only.

## Latest integration verification
81 backend tests passed; Ruff lint/format passed; npm run build passed (includes tsc).
Frontend has no separate lint/typecheck scripts; do not claim those commands ran.
Live backend restarted on port 8000: launcher PID 5900 (verify ownership before any restart).
Live HTTP text analysis confirmed trained-model explanation and probabilities summing to 1.
Live URL analysis confirmed heuristic explanation; Vite module shows updated model wording.
Preview: http://localhost:5173/ . Refresh the open tab if necessary.
No training or test-set evaluation occurred during integration.
Promotion tool: from backend, .venv/Scripts/python.exe -m ml.promote_text.
Promotion refuses overwrites. Existing promotion is complete; do not repeat it.
API model is an outer raw-input cleaning wrapper around the selected saved ensemble;
source training artifact and selection results remain unchanged in m4_preliminary_001.
Tests use synthetic model fixtures so clones do not need local joblib files; optional real artifact
smoke test skips when missing. Local .joblib artifacts stay ignored; metadata is aggregate only.
Next actual work: M5 rules/risk validation and hybrid ablation, then M6 URL model.

## Completed M4 ablations - 2026-11-10
Added ml/evaluate.py. prepare_partitions(raw_lookup=...) recovers original texts IN MEMORY
keyed by source plus frozen normalized text. Default dataset preparation behavior is unchanged.
Seven fixed balanced-LR variants: normalized both, word-only, char-only, stopwords removed,
without SMS training, original raw text, lexical normalization disabled. C from saved LR CV.
No-SMS keeps validation unchanged. Lexical-only variant preserves other sanitizer steps.
No ablation model or public text is saved; aggregate checkpoint metrics only.
Run from backend: .venv/Scripts/python.exe -u -m ml.evaluate --output models/ablations_preliminary_001
--variant permits selected variants; raw_both is actual recovered original text, not cleaned data.
Resume guarded by loader/runner hashes and partition membership. Do not edit during a run.
Rules-only/hybrid comparison remains pending until M5. The seven-variant run completed successfully.

## Latest ablation completion / exact continuation
Results stored at backend/models/ablations_preliminary_001; all seven aggregate checkpoints exist.
Reference normalized LR exactly matches the prior LR result. See generated docs/ABLATIONS.md.
Do not rerun completed ablations. Publisher: python -m ml.report_ablations (from backend).
Publisher updates docs/ABLATION_RESULTS.json, docs/ABLATIONS.md, models/metrics.json ablations,
and run-keyed models/experiments.csv. Trained API model and its fingerprint remain unchanged.
Raw original LR scored slightly higher than full normalization: no broad normalization benefit claim.
Keep stopwords disabled based on this comparison; no-SMS loses substantial validation performance.
This is evidence on the existing mixture, not a claim about real-world Roman Urdu scam prevalence.
M5 next: move expert rules/lexicons into resources, implement spec risk formula and explanations,
add positive/negative tests per rule and thresholds, compare ML-only/rules-only/hybrid on validation.
Use original raw mappings for rule cues; do not tune/evaluate test or custom holdout.
Validation error analysis should save only aggregate categories/hashes, never real message examples.

Final ablation verification: 87 tests passed; Ruff checks and git diff --check passed. Test/custom hold-out not evaluated. API model not replaced.

## Active M5 - 2026-11-10
Rules moved to JSON-compatible YAML 1.2 resources/rules.yaml (R01-R11); existing abuse lexicon
moved to its own resource without printing it. Outputs mask abuse words, use rule IDs.
R05 requires request context and excludes clause-local safety negation. Rules use raw request text.
Risk now uses 1-P(normal), configurable fusion weights, distinct scam/abuse axes and credential+URL floor.
No URL probability is invented before M6; no-URL fusion used when URL model unavailable.
Rule fusion uses max(scam_axis,abuse_axis); unknown/duplicate rule IDs add no extra weight.
High risk plus scam-axis flags overrides final label to scam per spec. URL endpoint remains heuristic.
Hybrid validation command from backend:
.venv/Scripts/python.exe -u -m ml.evaluate_hybrid --output models/m5_validation_001
This compares ML-only, rules-only and hybrid and audits candidate weights/thresholds on validation.
Spec defaults retained pending interpretation: binary harmful F1 is NOT guardian-alert utility.
Original validation messages remain only in memory; report aggregate error categories only.
Tests: initial full suite 107 passed, then 21 targeted rules/risk/configuration tests passed.
Await completion before reporting validation results. Existing preview backend needs restart after changes.

## Latest M5 completion / exact continuation - 2026-11-10
This section supersedes earlier M5-pending and active-run notes above.
Rules/risk implementation and validation fix cycle completed. Both m5_validation_001 and
m5_validation_002 finished; do not rerun. Second run uses dominant-scam-axis override,
fixing two abuse-to-scam overrides. Generated numbers: docs/RULES_RISK.md and HYBRID_RESULTS.json.
Publisher: from backend, .venv/Scripts/python.exe -m ml.report_hybrid.
Root metrics retain feature ablations plus ML/rules/hybrid comparison; ablation publishers preserve each other.
No model retraining/replacement, test predictions or custom hold-out evaluation occurred.
Defaults retained after diagnostic sweep; alert-severity calibration and top n-gram attribution remain pending.
R01-R11 flags and masked flagged_words integrated; frontend no longer reprints raw input in results.
109 backend tests passed. npm run build passed (includes tsc); no separate lint/typecheck scripts exist.
Ruff check passed for M5 files; git diff --check passed. Existing Starlette/httpx warning remains.
Next: M6 static URL features/model and API integration per TECH_DOC 10.1; audit dataset/source
and frozen splits before training; never fetch submitted URLs. Then M8 pages, M7 media, M9 WhatsApp.
M5 alert calibration/attribution follow-ups must remain visible; do not claim all milestone criteria complete.
Changes remain local on feat/data-prep; no PR or dev/main merge performed.

Live preview verification: backend restarted (launcher PID 8312; verify ownership before future restart). Synthetic credential-plus-URL request returned scam/high with floor >= .85 and R05; safety advice did not fire R05. Frontend localhost:5173 returned HTTP 200.

## Latest M6 completion / exact continuation - 2026-11-10
This section supersedes earlier M6-pending notes. Static URL features, LR/RF/GB comparison,
selected URL artifact, standalone endpoint and text-URL fusion are implemented.
Source: official UCI PhiUSIIL; CC BY 4.0; source labels INVERTED (0 phishing -> 1).
Source archive/partitions pinned in docs/URL_DATASET_INVENTORY.json. Dedup/conflict filtering
before stratified 70/15/15 seed42 split. No test predictions; no message or URL strings persisted.
Only computed static features used, never webpage features or HTTP/DNS lookups of submitted URLs.
Completed run: backend/models/url_preliminary_001/metrics.json. Generated docs/URL_MODEL.md,
URL_MODEL_RESULTS.json contain measured comparison. Selected artifact: models/url_clf.joblib
plus SHA/feature-code manifest. This artifact is ignored. Do NOT rerun completed training.
Reproduction only if genuinely necessary: from backend,
.venv/Scripts/python.exe -u -m ml.train_url --output models/<fresh-run>
Trainer refuses existing run/model; no automatic overwrite. Do not delete artifacts to rerun.
Saved pipeline stores no URL vocabulary; URL feature source hash verified by lazy runtime loader.
URL endpoint returns trained probability as standalone risk; text uses max URL probability in fusion.
Missing URL model -> URL HTTP503; text continues with explicit fallback. Invalid URL -> HTTP422.
url_features response no longer echoes URL/host credentials; numeric/boolean features only.
No API schema shape changed. Frontend states trained static URL model; build passed.
131 backend tests passed including artifact reload, split/dedup, URL cases and API fusion.
High validation scores are dataset-specific; random URL splits share some hostnames.
Do not present them as unseen-domain/live-phishing guarantees. Historical M5 results exclude URL fusion.
M5 alert-severity tuning and n-gram attribution remain pending; final test evaluation remains untouched.
Next major milestone: M8 React pages Analyze, Dashboard, Model Lab, Settings, About/Ethics.
Model Lab must display actual text metrics and separate binary url_models; no invented charts.
Dashboard/storage/consent endpoints still need inspection before implementing those pages.
Then M7 media, M9 WhatsApp last. Changes local on feat/data-prep, no PR/dev/main merge.

M6 final checks: Ruff lint/format and git diff --check passed; URL joblib git-ignore verified. Live backend restarted (launcher PID 20144, verify ownership before restart). Synthetic URL returned trained probabilities; text credential-plus-link used the URL model and preserved high-risk floor. Preview localhost:5173 HTTP200. No access logging enabled.

Observed live limitation: the synthetic reserved-domain URL https://example.com/demo received high risk. This smoke check verifies integration, not correctness on safe URLs. Static/source-specific shortcuts can produce false positives; unseen-domain and hard-negative validation remain a quality follow-up before any real alerts. Do not whitelist example.com merely to conceal this behavior.

## Latest M8 implementation - 2026-11-11
Five hash-routed React pages implemented: /#/analyze, /#/dashboard, /#/models,
/#/settings, /#/about. Existing text/URL inference preserved; model artifacts untouched.
Analyze: text/URL tabs, synthetic examples, masked language, rule IDs, risk meter,
probabilities/features, loading/error/empty states, clear, abort-on-unmount, round-trip latency.
Input/result exists only in component memory; not in query keys or browser storage.
Dashboard: real local HIGH-RISK web metadata history, page size20, full-history modality/day
aggregates and timeline. Low/medium analyses are not retained. No notification delivery implied.
Storage: built-in sqlite3, ignored backend/data/runtime/alerts.sqlite3, web_risk_history table.
Only id,ts,modality,label,risk_level,risk_score,rule_ids. Service accepts no text/URL/phone fields.
History failure does not hide analysis; response explanation discloses it. Tests use isolated temp DBs.
Model Lab: GET /api/metrics/models; five real text models, three URL models, two ablation groups.
Text/URL class sets separate; confusion matrix/per-class stats selectable; validation-only limits shown.
Historical M5 hybrid excludes URL fusion. URL false-positive limitation visible on Analyze/About.
Settings: GET /api/settings exposes read-only thresholds/dry-run and unavailable integration flags.
Consent/guardian/simulator genuinely deferred to M9; no phone collection or fake connected state.
File input genuinely deferred to M7. About covers privacy, limitations and human judgment.
API: app/dashboard_schemas.py + routers/dashboard.py; GET /api/alerts bounded limit/offset.
Frontend: React Router hash routes; TanStack Query for public metadata; Recharts graphs.
All requests in src/api.ts; errors do not echo backend validation input. API types generated,
not hand-maintained. npm run gen:types runs scripts/export-api.mjs -> backend/scripts/export_openapi.py
then openapi-typescript. Generated public OpenAPI snapshot + src/generated/api.ts checked in locally.
TypeScript changed from 6.0 to supported 5.9 because openapi-typescript 7 requires TS5;
no --force/legacy-peer-deps. npm scripts now include typecheck, lint, gen:types.
Dashboard/ModelLab lazy-loaded; final production chunks are below Vite warning threshold.
Styles split into focused files in src/styles. Prettier formatted frontend sources.
Verification: full backend 138 passed; after connection cleanup, seven dashboard tests passed again.
Frontend gen:types, typecheck, lint, build all passed. Ruff and git diff --check passed.
Live metrics/settings/alerts endpoints and frontend modules returned HTTP200.
Browser visual QA NOT completed: both cua_repl and Windows node_repl initialization fail with
"failed to write kernel assets: The system cannot find the path specified (os error 3)".
Responsive CSS is implemented, but mobile/desktop layout and actual navigation still need visual QA.
Production npm audit: zero vulnerabilities. Ten moderate transitive dev-tool minimatch advisories
remain; compatible npm audit fix did not resolve them. No forced upgrades applied.
No text/URL model retraining or test/custom hold-out evaluation. Changes local on feat/data-prep;
no commits/PR/dev/main merge performed. Do not repeat dataset training or artifact promotion.
Next: verify five pages in browser when tool works, then M7 media extraction per spec
(audio/image/PDF/video, limits and temp cleanup). M9 WhatsApp remains last.
Carry forward M5 calibration/n-gram attribution, M6 hard-negative/unseen-domain quality checks,
and final human review/test evaluation as open work. Do not describe the entire project complete.

Final backend restart launcher PID 21996; verify ownership before later restart. Preview remains http://localhost:5173/#/analyze. Runtime history DB is ignored; tests do not write into it.

## Active M7 continuation - 2026-11-11
Media extractors, /api/analyze/file, pre-parser body cap, temporary-directory cleanup,
magic-byte/type/size/page/duration/pixel limits, masked preview, warnings and file UI implemented.
Shared pipeline extracted to services/text_analysis.py; text/URL artifacts unchanged.
Original-script plus transliterated rules merged uniquely for media; Urdu ML bridge approximate.
Installed CPU torch + torchvision, EasyOCR, PyMuPDF, Pillow, filetype, imageio-ffmpeg,
faster-whisper and python-multipart. OCR weights installed under ignored models/media/ocr.
Actual synthetic PDF/PNG/silent MP4 inference succeeded; OCR missed a URL in PNG/video,
so PDF high vs PNG/video medium is a recorded extraction limitation, not a claimed success in detection.
Synthetic fixtures at backend/data/raw/media_demo (ignored); generate via python -m ml.make_media_demo.
Synthetic English speech fixture generated with Windows SAPI, no personal audio recorded.
Full suite: 158 passed. Frontend typecheck/lint/build passed before final UI fixes.
Speech model NOT YET verified: initial Xet download stalled, HTTP fallback downloaded part of
483546902-byte model.bin then connection/DNS failed. Setup process ended. No test-set evaluation.
Next immediate actions: retry `HF_HUB_DISABLE_XET=1 HF_HUB_DOWNLOAD_TIMEOUT=60 python -m ml.setup_media --speech`,
verify actual speech + tone rejection and audio-bearing video, finish UI/build/live restart/docs.
Browser tooling still fails kernel-assets initialization; do not claim visual QA.
File tab initially had a stale coming-later span due to a Windows UTF-8 read bug; fixed on continuation
with explicit UTF-8 reads, along with visible mojibake. Dashboard now counts media separately.
The backend preview must be restarted after final checks before File upload works live.


## M7 resumed progress
Usage-limit auto-review interruption resolved when user continued; no unsafe-action rejection.
UI File upload entry and mojibake fixed. Frontend gen:types/typecheck/lint/build passed again.
Full backend suite 159 passed; subsequent download/media tests 23 passed.
Media is live on backend launcher PID12772 (verify process ownership before restarting).
Synthetic PDF HTTP check passed and added one intentional QA metadata record to local Dashboard.
Speech setup now uses resumable pinned download with SHA-256 validation; cache models/media/speech/small.
Official size/hash were verified from Hugging Face model metadata; no user-media network calls.
Next: await current speech setup, run ml.smoke_media, verify speech/video/tone results, restart backend
so it picks up the direct speech path, update final status. The script ml/make_speech_demo.ps1
reproduces the Windows synthetic speech fixture; ml.smoke_media writes aggregate results only.


## Latest M7 completion / exact continuation - 2026-11-11
This section supersedes all M7 speech-pending notes above. Speech weights are installed,
SHA-256 verified and loaded successfully. API audio.py prefers models/media/speech/small;
its model.bin must be complete. The older incomplete HF cache is unused, not a missing dependency.
OCR Urdu/English weights and CPU dependencies are installed. Do NOT redownload or retrain.
Full backend suite: 161 passed. Final frontend gen:types/typecheck/lint/build passed.
Actual synthetic runtime report: backend/models/media_smoke.json, all five expected outcomes passed:
PDF/image/spoken audio/spoken video return200; non-speech tone returns422.
Do not turn these integration checks into an accuracy claim. Actual spoken fixture was English;
Urdu-script bridge/masking/mixed-script credential cues are unit-tested, real Urdu voice quality is not.
Image/silent video OCR missed a URL, causing medium rather than high; documented in docs/MEDIA.md.
Synthetic-only fixtures live in ignored backend/data/raw/media_demo. User can upload these in File tab.
Generators: python -m ml.make_media_demo; Windows powershell -File ml/make_speech_demo.ps1.
Verifier: python -m ml.smoke_media (isolated temporary history, aggregate output only).
File upload UI is enabled with choose/drop, configurable limits, masked collapsed preview,
extraction warnings and API-safe errors. Dashboard counts high-risk media metadata separately.
Real typed/media text, transcripts, filenames and URLs are never logged or saved in history.
Upload original/conversions removed on success/failure; framework upload file closed finally.
Tests cover chunked-body bound, type mismatch, page/pixel/duration limits, cleanup, missing models,
concurrency rejection, original/transliterated rules, Urdu masking, download resume and checksums.
Docs: MEDIA.md + TECH_DOC M7 contract. Cached model/media-demo directories verified git-ignored.
No final test set or custom hold-out evaluated. Existing trained text/URL models not changed.
Visual browser QA still unavailable due tool kernel-assets initialization error. Do not claim it passed.
Remaining: M5 LR term attribution/alert calibration, M6 URL false-positive/unseen-domain checks,
manual desktop/mobile and realistic Urdu media QA, human review/final test evaluation, M9 WhatsApp
(consent, dry-run, guardian alerts, dedicated demo number), M10 polish/report. WhatsApp is not connected.
Recommended next: improve model-quality/explanation checks before real alerts; M9 can start in dry-run.
Changes remain local on feat/data-prep; no PR/dev/main merge. Continue from this section, not stale notes.

Final M7 backend launcher PID 19792; verify ownership before restart. Preview http://localhost:5173/#/analyze → File upload.

Final live check passed: restarted /api/analyze/file processed synthetic spoken WAV with HTTP200/high risk; preview returned HTTP200 and File upload entry is served. Two intentional live QA history records (synthetic PDF and spoken audio) may appear in Dashboard; they contain metadata only, not content.

## Latest quality/demo continuation — 2026-11-11
Implemented partial LR word attribution in services/explain.py + text_analysis.py, including VotingClassifier encoded class decoding. Synthetic tests cover masking, missing attribution and actual VotingClassifier structure. No API schema change.
URL audit found all source benign training URLs have root paths and HTTPS. Two validation-only augmentation candidates saved in models/url_robust_001 and _002; scripts ml/improve_url.py + url_robustness.py reproduce training without test inference. See docs/URL_ROBUSTNESS_RESULTS.json for exact aggregate metrics. Candidate002 improves synthetic path stress substantially but reserved demo root/path URLs still predict high. Neither candidate was promoted; existing URL artifact/manifest unchanged. Do not claim false positives fixed or whitelist demo domains. Next quality work: audit additional lexical/source shortcuts and validate on independently reviewed benign/phishing URLs before promotion. Synthetic path labels are assumptions, not external accuracy.
README and docs/DEMO.md updated; scripts/start-demo.ps1 starts hidden local services and reuses existing ready ones. Browser visual QA remains unavailable. Media weights already installed; do not retrain/redownload completed models. Final test sets remain untouched. WhatsApp remains unimplemented bonus; guardian calibration and human review still pending. No PR/merge performed; cumulative work remains on feat/data-prep.

Final verification: full backend suite 165 passed; Ruff passed for quality changes. Restarted owned backend; live synthetic text returned high with LR component cues, frontend HTTP200. One additional synthetic QA metadata row may appear. No frontend code changed this session. Launcher readiness uses IPv4 for backend to avoid localhost resolution timeout.

## Active continuation — 2026-11-12
Confirmed second URL source shortcut: all benign training URLs have www and HTTPS/root paths. Added --www-invariance augmentation; models/url_robust_003 completed, reduces stress false positives but FAILS original recall gate, NOT deployed. Weighted recall recovery run models/url_robust_004 uses --www-invariance --phishing-weight 3; check completion before restarting. Download is slow, do not start duplicate runs. No final test predictions. ml/promote_url_robust.py enforces recall/F1, stress-FPR and synthetic-placeholder gates before any promotion, with previous-artifact backups.
Fixed Windows checkout CRLF feature-hash mismatch in URL loader: accepts identical LF-normalized code, still rejects changed code/model bytes. Full backend suite 167 passed before weighted experiment/promotion utility. New report generator ml/report_demo.py creates docs/DEMO_REPORT.md from aggregate artifacts; regenerate after candidate/deployment decision. Preview launcher passed. Visual QA attempted via computer-use skill but node runtime failed: registered runtime ownership is missing. Do not claim browser QA. More results will follow below; preserve existing artifacts and untouched test sets.

## Final URL quality decision — 2026-11-12
Runs url_robust_003 (www/path augmentation) and url_robust_004 (same plus phishing sample weight 3) completed. Neither passes the unchanged source-recall regression gate. The latter also fails the promotion utility's stress-FPR bound. Neither promoted; deployed URL model remains url_gb with its original SHA. Do not call URL false positives fixed. Source benign labels are confounded with www + HTTPS + root paths; augmentation is not a substitute for independent reviewed labels. Avoid more blind weight tuning; next substantive URL work requires representative reviewed URL validation under existing dataset policy, with no URL fetching. Test set and custom hold-out remain untouched.
Model loader CRLF fix is deployed code (verified full suite before final new gate tests). Promotion utility retains rollback backups if a future candidate passes; do not invoke on rejected runs. docs/DEMO_REPORT.md is generated by python -m ml.report_demo and honestly separates current artifact from rejected candidate metrics. Browser automation remains blocked by local runtime ownership failure; do not mark visual QA complete. Preview launcher is working. No final human review, guardian calibration or WhatsApp completion claim. Final test count/live results recorded below after checks.

Final verification for 2026-11-12 continuation: 173 backend tests passed; Ruff passed on all touched Python files; git diff --check passed (only expected LF/CRLF warning). Demo report regenerated after run004. No frontend code changed. Existing branch feat/data-prep; latest pre-session commit e946230, remote tracking currently lists origin/main only, no verified dev target. No commit, push or PR was made this session. URL deployed artifact unchanged; CRLF loader fix is the functional repair delivered. Further tuning was stopped after two rejected candidates; final test data remains unconsumed.

## Demo completion work — 2026-11-12
Supersedes the old browser QA blocker. Browser desktop scam result and Dashboard were verified at 1365px. Mobile Model Lab, Settings and upload controls were verified at 390px. Latest frontend typecheck, lint and build passed. Backend 173 tests passed. Synthetic media smoke reran successfully across PDF, image, speech, video and non-speech rejection. A synthetic browser test added one metadata row locally. Realistic Urdu speech and independent human review remain pending.
Original local branch commits include tracked ignored runtime/model artifacts. Preserve the user's branch, but use a clean Git snapshot based on origin/main for publication. Never push feat/data-prep history. GitHub connector branch creation returned 403; existing Git credentials passed a push dry run. URL RF run models/url_robust_rf_005 is validation only and must pass promotion checks. One-shot evaluator ml/final_evaluation.py is prepared; run only after model selection freezes. The aggregate final report, if created, is the authoritative record of consumed test splits.

Latest verification: 174 backend tests pass. Frontend typecheck/lint/build pass after Model Lab copy change. Real synthetic Urdu image OCR returned HTTP200, reached the transliteration bridge and matched R03/R05; reproduce with python -m ml.smoke_urdu_image. RF005 failed the existing promotion gate and was retained for analysis only. The deployed URL model still has false positives. Final evaluation froze model selection and attempted preflight; first run ended before reservation/prediction. Inspect backend/models/final_evaluation and docs/FINAL_RESULTS.json before any retry. GitHub dev exists and the new feat/demo-ready history is based directly on origin/main with runtime/model artifacts excluded.

Final one-shot evaluation COMPLETE. This supersedes all earlier notes that the test sets are untouched. docs/FINAL_RESULTS.json records aggregate text ML/hybrid, synthetic custom hold-out and URL test results plus frozen model hashes and partitions. Do not run inference on those test splits again or tune from their scores. Rebuild only with new independent evaluation data if needed. The original deployed URL model is frozen because RF005 and earlier candidates failed validation promotion. URL bias and independent human review remain research limitations. Local feat/data-prep history stays private because it contains tracked ignored artifacts. Clean feat/demo-ready was published in GitHub PR #1 to dev.
`nPR #1 verified merged into dev at 1607d10f8cde0200d66327204b646ee9b310581f. Remote main was not a merge target. Local feature checkout remains intact with ignored assets for preview.

## M9 WhatsApp continuation — 2026-11-13
Implemented dedicated-account bridge, authenticated text/media endpoints, guardian confirmation/STOP, owner opt-in, atomic dedupe and rate limits, and Settings synthetic simulator. See whatsapp/README.md. Actual account pairing and live alert delivery require the dedicated demo account and consenting guardian. No real account was paired and no real messages were sent. Keep local credentials, auth state, runtime databases, and artifacts out of Git.

WhatsApp PR #3 merged into dev at 58a738a413f1224c3a74c411c46df42498a4ed64. Updated and verified submission ZIP includes the bridge, lockfile, setup and core report. Live pairing and delivery still require dedicated account and guardian opt-in.

Settings now includes authenticated WhatsApp QR and connection status. Start the configured bridge, then unlock the QR with the local bridge key. Pairing endpoint binds only to 127.0.0.1:8011. Real QR requires a configured dedicated account.

WhatsApp transport now launches headless Chromium with whatsapp-web.js. Settings displays its QR via the authenticated loopback endpoint. No Meta API key. Dedicated-account QR scan and guardian consent still require real devices.

Settings pairing now uses the local FastAPI proxy; bridge key stays server-side. Connected Settings displays guardian consent and an expiring command. High-risk delivery uses the linked account self-chat and the configured guardian. Local dry-run disabled at user request; owner and guardian consent still gate delivery. Live verification requires an active linked session and guardian opt-in.
