# Dedicated WhatsApp demo bridge

Use Node 22+ and a dedicated demo account. The bridge runs WhatsApp Web in background Chromium using [whatsapp-web.js](https://docs.wwebjs.dev/). Scan the linked-device QR from Settings or the terminal. No Meta API credentials are needed. The bridge key authenticates local Nigehbaan requests.

1. Copy whatsapp/.env.example to whatsapp/.env. Set a random bridge key of at least 32 characters. Set the demo and guardian JIDs in the international-digits@s.whatsapp.net format, with distinct accounts.
2. Put the same key and WHATSAPP_OWNER_OPT_IN=true in backend/.env and whatsapp/.env. Start or restart the backend. Keep DRY_RUN=true in both files for the first run.
3. In whatsapp, run npm ci and npm run dev. In WhatsApp Linked Devices scan the local QR using the dedicated demo account. Keep the QR and auth_browser folder private.
4. Share the short-lived NIGEHBAAN command printed by the bridge with the consenting guardian privately. The guardian replies with that exact command to the demo account. They can revoke consent with STOP.
5. Send a synthetic high-risk message to the demo account from a third test account. The bridge only processes fresh incoming direct messages after consent. The bridge prints a content-free alert decision in dry-run. The synthetic simulator in Settings also works without pairing.
6. For a real delivery test after both parties agree, set DRY_RUN=false in both files and restart both services. The demo account gets a self-chat warning and the guardian gets a generic warning. Identical alerts are suppressed for 24 hours and each sender is limited to three alert reservations per hour.

Never use a personal account or share the QR or auth files. JIDs are configured only in the local ignored environment file and can occur in private Chromium profile. The backend receives keyed hashes for consent and deduplication. Content stays out of alert text, logs and the application database. Disable owner opt-in and stop the bridge to end monitoring. No real delivery is required to use Settings > Simulate WhatsApp alert.

For browser pairing, open http://localhost:5173/#/settings after starting the bridge. Settings loads the QR automatically using the local backend configuration. The bridge serves the expiring QR on loopback port 8011 and requires the key for every request.

On Linux, run the bridge as a non-root user with the Chromium system dependencies installed. Set WHATSAPP_HEADLESS=false to show Chromium or WHATSAPP_CHROME_PATH to select a local browser. The dedicated browser profile is stored in the ignored auth_browser directory. Restart the bridge after a disconnect.

After pairing, Settings shows the guardian opt-in command while consent is pending. The guardian sends it to the demo account. With DRY_RUN=false in both local configurations, eligible high-risk messages trigger an alert in the account’s self-chat and a generic guardian alert.
