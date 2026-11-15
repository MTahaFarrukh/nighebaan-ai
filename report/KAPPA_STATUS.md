# Cohen's kappa status

**No project kappa is reported.**

Two independent human reviewers did not complete the custom Roman Urdu review
pack during this finish session. `custom_scam.review.json` is absent. The
promotion command in `docs/DATA_REVIEW.md` was **not** run.

- Draft custom set: 800 candidates (500 scam / 300 normal), LLM-assisted
  templates, documented in `docs/DATASETS.md`.
- Training used a **preliminary, human-unverified** custom subset. The frozen
  custom hold-out in `docs/FINAL_RESULTS.json` has 16 rows.
- Test-suite kappa values in `backend/tests/test_dataset_workflow.py` use
  **artificial** annotations and are not project results.

Do not invent an agreement score. If two people later label the 100-item
blind sample independently, compute kappa only via:

```powershell
# from backend, after both reviewer sheets are complete
.venv\Scripts\python.exe -m ml.custom_dataset promote --directory data/raw/custom/review_v1 --output data/raw/custom/custom_scam.csv
```

That would require a **new** corpus version and **must not** be used to retune
the already-frozen test evaluation.
