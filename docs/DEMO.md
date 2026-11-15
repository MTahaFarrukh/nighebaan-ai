# Viva demo quick guide (8–10 minutes)

The detailed, teacher-facing walkthrough is [report/DEMO_SCRIPT.md](../report/DEMO_SCRIPT.md).
The CCP write-up is [report/Nigehbaan_AI_CCP_Report.md](../report/Nigehbaan_AI_CCP_Report.md).

## Preflight

1. From the repository root, run `powershell -File scripts/start-demo.ps1` and open the printed preview.
2. Confirm text/URL artifacts are available. For media, prepare the synthetic files in `backend/data/raw/media_demo` and confirm local OCR/Whisper weights are installed. Run `python -m ml.smoke_media` from `backend` before the viva if you need to verify all four media paths; it is a preflight, not a timed demo step.
3. Use only synthetic inputs. Keep WhatsApp in dry-run mode; do not show personal chats, credentials, or QR codes.

## Suggested order

1. **Analyze:** show the synthetic OTP/link text example, the safety-advice contrast, and a static URL check. Explain that URLs are never fetched.
2. **Media:** upload the synthetic PDF, image, audio, and video in turn. Show extraction warnings and masked previews. Speech fixtures are synthetic and do not establish realistic Roman Urdu accuracy.
3. **Dashboard:** show high-risk metadata only. WhatsApp entries appear only after a real consented analysis is recorded; no paired account means no WhatsApp rows. The Settings simulator sends no message and creates no Dashboard history row.
4. **Model Lab:** show text/URL comparisons and validation views. Use [FINAL_RESULTS.json](FINAL_RESULTS.json) for frozen reported figures; do not infer performance from one live example.
5. **Settings:** point out thresholds, dry-run, and current pairing status. Explain that the simulator returns a decision only.
6. **About/Ethics:** finish with privacy, static URL analysis, masked abusive terms, and the limitations in the full script.

## Claims to avoid

Do not call the model perfectly accurate or safe for automatic decisions. URL data has strong source shortcuts; synthetic robustness checks are not externally verified URL labels. OCR missed a link in a synthetic fixture. English synthetic speech has been exercised, but realistic Roman Urdu speech accuracy remains unevaluated. LR word cues explain only the linear component, not the complete ensemble or a causal reason. Thresholds are not guardian-calibrated. Custom labels remain human-unverified. The frozen models were evaluated once on the test and synthetic custom hold-out partitions. See [FINAL_RESULTS.json](FINAL_RESULTS.json) for aggregate scores.

The backend and frontend runtime checks passed, but interactive browser recording/visual QA did not complete successfully in this environment. Do not claim that mobile and desktop visual QA passed.

An aggregate demo report is available at [DEMO_REPORT.md](DEMO_REPORT.md), reproducible with `python -m ml.report_demo` from `backend`. Rejected URL robustness experiments are documented there; deployed URL false positives remain known.

WhatsApp live pairing, media download, and alert delivery were not verified. Do not use a personal number; any live demonstration requires a dedicated account and prior recipient agreement.
