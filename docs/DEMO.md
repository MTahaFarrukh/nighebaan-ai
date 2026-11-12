# Five-minute local demo

1. Run `powershell -File scripts/start-demo.ps1` from the repo root; open the printed preview.
2. Analyze the synthetic OTP+link example. Review risk, matched rules and the explanation.
3. Try safety advice: `Never share your OTP.` It should not fire the credential-request rule.
4. Upload a generated synthetic PDF/image/audio/video from backend/data/raw/media_demo.
   Show the masked preview and extraction warnings. Pure tone is rejected, not labeled safe.
5. Open Dashboard: metadata only, no source content. Counts include high-risk synthetic QA runs.
6. Open Model Lab: text and binary URL results are separate. Show the confusion matrix and
   ablations. State clearly that these are validation scores, not final test numbers.
7. Settings shows the actual backend thresholds. WhatsApp is not connected; no messages are sent.

## Claims to avoid

Do not call the model perfectly accurate or safe for automatic decisions. URL data has strong
source shortcuts; synthetic robustness checks are not externally verified URL labels.
OCR missed a link in a synthetic fixture. English synthetic speech has been exercised, but
realistic Roman Urdu speech accuracy remains unevaluated. LR word cues explain only the linear
component, not the complete ensemble or a causal reason. Thresholds are not guardian-calibrated.
No human review/kappa was fabricated. Final test/custom hold-out remain untouched.

Browser QA passed for the desktop scam result and Dashboard, and mobile Model Lab, Settings and file upload controls. WhatsApp needs a dedicated demo number,
consent and dry-run verification before any real guardian alerts; do not use a personal number.

Aggregate demo report: [DEMO_REPORT.md](DEMO_REPORT.md), reproducible with `python -m ml.report_demo` from backend. Rejected URL robustness experiments are documented there; deployed URL false positives remain known.
