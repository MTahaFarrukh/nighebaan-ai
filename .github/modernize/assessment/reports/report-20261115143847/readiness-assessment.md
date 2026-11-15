# Nigehbaan AI — readiness assessment

**Date:** 2026-11-15  
**Scope:** Whole-workspace modernization/readiness review, with emphasis on WhatsApp analysis, consent, API contracts, dry-run delivery, and frontend readiness.

## Assessment approach and limits

The workspace is a polyglot application: Python/FastAPI backend, React/TypeScript frontend, and a Node/Baileys WhatsApp bridge. No Java or .NET project manifests were found, so the AppCAT Java/.NET assessment workflow does not apply. This is a source-based readiness assessment, not an AppCAT report. No tests, builds, live account pairing, or dependency upgrades were run. Existing environment files, auth state, runtime data, and unrelated working-tree changes were left untouched; no message text, phone identifiers, auth state, or secrets are included here.

## WhatsApp analysis-to-frontend flow

1. The bridge accepts fresh incoming notifications, filters own/status/group/broadcast events, and requires the configured owner opt-in. It sends supported text or bounded media to the local backend; sender and guardian identifiers are HMACed before transmission.
2. Authenticated backend routes check owner opt-in and stored guardian state before analysis. Text/media is processed in memory; dedupe and rate limits use keyed digests and hashed identifiers. High-risk metadata may be recorded without message content.
3. The backend returns a decision and generic alert text. The bridge sends nothing unless the decision is eligible and both backend and bridge `DRY_RUN` settings permit live delivery. The default remains dry-run.
4. The frontend’s Analyze page calls the API through `src/api.ts`; input/results are component-local and API responses are not stored in browser history. Settings polls the local pairing proxy and offers a synthetic simulator; the proxy restricts access to the local Settings origin and keeps the bridge key server-side.

Relevant evidence: `whatsapp/bridge.mjs` (message handling, consent check, delivery gate); `backend/app/routers/whatsapp.py` (authenticated event/media routes and decision); `backend/app/services/alert_policy.py` (owner opt-in, consent, dedupe/rate limit); `frontend/src/api.ts`, `frontend/src/pages/Analyze.tsx`, `frontend/src/pages/Settings.tsx`, and `frontend/src/components/WhatsAppPairing.tsx`.

## Findings and blockers

### High — guardian consent is not independently obtained

`docs/TECH_DOC.md` §12.3 requires guardian confirmation and revocation. The current bridge enables the configured guardian automatically after the linked account connects (`whatsapp/bridge.mjs`); backend consent is then treated as enabled. Settings only displays the status; it has no consent/revoke action. The prior command-based UI branch remains, but the bridge currently returns no command. An environment-configured recipient is not evidence that the guardian personally consented. **Do not enable live monitoring/delivery until the consent policy and revocation path are resolved.**

### High — medium-risk events can be delivered

`docs/TECH_DOC.md` §12.2 specifies high-risk alerts, while `backend/app/routers/whatsapp.py` and `whatsapp/bridge.mjs` make both medium and high decisions eligible for delivery. Settings itself notes that alert thresholds are not calibrated for guardian alerts. This is a safety-policy/API behavior mismatch. Keep `DRY_RUN=true` until policy is reconciled and validated.

### High — real-world model/alert readiness remains unproven

The handoff records pending alert-severity calibration, URL false-positive/unseen-domain validation, human review, and realistic Urdu-media quality checks. Final test evaluation has already been consumed; do not use those test scores to tune thresholds or models. These gaps make live guardian alerts premature.

### Medium — WhatsApp verification coverage is thin

There is one backend WhatsApp policy test and no project-owned automated test files under `whatsapp/` (the package test command therefore has no bridge tests). The handoff records syntax/focused checks and a 176-test backend run, but not a full-suite rerun after the latest bridge/config changes. No dedicated account pairing or live delivery has been verified. Add synthetic contract tests for consent, medium/high decisions, both dry-run gates, media cleanup, and rate/dedupe behavior before live testing.

### Medium — frontend consent and pairing readiness is incomplete

The API types include consent and pairing contracts, but the frontend does not call consent endpoints or provide an explicit guardian consent/revocation flow. `WhatsAppPairing` still conditionally renders a guardian command that the bridge currently returns as null. Pairing is local-only and origin-bound; visually revalidate QR, disconnected/error, consent, simulator, and dry-run states after the latest bridge changes. The simulator is a useful no-delivery fallback.

### Medium — runtime documentation has drifted

`whatsapp/package.json` requires Node `>=22`, while `AGENTS.md` and `docs/TECH_DOC.md` still describe Node 20. The frontend manifest uses React 19 and React Router 7, while project guidance describes React 18. Align the setup/spec documentation and verify the supported runtime matrix.

## Positive readiness evidence

- The bridge/backend boundary is authenticated, uses bounded input/media, and sends keyed digests rather than sender identifiers.
- Inspected WhatsApp diagnostics expose decision metadata rather than message content; alert text is backend-generated and guardian-facing text is generic.
- `.env`, `whatsapp/auth_baileys/`, and backend runtime data are ignored by Git and are not tracked.
- Frontend API calls are centralized, generated API types are present, loading/error states exist, and Analyze input is kept in component state.
- The handoff records prior frontend typecheck/lint/build and desktop/mobile UI checks; these are historical evidence, not proof that the latest WhatsApp flow has been visually revalidated.

## Recommended next phase

Create a dependency-ordered modernization plan before implementation:

1. Resolve the consent model (separate owner and guardian opt-in, clear revocation/STOP behavior, and accurate Settings UI).
2. Reconcile high-only versus medium/high alert behavior with the documented risk policy; keep dry-run as the default and require both gates for any live test.
3. Freeze the API contract and add synthetic end-to-end/contract coverage for text, media, consent, dry-run, alert eligibility, and privacy-safe persistence/logging; regenerate frontend types if schemas change.
4. Complete validation using new independent/reviewed data only; do not retune on the consumed final test split. Keep URL and Urdu-media limitations visible.
5. Re-run backend/frontend checks, perform current desktop/mobile pairing-flow visual QA, and update runtime/setup documentation.
6. Only after these gates, plan a live test with the dedicated account and explicit consent from all participants.
