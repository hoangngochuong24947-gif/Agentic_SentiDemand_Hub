# Frontend Rebuild Progress

Last updated: 2026-04-25.

## Phase Status

| Phase | Name | Status | Notes |
| --- | --- | --- | --- |
| Phase 0 | Rebuild memory and guardrails | Complete | Required docs and lightweight check script are in place. |
| Phase 1 | Interface rebuild preparation | Complete enough for handoff | React/Vite shell, route screens, current endpoint adapters, and `/app` serving are in place. |
| Phase 2 | Versioned API contract and integration | Complete | `/api/v1` is mounted; async upload jobs are implemented; React prefers v1 with legacy fallback and upload polling. |
| Phase 3 | Browser verification and structured outputs | Complete enough for Phase 4 handoff | Structured chart endpoint/cards, structured advice sections, fallback preservation, and screenshot smoke checks are recorded. |
| Phase 4 | Storage, export, session, and job controls | Complete enough for handoff | JSON-backed storage adapter, export zip endpoint, job cancel primitives, and React export/cancel UI are implemented and verified. |

## Completed In This Pass

- Added the rebuild plan document.
- Added the rebuild memory document.
- Added this progress tracker.
- Added the documentation guard script.

## Current Guardrail

The new script checks whether `frontend/` or `src/comment_analyzer/api/` has Git status changes. If so, it requires these docs to exist and be non-empty:

- `docs/frontend_rebuild_plan.md`
- `docs/frontend_rebuild_memory.md`
- `docs/frontend_rebuild_progress.md`

## Open Work

- Convert Phase 1 route notes into concrete frontend tasks before source edits begin.
- Decide whether the guard script should be wired into existing hooks.
- After frontend implementation starts, update this file after each pass with changed routes, verification results, and known risks.

## Known Constraints

- Do not overwrite unrelated user or agent changes.
- Do not modify frontend source during the documentation pass.
- Keep copy compact and label-first when frontend work begins.
# 2026-04-25 Phase 1 Implementation Update

## Changes

- Created the React/Vite/TypeScript frontend under `frontend/`.
- Implemented route screens for Upload, Runs, Workspace tables, Chart dashboard, Insights, and Run Detail.
- Connected Phase 1 to current Hub endpoints instead of the not-yet-existing `/api/v1` API.
- Reused existing chart HTML artifacts through iframes.
- Added FastAPI static serving for the production build at `/app`.
- Added the frontend rebuild doc guard script.

## Verification

- `cd frontend && npm install`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_visualization.py tests/test_run_registry.py`
- Playwright smoke checks:
  - `http://127.0.0.1:8877/app`
  - `http://127.0.0.1:8877/app/workspace/6fb0fd8ddf0b`
  - `http://127.0.0.1:8877/app/dashboard/6fb0fd8ddf0b`

## Bugs Fixed During Verification

- Set Vite `base` to `/app/` so built CSS/JS assets load from the FastAPI-mounted React path.
- Added React Router basename from `import.meta.env.BASE_URL` so `/app/*` routes render instead of a blank page.
- Added frontend-side artifact link synthesis because `/api/runs/{run_id}` returns raw artifact records without the server-rendered `open_url` / `download_url` fields.

## Remaining

- Run backend regression tests.
- Browser-check `/`, `/workspace/{run_id}`, `/dashboard/{run_id}`, `/insights/{run_id}`, `/runs/{run_id}` in Vite dev.
- Begin Phase 2 `/api/v1` extraction and async job model after Phase 1 UI is visually accepted.

# 2026-04-25 Phase 2 Documentation Start

## Scope

- Phase 2 has started.
- This pass updates only rebuild docs, README, and Hub runbook memory.
- No frontend or backend source should be changed by the documentation/memory worker.

## Division Of Work

- Backend/API worker: design and implement `/api/v1` endpoints, upload job lifecycle, stable run/artifact payloads, and error envelopes.
- Frontend worker: migrate Phase 1 screens to the `/api/v1` contract after the contract is available, preserving the accepted routes and visual direction.
- Documentation/memory worker: record contract goals, verification commands, progress, and next steps in the rebuild docs, README, and Hub runbook.

## `/api/v1` Contract Goal

- Keep current routes and legacy pages available while adding versioned API routes.
- Provide stable JSON for run list, run detail, tables, charts, logs, insights, upload submission, job status, artifact open/download metadata, and errors.
- Make async analysis explicit: submit upload, poll job, then navigate to the completed run.

## Verification Target

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- Browser smoke against `http://127.0.0.1:8765/app` and Vite dev routes after backend/frontend workers make source changes.

## Next

- Backend/API worker drafts the v1 payload shapes.
- Frontend worker aligns adapters and route data loading to those shapes.
- Documentation/memory worker records each Phase 2 pass and any contract changes.

