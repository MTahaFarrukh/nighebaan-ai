# Nigehbaan AI Windows setup

Install Git, Python 3.11 and Node.js 22 or newer. For WhatsApp install Chrome or Edge.

## 1. Get the code and models

In PowerShell:
```powershell
git clone -b dev https://github.com/MTahaFarrukh/nighebaan-ai.git
cd nighebaan-ai
```

Extract this model ZIP into the nighebaan-ai repository root. The four files go in
backend/models. Keep each model with its matching manifest. This pack contains
serialized Python models. Use copies from a trusted source.

## 2. Install and run

From the repository root:
```powershell
py -3.11 -m venv backend/.venv
& ./backend/.venv/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
& ./backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
powershell -File scripts/start-demo.ps1
```

Open http://localhost:5173/#/analyze. Try the built-in scam example, then the
normal message example. Training and datasets are unnecessary for inference.

## 3. Optional image, scanned PDF, audio and video setup

```powershell
cd backend
& ./.venv/Scripts/python.exe -m ml.setup_media --ocr
& ./.venv/Scripts/python.exe -m ml.setup_media --speech
cd ..
```

These commands download the OCR and speech weights. They need internet access
and disk space. See docs/MEDIA.md for retries and supported inputs.

## 4. Optional WhatsApp Web

Do this before starting the backend, or restart the backend after editing its
configuration so it reloads the values.

```powershell
Copy-Item whatsapp/.env.example whatsapp/.env
Copy-Item backend/.env.example backend/.env
node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"
```

Use Copy-Item only if the destination does not already exist. Put the generated
key in WHATSAPP_API_KEY in both local .env files. In both, set
WHATSAPP_OWNER_OPT_IN=true after the demo account owner agrees and set
DRY_RUN=true for the first test. In whatsapp/.env set WHATSAPP_DEMO_JID and
WHATSAPP_GUARDIAN_JID to distinct numbers in international format, digits only
followed by @s.whatsapp.net. Use a dedicated demo account.

Start the demo backend with the launcher above. In another PowerShell window:
```powershell
cd nighebaan-ai/whatsapp
$env:PUPPETEER_SKIP_DOWNLOAD = 'true'
npm.cmd ci
npm.cmd run dev
```

The bridge detects Chrome or Edge in standard Windows locations. If installed
elsewhere, set WHATSAPP_CHROME_PATH in whatsapp/.env to the browser executable.
Open http://localhost:5173/#/settings. The QR appears automatically.
On the demo phone use WhatsApp > Linked Devices > Link a Device and scan it.
After connection, the guardian sends the opt-in command shown in Settings to the
demo account from the configured guardian account. STOP revokes consent.

With dry-run enabled, test with a synthetic message from a third test account.
To try live delivery after both parties agree, set DRY_RUN=false in both local
files and restart both the backend and bridge. Send a different synthetic
example for the live test because duplicate alerts are suppressed.
Check Message Yourself and the guardian chat for a high-risk warning. A normal
message should produce no warning. Live delivery still needs an end-to-end check
with the recipient's linked accounts. The Settings simulator works without pairing.

Keep .env files, bridge keys, linked-device profiles and local history private.
