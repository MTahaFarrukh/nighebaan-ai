# Dedicated WhatsApp demo bridge

Use Node 22+ and a dedicated demo account. The bridge uses [Baileys](https://github.com/WhiskeySockets/Baileys/releases) and local QR pairing.

1. Copy whatsapp/.env.example to whatsapp/.env. Set a random bridge key of at least 32 characters. Set the demo and guardian JIDs in the international-digits@s.whatsapp.net format, with distinct accounts.
2. Put the same key and WHATSAPP_OWNER_OPT_IN=true in backend/.env and whatsapp/.env. Start or restart the backend. Keep DRY_RUN=true in both files for the first run.
3. In whatsapp, run npm ci and npm run dev. In WhatsApp Linked Devices scan the local QR using the dedicated demo account. Keep the QR and auth_demo folder private.
4. Share the short-lived NIGEHBAAN command printed by the bridge with the consenting guardian privately. The guardian replies with that exact command to the demo account. They can revoke consent with STOP.
5. Send a synthetic high-risk message to the demo account from a third test account. The bridge only processes fresh incoming direct messages after consent. The bridge prints a content-free alert decision in dry-run. The synthetic simulator in Settings also works without pairing.
6. For a real delivery test after both parties agree, set DRY_RUN=false in both files and restart both services. The demo account gets a self-chat warning and the guardian gets a generic warning. Identical alerts are suppressed for 24 hours and each sender is limited to three alert reservations per hour.

Never use a personal account or share the QR or auth files. JIDs are configured only in the local ignored environment file and can occur in private Baileys auth state. The backend receives keyed hashes for consent and deduplication. Content stays out of alert text, logs and the application database. Disable owner opt-in and stop the bridge to end monitoring. No real delivery is required to use Settings > Simulate WhatsApp alert.
