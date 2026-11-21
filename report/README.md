# CCP report pack

| File | Purpose |
|---|---|
[figures/](figures/) | Generated charts (no live message text) |

Regenerate charts from the repository root / `backend`:

```powershell
cd backend
.venv\Scripts\python.exe -m ml.make_figures
```

Export the Markdown report to PDF or DOCX in Word / Pandoc. Do not retype
metrics; they come from `docs/FINAL_RESULTS.json` and related generated files.

