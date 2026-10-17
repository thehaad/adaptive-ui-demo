# AdaptiveUI Backlog

Last updated: 2026-10-17 · Target: **Build North, 2026-10-25** (8 days)

**Status key:** `Not started` · `Partial` (foundation exists, see notes) · `Blocked` (waiting on another item)

## Already done (for context, not outstanding)

- JSON layout schema and a platform-neutral renderer (`src/adaptive/`), independent of the demo app.
- Developer-registered components: `Row`, `Steps`, `WelcomeCard`, `PreferenceSelector`, `ActionButton`; density context (`comfortable` / `compact`).
- Product Capability Manifest ([capabilities.json](capabilities.json)): 4 option sets, 1 action (`complete_onboarding`), shared by backend and frontend.
- FastAPI backend with Claude Sonnet 5 composition: structured-output schema, catalog validation, one retry.
- Guided (`Steps`) and compact (`Row`) onboarding composed by Claude, with completion footer rules enforced by schema and validator.
- Host-controlled completion with a congratulations screen and a Start Over button; non-blocking telemetry.
- SQLite session telemetry (`telemetry_version` 2): layout, source (static / ai / fallback), per-event counters, completion; idempotent `PUT /api/sessions/{id}`.
- ≥ 44 pt touch targets; web layouts checked at 390 px and 1280 px.

---

## P0: Must complete for Build North (Oct 25)

| # | Item | Status | Next steps / done when |
|---|------|--------|------------------------|
| P0-1 | **Recurring fitness dashboard** with AI-driven composition, personalized from *stated* preferences (not learned behaviour) | Not started | Includes onboarding-answer capture. See details below. |
| P0-2 | **Deploy the MVP** with a browser-accessible demo | Blocked | Host the Expo web build and FastAPI on a public URL. **Blocked on P0-5 for public exposure of the personalization endpoint** (private or Claude-disabled deploys can proceed). Done when: a stranger can open the link, personalize, finish, and see telemetry written. Needs: production `EXPO_PUBLIC_API_URL`, CORS origins from config (currently hardcoded to localhost), a persistent location for the SQLite file (or accept reset on redeploy), the Anthropic key set only on the server. No Dockerfile, CI or hosting config exists yet. |
| P0-3 | **Document SDK integration and developer setup** | Partial | Only a 9-line [backend/README.md](backend/README.md) exists (partly stale); there is no root README. Write: quickstart (backend + Expo, `.env`, `uv`, ports), how to register components, write a manifest, and wire `AdaptiveRenderer`, `SessionContext` and actions. Note that `src/adaptive/` is the SDK boundary but is not yet packaged; document it as copy-in for now. |
| P0-4 | **Prepare the hackathon demo and submission** | Not started | Script a 3-minute flow (beginner vs experienced onboarding, then dashboard); rehearse offline/failure paths; prepare a fallback if the live Claude call is slow or down; write the submission text and capture screenshots. |
| P0-5 | **Public API protection and cost controls** | Partial | **Gate: must be done before the Claude-powered personalization endpoint is exposed publicly (P0-2).** Per-request bounds already exist (preference ≤ 500 chars, `max_tokens` 4000, at most 2 Claude calls per request, session layout ≤ 50 KB). Missing: per-client rate limits on `POST /api/layout/personalize` (and basic limits on `PUT /api/sessions/{id}`); a daily call/spend cap with a clean 429/503 that makes the app fall back to a static layout; a kill switch (env var) that disables Claude calls; CORS origins from config; a budget alert or limit set in the Anthropic console; logs that never contain the key or preferences. Done when: a scripted burst of requests is throttled, the cap trips and degrades gracefully, and the key is only in the server environment. |
| P0-6 | **Essential automated regression tests** | Not started | Commit a small, fast suite; scope below. Done when one documented command runs it with no network and no real Claude calls, and it passes before each deploy. |

### P0-1 details: recurring dashboard

Scope is deliberately small: **one** AI-composed dashboard screen reachable from the congratulations step, personalized from what the user *told us*.

