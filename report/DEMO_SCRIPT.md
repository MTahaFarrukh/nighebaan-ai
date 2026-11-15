# Teacher Demo Script (8–10 minutes)

This walkthrough demonstrates the current local application using synthetic inputs. It does not imply live WhatsApp delivery, production-grade detection, or that Gemini is configured.

## Before the viva

- Use only synthetic messages, files, URLs, and accounts. Do not display real chats, phone numbers, QR codes, or credentials.
- Start the application with the documented Windows demo command: `.\scripts\start-demo.ps1`. Open the local frontend and confirm the backend health check succeeds.
- Confirm the text and URL model artifacts are present. For media demos, the local OCR and Whisper model weights must also be installed; media inference does not use Gemini.
- Prepare the generated fixtures before the presentation. From `backend`, run `.\.venv\Scripts\python.exe -m ml.make_media_demo`, then `powershell -ExecutionPolicy Bypass -File .\ml\make_speech_demo.ps1`. Run `.\.venv\Scripts\python.exe -m ml.smoke_media` as a preflight, not as part of the timed presentation. It exercises the synthetic PDF, image, audio, and video paths and can take time on CPU.
- Keep WhatsApp in dry-run mode. The Settings simulator is safe to show; it sends no message and does not create a Dashboard history row. Only demonstrate live WhatsApp with a separately prepared, consented test account and a dedicated test sender.
- If an inference fails during preflight, fix the setup or omit that modality and explain the limitation. Do not substitute a fabricated result.

## Presentation

### 1. Introduce the system (about 45 seconds)

> “Nigehbaan AI analyzes text, URLs, and text extracted from media for scam and abusive-content indicators. It combines machine-learning predictions with explainable rules. Media processing is local; Gemini is not required. The result is a decision-support signal, not proof that a message is safe or harmful.”

Point out the Analyze, Dashboard, Model Lab, Settings, and About/Ethics areas.

### 2. Analyze text (about 1½ minutes)

On **Analyze → Text**, enter this synthetic scam-style example:

```text
Foran apna OTP bhejo warna account band ho jayega: https://example.com/verify
```

Show the predicted label, risk score/level, explanation, and any fired rule IDs. Explain that `example.com` is a placeholder and is not visited.

Then enter:

```text
Never share your OTP with anyone.
```

Compare the explanation and rule evidence. Do not promise that negation always makes the model output `normal`; the point is to show that rule evidence and model predictions are distinct signals.

If showing abusive-language detection, use only a pre-approved synthetic example whose displayed preview has been checked for masking. Otherwise explain the masked abusive-cue rule without entering or displaying abusive terms.

### 3. Analyze a URL (about 45 seconds)

On **Analyze → URL**, enter:

```text
http://192.0.2.10/verify-account
```

Explain that URL analysis uses static features. The app does not open or fetch the address, and the result does not establish that a real website exists.

### 4. Analyze media (about 2 minutes)

On **Analyze → File**, select the prepared synthetic fixtures one at a time:

1. PDF
2. Image
3. Audio
4. Video

Show the extracted-text preview, analysis result, and any extraction warning or confidence information the UI provides. The speech fixtures use synthetic speech; they demonstrate the pipeline, not Roman Urdu speech-recognition accuracy. Audio/video processing can be slower than text analysis.

If useful, show that a silent or unextractable file is rejected with a clear error rather than being presented as a confident `normal` result.

### 5. Review the Dashboard (about 1 minute)

Open **Dashboard** and point out the high-risk history metadata, such as source, label, risk, rule IDs, and alert status. Message content is not shown there.

> “The Dashboard retains high-risk metadata; it is not a transcript viewer. A WhatsApp row appears only when a real, consented WhatsApp analysis is recorded. The Settings simulator demonstrates a decision only—it does not send a message or add a Dashboard row.”

If no WhatsApp rows are present, that is expected when no dedicated WhatsApp account is connected.

### 6. Explore the Model Lab (about 1 minute)

Open **Model Lab** and show the text/URL comparisons, confusion matrix, class-level metrics, and ablation view. Explain that the displayed figures are tied to the project's evaluation data and that final reported metrics should be read from the reproducible results artifact, not inferred from one live example. Do not claim that the hybrid model always outperforms an individual model.

### 7. Show Settings and the WhatsApp simulator (about 1 minute)

Open **Settings** and point out the risk thresholds, WhatsApp connection state, and dry-run status. Run the simulator if desired, then clarify:

> “This is a simulated alert-policy decision. It does not deliver a WhatsApp message and does not create a Dashboard history record. Live pairing and delivery are separate and have not been verified for this demo.”

Do not expose a QR code or pair a personal account during the viva.

### 8. Close on About/Ethics (about 30 seconds)

Open **About/Ethics** and summarize the privacy and limitation points: synthetic demo data, no URL fetching, masked abusive terms, and no guarantee that low-risk content is safe.

## Optional live WhatsApp demonstration

Only attempt this if a dedicated test setup is already paired, consented, and verified before the viva. Use a synthetic message from a dedicated test sender, keep dry-run enabled unless actual delivery has been separately approved, and show only the resulting metadata. If pairing, consent, or delivery is not verified, skip this section and state that WhatsApp live delivery is unverified. Never use a personal account or real conversation.

## If something goes wrong

- If the app is unavailable, do not claim a live result. Explain the planned flow and use the written report's reproducible evaluation results.
- If a text or URL model is unavailable, skip live classification and report the setup blocker; do not make up a score.
- If OCR or speech weights are unavailable or media extraction is slow, skip that fixture and explain that local model weights are required.
- If the synthetic WhatsApp simulator runs, state again that it sends no message and creates no Dashboard row.

## Claims to avoid

- “Gemini powers the analysis.” The current media and analysis pipeline is local and does not require Gemini.
- “Every Roman Urdu voice message is transcribed accurately.” The synthetic media smoke test verifies the pipeline, not broad real-world accuracy.
- “The URL was checked online” or “the example site is malicious.” URL analysis is static and never fetches the URL.
- “The Settings simulator sent an alert” or “the simulator created a WhatsApp Dashboard row.”
- “WhatsApp is live and verified” unless pairing and delivery have actually been tested with the dedicated consented setup.
- Any accuracy, F1, or safety guarantee not backed by the project's reproducible evaluation artifacts.