# 2026-04-25 Phase 2 API Handoff Integrated

## Changes

- Added stable API v1 source under `src/comment_analyzer/api/`.
- Added API tests in `tests/test_api_v1.py`.
- Mounted `/api/v1` routes into the existing Hub server so React at `/app` can use the new contract on the same host.
- Updated React API adapter to prefer `/api/v1` for health, runs, run detail, upload, and insight generation with legacy fallback.

## Verification

- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `python scripts/check_frontend_rebuild_docs.py`
- HTTP smoke:
  - `/api/v1/health`
  - `/api/v1/runs`
  - `/api/v1/runs/6fb0fd8ddf0b`
  - `/api/v1/runs/6fb0fd8ddf0b/charts`

# 2026-04-25 Phase 2 Async Job Closure

## Changes

- Changed `/api/v1/data/upload` to return immediately with `job_id` and `status="queued"`.
- Added background pipeline execution that updates job state while analysis runs.
- Added six upload steps: `Upload`, `Clean`, `Sentiment`, `Topics`, `Demand`, `Charts`.
- `/api/v1/analysis/jobs/{job_id}` now returns `steps`, `progress`, `run_id`, `result`, and `error`.
- React upload flow now polls job status and displays the six-step progress before navigating to the run workspace.

## Verification

- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `python scripts/check_frontend_rebuild_docs.py`

## Next

- Resume Phase 3: structured chart data and structured advice with iframe/markdown fallback.

# 2026-04-25 Phase 3 Documentation Start

## Scope

- Phase 3 has started.
- This pass records Phase 3 memory only and does not change frontend or backend source.
- The active focus is browser verification plus structure checks for charts and AI advice.

## Division Of Work

- Browser verification worker: validate the built `/app` route and Vite dev routes across desktop/mobile smoke checks.
- Chart structure worker: confirm chart records expose stable metadata for cards, status, reason, open/download actions, and legacy HTML artifact fallback.
- Advice structure worker: confirm insights can be presented as compact structured sections: Findings, Actions, Risks, and supporting context.
- Documentation/memory worker: record goals, verification commands, and fallback principles in the rebuild docs, README, and Hub runbook.

## Phase 3 Goals

- Keep existing Hub routes, `/api/v1`, and React routes working together.
- Make chart-facing responses structured enough that React does not need to scrape chart HTML for route UI.
- Make advice output structured enough for operational blocks instead of a single long text wall.
- Preserve iframe fallback for existing ECharts HTML artifacts until structured chart rendering fully replaces it.

## Verification Target

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- Browser smoke:
  - `python -m comment_analyzer.visualization.gallery`
  - `cd frontend && npm run dev`
  - Check `http://127.0.0.1:8765/app`
  - Check Vite Upload, Runs, Workspace, Dashboard, Insights, and Run Detail routes.

## Next

- Run browser checks and record any route-level rendering issues.
- Inspect chart and advice payloads against the structured output goals.
- Keep iframe fallback available for all existing chart HTML artifacts.

# 2026-04-25 Phase 3 Structured Charts And Advice Integrated

## Changes

- Added `GET /api/v1/runs/{run_id}/chart-data` with five stable structured chart candidates.
- Added structured advice payloads with `findings`, `actions`, `risks`, and `context`.
- Updated React Dashboard to prefer native structured charts while keeping legacy chart artifacts visible.
- Updated React Insights to render structured advice sections with markdown fallback.
- Fixed long run title wrapping so desktop and mobile routes do not horizontally overflow.

## Verification

- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `python scripts/check_frontend_rebuild_docs.py`
- HTTP smoke on `http://127.0.0.1:8891`:
  - `/api/v1/health`
  - `/api/v1/runs`
  - `/api/v1/runs/6fb0fd8ddf0b/chart-data`
  - `/app/`
- Playwright screenshots:
  - `docs/frontend_rebuild_screenshots/phase3-upload-desktop.png`
  - `docs/frontend_rebuild_screenshots/phase3-dashboard-desktop.png`
  - `docs/frontend_rebuild_screenshots/phase3-insights-mobile.png`

## Next

- Begin Phase 4: storage abstraction, export endpoint, session key hardening, and job controls.

# 2026-04-25 Phase 3 Structured Outputs In Progress

## Changes

- Phase 2 async upload closure is now recorded as complete: `/api/v1/data/upload` returns queued jobs and React polls `/api/v1/analysis/jobs/{job_id}` before navigating to the completed run.
- Phase 3 implementation is active for structured chart data exposed through the chart endpoint so React can render native chart cards without scraping HTML.
- React-native chart cards are in progress with structured metadata, status/reason handling, and open/download actions while preserving iframe fallback for existing ECharts HTML artifacts.
- Structured advice sections are in progress for Findings, Actions, Risks, and supporting context while preserving markdown/plain text as a fallback artifact.