- **Prerequisite: capture onboarding answers (stays in this milestone).** Selections currently live only in `PreferenceSelector` local state; neither the host nor the database sees *which* option was chosen (only counts). Without this the dashboard has nothing to personalize from. Add a host-side answers record (option-set id → value) and decide whether to persist it (this would be a schema change, so it needs sign-off).
- **Components:** the current library is onboarding-oriented. Plan on 2–3 new generic components (e.g. a metric/progress card and a simple list), registered by the host and described in the manifest.
- **Composition:** reuse the structured-output and validation pipeline with a dashboard schema/prompt; new endpoint or mode; keep the manifest-only rule (no invented data, options or routes).
- **Personalization basis: stated preferences only.** The initial dashboard adapts to the user's *stated* preferences: their onboarding answers and free-text preference. It is **not** learned behavioural optimization: no model of past behaviour, no cross-user data, no automatic layout selection. Behavioural signals (e.g. interaction counts) are at most simple, explainable inputs; anything learned belongs to P1 cross-user learning and P2 experimentation.
- **Done when:** two users who give different answers see visibly different dashboard compositions, the dashboard uses only manifest-approved components and data, and the session is recorded.

### P0-6 details: essential regression tests

Focus on the three areas where a regression would break the demo. Do **not** port every exploratory script.

- **Layout validation:** valid guided and compact compositions; rejection cases (unknown component, prop, option set or action; no, duplicate or misplaced completion button; a final Steps question that is not a `PreferenceSelector`; fewer than 2 steps; nested containers; route-like props); the structured-output schema keeps `ActionButton` out of `children` and requires `completion`.
- **AI output handling (mocked Claude, no network):** valid output is assembled into a flat layout with a stable id; one retry after an invalid layout, with the errors fed back; failure after exactly two attempts; missing API key returns 503; no structured output or refusal is handled; `GET /api/layout` still works.
- **Session recording (temp SQLite database):** idempotent `PUT` replay; out-of-order and stale snapshots cannot lower counters; a completed session cannot reopen or change its completion time; `interaction_count` equals the sum of event counts; unknown events, bad totals, bad layouts and immutable-field changes are rejected (422/409); rows survive a restart; the client outbox keeps a failed record and retries without duplicating completion.
- **Out of scope for P0:** browser and visual scripts, real-Claude checks, performance tests.
- **Tooling note:** the backend suite would likely use `pytest` (a new dev dependency that needs approval); the recorder logic can run on Node's built-in test runner with no new dependency.

### Dependencies and order

P0-1 needs the answers capture first. P0-6 should land early so later work is protected. **P0-5 must be finished before P0-2 exposes the endpoint publicly**; until then, keep the deployment private or Claude-disabled. P0-3 can proceed in parallel; P0-4 follows them all.

---

## P1: Important improvements if time permits

| Item | Status | Notes |
|------|--------|-------|
| Developer-defined **required and optional fields** | Not started | Today every question is optional and Next is always enabled. Add a `required` flag (manifest or component prop) that the validator and renderer understand. |
| **Single-selection and multi-selection** support | Not started | `PreferenceSelector` is single-select only. Add a mode (`single` / `multi`) and record `selection_changed` for toggles. |
| **Minimum / maximum selection** constraints | Not started | Needed for multi-select (e.g. choose 1–3); depends on the item above. |
| **Validation before advancing or completing** onboarding | Blocked | Depends on required fields and selection constraints. Block Next/Finish with clear inline messages, without breaking the non-blocking completion telemetry. |
| **Cross-user learning** from onboarding outcomes | Blocked | Needs selections captured (see P0-1), a defined "outcome" beyond completion, and enough sessions. Start with offline analysis, not automatic layout selection. |
| **Basic session analytics and layout comparisons** | Partial | The data exists (`sessions`: layout JSON, counts, status, timestamps). Missing: queries or a simple report comparing layouts (completion rate, interactions, time to complete). Not a dashboard product. |
| **Preserve automated tests in the repository** (beyond the P0 essentials) | Partial | The essential regression suite is **P0-6**. What remains here: browser/visual checks, a real-Claude smoke test (opt-in, costs money), recorder end-to-end checks against a live server, and lint (`npx expo lint` would install ESLint; AGENTS.md expects lint before completion). Exploratory scripts need not all be kept. |
| **Security review and deployment safeguards** (beyond P0-5) | Partial | The API key is already backend-only and `.env` is git-ignored; rate limiting, spend caps, CORS config and key-safe logging moved to **P0-5**. Remaining: authentication options, privacy notice and retention decision for the stored free-text preference, dependency audit, request-size review, and abuse monitoring. |

