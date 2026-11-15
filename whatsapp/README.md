# Dedicated WhatsApp demo bridge (Baileys)

Use Node 22+ and a dedicated demo account. The bridge uses the Baileys WebSocket client and stores its multi-file authentication state under `auth_baileys/`. Scan the linked-device QR from Settings or the terminal. No Meta API credentials or Chromium installation are needed. The bridge key authenticates local Nigehbaan requests.

1. Copy whatsapp/.env.example to whatsapp/.env. Set a random bridge key of at least 32 characters. Set the demo and guardian JIDs in the international-digits@s.whatsapp.net format, with distinct accounts.
2. Obtain the account owner's opt-in and the configured recipient's informed agreement before enabling monitoring. Put the same key and WHATSAPP_OWNER_OPT_IN=true in backend/.env and whatsapp/.env. Start or restart the backend. Keep DRY_RUN=true in both files for the first run.
3. In whatsapp, run npm ci and npm run dev. In WhatsApp Linked Devices scan the local QR using the dedicated demo account. Keep the QR and auth_baileys folder private.
4. The configured `WHATSAPP_GUARDIAN_JID` is enabled automatically after the dedicated demo account connects. This is environment-based authorization only: the app does not verify or store the recipient's informed agreement. No guardian command or `STOP` revocation flow is implemented.
5. Send a synthetic high-risk message to the demo account from a third test account. The bridge only processes fresh incoming direct messages after the owner opt-in and configured guardian are active. The bridge prints a content-free alert decision in dry-run. The synthetic simulator in Settings also works without pairing.
6. For a real delivery test after both parties agree, set DRY_RUN=false in both files and restart both services. The demo account gets a self-chat warning and the guardian gets a generic warning. Identical alerts are suppressed for 24 hours and each sender is limited to three alert reservations per hour.

Never use a personal account or share the QR or auth files. JIDs are configured only in the local ignored environment file and can occur in the private Baileys auth state. The backend receives keyed hashes for authorization and deduplication. The owner self-alert includes only a safe detected-keyword category for demonstration; the guardian alert never includes message content. Content stays out of logs and the application database. To stop monitoring, set `WHATSAPP_OWNER_OPT_IN=false` in both local files and stop the backend and bridge. Obtain renewed agreement before re-enabling. No real delivery is required to use Settings > Simulate WhatsApp alert.

For browser pairing, open http://localhost:5173/#/settings after starting the bridge. Settings loads the QR automatically using the local backend configuration. The bridge serves the expiring QR on loopback port 8011 and requires the key for every request.

On Linux, run the bridge as a non-root user. Baileys does not launch Chromium; it maintains a direct WhatsApp Web protocol connection. Restart the bridge after a disconnect if automatic reconnection does not recover the session.

After pairing, Settings shows connection and configured-guardian status. Only attempt real delivery after both parties have agreed and alert thresholds have been reviewed. With `DRY_RUN=false` in both local configurations, eligible high-risk messages trigger an alert in the account’s self-chat and a generic guardian alert.
