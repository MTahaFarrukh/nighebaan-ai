# CCP report pack

| File | Purpose |
|---|---|
| [Nigehbaan_AI_CCP_Report.md](Nigehbaan_AI_CCP_Report.md) | 10+ page technical report |
| [CCA_CCP_MAPPING.md](CCA_CCP_MAPPING.md) | Course-brief mapping |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | Viva-safe six-case demo |
| [VIVA.md](VIVA.md) | Implementation and domain questions |
| [KAPPA_STATUS.md](KAPPA_STATUS.md) | Why kappa is not reported |
| [figures/](figures/) | Generated charts (no live message text) |

Regenerate charts from the repository root / `backend`:

```powershell
cd backend
.venv\Scripts\python.exe -m ml.make_figures
```

Export the Markdown report to PDF or DOCX in Word / Pandoc. Do not retype
metrics; they come from `docs/FINAL_RESULTS.json` and related generated files.

Live UI screenshots are **not** stored here (privacy and environment). Capture
them during the demo using `DEMO_SCRIPT.md` and keep them off Git if they
could contain personal data.