## Fallback Policy

- Existing chart HTML remains openable and embeddable through iframe fallback until structured rendering is fully verified.
- Existing advice markdown/plain text remains displayable if structured sections are unavailable or incomplete.
- Phase 3 UI should prefer structured payloads when present, then gracefully fall back to legacy artifacts.

## Verification

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- Browser smoke for `/app` and Vite routes

## Status

- Implementation: in progress.
- Verification: pending for this Phase 3 structured-output pass.

# 2026-04-25 Phase 4 Documentation Start

## Scope

- Phase 4 is active.
- This pass updates only rebuild docs, README, and Hub runbook memory.
- Documentation/memory ownership remains limited to `docs/frontend_rebuild_memory.md`, `docs/frontend_rebuild_progress.md`, `docs/frontend_rebuild_plan.md`, `README.md`, `docs/HUB_RUNBOOK.md`, and the doc checker if needed.

## Division Of Work

- Backend/API worker: implement the run storage abstraction, `POST /api/v1/export/results`, session hardening prep, and job cancel/control primitives.
- Frontend worker: add export and cancel/control UI against the Phase 4 API surfaces while keeping upload polling and legacy fallbacks stable.
- Documentation/memory worker: record intent, active endpoints, verification targets, and known pending checks without editing frontend/backend source.

## Phase 4 Progress Entry

- Storage abstraction: active target. Keep current local JSON/file-mode behavior working while preparing for SQLite and multi-user storage.
- Export endpoint: active target. Add unified results export through `POST /api/v1/export/results`, with response shape and downloadable artifact behavior to be verified by source workers.
- Job controls: active target. Add cancel/control primitives, including cancel status, retry-friendly failure state, and local concurrency limits.
- Frontend export/cancel UI: active target. Add visible export and cancel affordances once API contracts are available.
- Session hardening prep: active target. Avoid storing plain DeepSeek keys on disk and keep session behavior explicit.

## Verification Target

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- HTTP smoke after source workers land changes:
  - `POST /api/v1/export/results`
  - `GET /api/v1/analysis/jobs/{job_id}`
  - Cancel/control endpoint selected by backend worker
  - Built React export/cancel flows under `/app`

## Status

- Implementation: completed for the conservative Phase 4 pass.
- Verification: completed in the 2026-04-26 Phase 4 integration entry below.

# 2026-04-26 Phase 4 Integration Verified

## Changes

- Added JSON-backed API storage abstraction in `src/comment_analyzer/api/storage.py`.
- Added `POST /api/v1/export/results` and `GET /api/v1/export/results/{export_id}/download`.
- Added zip export creation with `manifest.json`, selected artifact groups, and included counts.
- Added job cancel primitives through `POST /api/v1/analysis/jobs/{job_id}/cancel`.
- Added React export actions on Workspace, Dashboard, and Run Detail.
- Added upload cancel-request UI for queued/running jobs.
- Aligned frontend cancel contract with backend `cancellation_requested`.
- Improved wide table previews with horizontal scrolling and fixed minimum column width.

## Verification

- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `python scripts/check_frontend_rebuild_docs.py`
- HTTP smoke on `http://127.0.0.1:8892`:
  - `/api/v1/health`
  - `/api/v1/runs`
  - `/api/v1/runs/6fb0fd8ddf0b/chart-data`
  - `POST /api/v1/export/results`
  - `GET /api/v1/export/results/{export_id}/download`
  - `/app/`
- Playwright screenshots:
  - `docs/frontend_rebuild_screenshots/phase4-workspace-export-desktop.png`
  - `docs/frontend_rebuild_screenshots/phase4-upload-cancel-desktop.png`

## Remaining Risk

- Job cancellation is cooperative metadata only; it does not terminate a running pipeline thread.
- Export includes artifacts with existing file paths; pathless/missing artifacts are skipped and reflected in included counts.

# 2026-04-26 Advice Backend Session And Prompt Fix

## Changes

- Fixed `/api/v1/runs/{run_id}/insights/generate` so it resolves the DeepSeek key from backend session storage when React sends `session_id`.
- Kept prompt construction fully in the backend; React only sends `session_id` and triggers generation.
- Added a clean backend Chinese advice prompt for structured Findings / Actions / Risks / Context output.
- Added backend DeepSeek call helper for v1 advice generation instead of depending on legacy page prompt wiring.
- Persisted and returned `advice_markdown` and `structured_advice` in run detail so refreshing the Advice route keeps generated content visible.
- Added regression coverage for session-backed advice generation and run-detail advice reload.

## Verification

- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
