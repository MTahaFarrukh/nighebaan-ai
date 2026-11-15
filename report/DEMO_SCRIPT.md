# Viva demo script (six cases)

Run from the repository root. Do not retrain. Do not pair a personal WhatsApp account.

```powershell
powershell -File scripts/start-demo.ps1
```

Open http://localhost:5173/#/analyze. If ports are busy, free them; do not kill unknown processes.

**Claims to avoid while presenting:** “safe”, “99% phishing detector”, “kappa”, “WhatsApp is live”, “hybrid beats ML”, “example.com is correctly high risk”.

If a dedicated demo number and consenting guardian are already paired, say so once, then still run the simulator so the examiner sees the no-content alert path. Otherwise state: **bridge implemented, not live-paired; simulator only.**

Capture screenshots locally if the examiner wants them. Do not commit QR codes, phone numbers, or real chats.

---

## Case 1 — Roman Urdu OTP + link (expect high / scam cues)

1. Analyze → Text.
2. Click the built-in example `Foran OTP bhejo https://example.com` (or type it).
3. Analyze.

**Show:** risk high (credential+URL floor 0.85), rule **R05** and likely **R01** / **R03**, explanation mentions credential request with a link. URL probability is static (page is not visited).

**Say:** “R05 is a knowledge-base rule with request verbs. The floor is policy, not ML.”

---

## Case 2 — Safety advice must not fire R05

1. Use `Never share your OTP.`
2. Analyze.

**Show:** R05 absent (exclude patterns for `never` / `mat` / `nahi` + share). Label should stay non-scam unless the model is confused; the point is the **rule**.

**Say:** “This is clause-local negation, not deep language understanding.”

Optional follow-up (same idea): `Kal class kitne bajay hai?` as a normal Roman Urdu control.

---

## Case 3 — Abuse masking

Use a **synthetic** abusive phrase you already tested in private. Do not improvise slurs in front of the class if you are unsure of masking.

**Show:** label `abusive`, rule **R11**, flagged tokens masked (`g***`). Dashboard later must not contain the text.

**Say:** “The lexicon is a separate resource file. We never print it in logs or the report.”

---

## Case 4 — File upload (PDF)

1. Analyze → File.
2. Upload a synthetic fixture from `backend/data/raw/media_demo` (generate with `python -m ml.make_media_demo` from `backend` if the folder is empty).
3. Show masked preview, warnings, modality `pdf`.

**Say:** “OCR can miss URLs; a missed link is an extraction error, not a claim that the screenshot was safe. English speech was smoke-tested; Urdu ASR is a limitation.”

If Whisper weights are missing, skip audio and say HTTP 503 on purpose beats a fake transcript.

---

## Case 5 — URL bias (the trap question)

Do **not** present `https://example.com` as a correctly detected phishing site.

1. Analyze → URL.
2. Paste `https://example.com` or `https://example.com/demo`.
3. If risk is high, **agree with the limitation**: benign training URLs in PhiUSIIL (as used) are almost all `www` + HTTPS + root path. Robustness candidates were rejected because they hurt phishing recall. We did not whitelist `example.com`.

Contrast: a URL that *looks* like a phishing pattern (IP host, `@`, odd TLD, `bit.ly`) is a fair static-feature demo—still without visiting it.

**Say:** “Test macro-F1 0.996 is source-specific. I will not defend it as live accuracy.”

---

## Case 6 — Settings simulator (network requirement without live send)

1. Open `#/settings`.
2. Show medium 0.35, high/alert 0.70, dry-run as configured.
3. Run **Simulate WhatsApp alert**.
4. Open Dashboard: only metadata (time, modality, label, risk, rule IDs).

**Show:** guardian text would be generic; no message body. QR pairing is loopback-only and needs a dedicated account.

Then open **Model Lab**: validation tables, confusion matrix, ablations. State that the **test** numbers are in `docs/FINAL_RESULTS.json` and in the CCP report, and were computed once.

---

## Timing (about five minutes)

| Minute | Action |
|---|---|
| 0–0.5 | Architecture one-liner: extract → preprocess → ML ‖ rules ‖ URL → risk |
| 0.5–2 | Cases 1–2 |
| 2–3 | Case 5 (URL honesty) |
| 3–4 | Case 4 or 3 |
| 4–5 | Simulator + Model Lab + “hybrid F1 is slightly worse on test, rules still buy the OTP floor” |

If anything crashes: `/api/health`, then retry. Missing `text_clf.joblib` returns 503 by design.