---

## P2: Post-hackathon product roadmap

| Item | Status | Notes |
|------|--------|-------|
| **Developer administration studio** | Not started | Replace the hand-edited `capabilities.json` and registry with a UI for components, option sets and actions. |
| **Dynamic data-source registration and pagination** | Not started | Let hosts register data sources (lists, metrics) with paging; the AI references sources by id, never raw queries. |
| **Persistent telemetry and reliable offline synchronization** | Partial | Server persistence (SQLite) and idempotent merges exist. Missing: durable client outbox (localStorage / async storage), background retry, production database. |
| **Native SwiftUI and Jetpack Compose SDKs** | Not started | The JSON layout and manifest are already platform-neutral; each SDK needs a renderer, component registry and session client. |
| **Full-application UI composition** | Not started | Beyond onboarding and one dashboard: navigation, multiple screens, host-defined routes (still no AI-generated routes). |
| **More advanced personalization and experimentation** | Not started | A/B allocation, outcome-driven layout selection, guardrails. Depends on cross-user learning and analytics. |

---

## Known technical limitations and risks

| Area | Limitation / risk | Mitigation or plan |
|------|-------------------|--------------------|
| Telemetry durability | The outbox is in memory only: records are lost if the app closes while the server is unreachable. Retries are triggered by the next interaction or new session; there is no polling, so a final completion made offline may never be sent. | P2 durable outbox. |
| Telemetry trust | Session ids, timestamps and counts are client-attested. The server checks consistency, not truth. | Acceptable for the demo; revisit with auth and server-issued sessions. |
| Security | No production authentication, no multi-tenant isolation, no rate limiting; any caller can create sessions and trigger Claude calls. | **P0-5 is a gate**: do not expose the personalization endpoint publicly without rate limits, a spend cap and a kill switch. Auth and isolation stay in P1/P2. |
| Composition scope | Claude can only compose a limited library (5 components, 4 option sets, 1 action). A `Steps` step is a single component, so one decision can span two steps when Claude adds an explanation card. | Expand the library deliberately; consider a restricted step group later. |
| Schema enforcement | The SDK strips `const`, so component names and option-set ids are enforced by the validator and retry, not the schema alone. | Keep validation authoritative. |
| Shared manifest | Backend and frontend share `capabilities.json` by relative path, which assumes one repository. | Publish the manifest as an artifact or endpoint if they are deployed separately. |
| Data captured | Only event counts are stored, not which options were chosen. | Addressed in P0-1 (answers capture). |
| Privacy | The free-text preference is stored as typed; a UI hint asks users to avoid personal details but cannot enforce it. | P1 privacy notice and retention decision. |
| Devices | Native iOS/Android behaviour has not been fully tested; verification so far covered Expo web in desktop Chrome at 390 px and 1280 px. | Test on a device or emulator before claiming native support. |
| Personalization claims | Current personalization has not demonstrated measurable improvement in real-user outcomes; guided vs compact is a prompt-guided difference, not a validated one. | Phrase demo claims carefully; P1 analytics. |
| Model availability | A live Claude call is on the demo critical path; latency, outages and credit limits are risks, and the app falls back to static layouts only when the layout endpoint itself fails. | P0-4 demo fallback plan. |
| Schedule | Eight days to Build North with deployment, docs, dashboard, API protection, tests and demo all outstanding. | Cut order: dashboard polish and adaptation detail first. Never cut API protection (P0-5), the essential tests (P0-6), deployment or demo preparation. |
| Tests | No tests are committed, so layout validation, AI output handling and session recording currently have no regression protection. | P0-6. |
