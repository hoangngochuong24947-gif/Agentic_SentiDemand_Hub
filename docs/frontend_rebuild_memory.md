# Frontend Rebuild Memory

This file preserves the working memory for the SentiDemand Hub frontend rebuild so future agents can continue without rediscovering the plan.

## Current State

- Phase 0 is done: documentation, memory, progress tracking, and the doc guard script exist.
- Phase 1 is complete enough for handoff: the React/Vite frontend exists under `frontend/` and is connected to the current Hub endpoints.
- Phase 2 is done: `/api/v1` is implemented and mounted into the existing Hub; React now prefers v1 with legacy fallback; upload now runs as a background job with polling progress.
- Phase 3 is done enough for Phase 4 handoff: structured chart endpoint/card data, structured advice sections, fallback preservation, and browser screenshot verification are in place.
- Phase 4 is complete enough for handoff: storage abstraction, `POST /api/v1/export/results`, job cancel primitives, and frontend export/cancel UI are implemented and verified.
- The FastAPI Hub can serve the built React app at `/app` after `frontend/dist` is generated.
- Current Phase 4 verification has passed for API v1 tests, old Hub tests, frontend typecheck/build, HTTP smoke, screenshots, and doc guard.

## Phase 2 Working Memory

Division of work:

- Backend/API worker: implemented the `/api/v1` contract, async upload/job lifecycle, stable run/artifact payloads, and compatibility adapters for existing Hub data.
- Frontend worker: consumes the `/api/v1` contract with legacy fallback, keeps Phase 1 routes intact, and preserves the calmer operational UI direction.
- Documentation/memory worker: keep `docs/frontend_rebuild_memory.md`, `docs/frontend_rebuild_progress.md`, `docs/frontend_rebuild_plan.md`, `README.md`, and `docs/HUB_RUNBOOK.md` current without touching source code.

`/api/v1` contract target:

- Use versioned endpoints under `/api/v1` for new frontend integration.
- Prefer stable JSON envelopes for runs, artifacts, charts, tables, logs, insights, upload jobs, job status, and errors.
- Keep existing routes working while the v1 contract is introduced.
- Make upload analysis explicit as a job flow: submit, poll status, then open the created run. This is now implemented for `/api/v1/data/upload`.

Phase 2 async closure:

- `POST /api/v1/data/upload` saves the upload, creates a job, returns immediately with `job_id`, `run_id=""`, and `status="queued"`.
- Background execution runs the existing pipeline and updates job state.
- `GET /api/v1/analysis/jobs/{job_id}` returns `steps`, `progress`, `run_id`, `result`, and `error`.
- Upload progress uses six stages: `Upload`, `Clean`, `Sentiment`, `Topics`, `Demand`, `Charts`.
- React stores the returned `job_id`, polls the job endpoint, shows the six-step progress, and navigates to `/workspace/{run_id}` after completion.

Phase 2 verification commands:

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- Browser smoke after services start:
  - `python -m comment_analyzer.visualization.gallery`
  - `cd frontend && npm run dev`
  - Check `http://127.0.0.1:8765/app` and Vite dev routes.

## Phase 3 Working Memory

Division of work:

- Browser verification worker: run the Hub and Vite paths, capture desktop/mobile smoke checks, and report route-level issues without changing product scope.
- Chart structure worker: verify that chart-facing data is structured enough for React screens to render cards, metadata, open/download actions, and quiet missing states without parsing raw HTML.
- Advice structure worker: verify generated insight/advice responses can be presented as structured blocks: Findings, Actions, Risks, and supporting context.
- Documentation/memory worker: keep `docs/frontend_rebuild_memory.md`, `docs/frontend_rebuild_progress.md`, `docs/frontend_rebuild_plan.md`, `README.md`, and `docs/HUB_RUNBOOK.md` current without touching source code.

Phase 3 goals:

- Built React at `/app` works against the Hub after `npm run build`.
- Structured chart data is exposed through `GET /api/v1/runs/{run_id}/chart-data`.
- React Dashboard renders native structured chart cards first and keeps legacy HTML chart artifacts visible.
- Structured advice is returned and rendered as compact Findings, Actions, Risks, and Context sections.
- Markdown advice remains available as a fallback/artifact.
- Iframe/open-link fallback remains available for existing ECharts HTML artifacts.

Phase 3 implemented:

- `GET /api/v1/runs/{run_id}/chart-data` returns stable chart candidates for sentiment, keywords, features, topics, and demand.
- React chart cards prefer structured data when available, then fall back to iframe/open links for legacy ECharts HTML artifacts.
- `POST /api/v1/runs/{run_id}/insights/generate` includes `structured_advice`.
- Advice rendering prefers structured sections when available, then falls back to markdown or plain prose artifacts without blocking display.
- Long run titles wrap on desktop and mobile without horizontal overflow.

Phase 3 verification commands:

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- HTTP smoke after services start:
  - `python -m comment_analyzer.visualization.gallery --port 8891`
  - Check `/api/v1/health`, `/api/v1/runs`, `/api/v1/runs/{run_id}/chart-data`, and `/app/`.
- Playwright screenshot paths:
  - `docs/frontend_rebuild_screenshots/phase3-upload-desktop.png`
  - `docs/frontend_rebuild_screenshots/phase3-dashboard-desktop.png`
  - `docs/frontend_rebuild_screenshots/phase3-insights-mobile.png`

## Implemented This Pass

- Added React routes for Upload, Runs, Tables, Charts, Advice, and Run Detail.
- Added typed adapters for current endpoints: `/api/manifest`, `/api/runs/{run_id}`, `/upload`, `/api/session/deepseek-key`, `/api/runs/{run_id}/insights/generate`.
- Added hooks: `useRuns`, `useRun`, `useUploadRun`, `useRunTables`, `useRunCharts`, `useRunLogs`, `useDeepSeekSession`, `useGenerateInsight`, `useRebuildProgress`, `useFeatureFlag`.
- Added `/app` static serving in `src/comment_analyzer/visualization/gallery.py`.
- Verified `npm run typecheck`, `npm run build`, and `python scripts/check_frontend_rebuild_docs.py`.

## Next Step

- The planned frontend rebuild phases are complete enough for handoff.
- Future hardening should focus on true SQLite persistence, stronger session/auth boundaries, and cooperative cancellation checks inside long-running pipeline stages.
- Keep this file updated after any new API, frontend, or storage hardening pass.

## Phase 4 Working Memory

Phase 4 is complete enough for handoff.

Division of work:

- Backend/API worker: storage abstraction, `POST /api/v1/export/results`, session hardening prep, job cancel/control primitives, local concurrency limits, and retry-friendly failed/canceled job states.
- Frontend worker: export and cancel/control UI, wired to the Phase 4 API surfaces while preserving upload polling and legacy fallback behavior.
- Documentation/memory worker: update only rebuild docs, README, Hub runbook, and the doc checker if needed; do not edit frontend or backend source.

Target scope:

- Introduce a run storage abstraction so the registry can evolve beyond a direct JSON file.
- Add a unified export endpoint through `POST /api/v1/export/results`.
- Harden DeepSeek/session handling without writing plain API keys to disk.
- Add job control primitives for local operation: cancel status and retry-friendly failure state.
- Keep local demo file-mode behavior working while preparing for SQLite/multi-user evolution.

Implemented:

- `src/comment_analyzer/api/storage.py` wraps the existing JSON `RunRegistry` behind a storage interface.
- `POST /api/v1/export/results` creates a zip export with `manifest.json`, selected artifact groups, and included counts.
- `GET /api/v1/export/results/{export_id}/download` downloads the generated zip.
- `POST /api/v1/analysis/jobs/{job_id}/cancel` marks queued jobs canceled and running jobs as cancel requested/canceling.
- React Workspace, Dashboard, and Run Detail expose compact Export actions.
- React upload progress exposes Cancel analysis for queued/running jobs and reads backend `cancellation_requested`.
- Wide table previews use horizontal scrolling and minimum column widths.
- Advice generation now resolves DeepSeek keys from backend session storage when React sends `session_id`; prompt construction stays in the backend.
- Run detail now returns persisted `advice_markdown` and `structured_advice`, so Advice reloads do not lose generated content.

Phase 4 verification target:

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- HTTP smoke for `POST /api/v1/export/results`, job status/control endpoints, and built React export/cancel flows.

Verification status:

- Passed: `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`.
- Passed: `cd frontend && npm run typecheck`.
- Passed: `cd frontend && npm run build`.
- Passed: `python scripts/check_frontend_rebuild_docs.py`.
- Passed HTTP smoke on `http://127.0.0.1:8892` for health, runs, chart-data, export create/download, and `/app/`.
- Screenshots:
  - `docs/frontend_rebuild_screenshots/phase4-workspace-export-desktop.png`
  - `docs/frontend_rebuild_screenshots/phase4-upload-cancel-desktop.png`

Remaining risks:

- Job cancellation is cooperative metadata only; it does not kill a running Python pipeline thread.
- Export includes only artifacts with existing file paths; missing/pathless artifacts are skipped and counted accordingly.
- DeepSeek session keys are still in process memory; full persistent secure session/auth remains future hardening.

## Rebuild Intent

The user-provided plan asks for a full frontend rebuild that keeps the product functionality but makes the interface quieter, more compact, and more polished.

Preserve:

- Upload and analysis workflow
- Run list and run statuses
- Table previews and downloads
- Chart gallery and chart details
- AI advice generation
- Legacy run detail access

Improve:

- Reduce visible explanatory text.
- Use compact labels instead of paragraphs.
- Make dashboards feel operational rather than marketing-oriented.
- Use light, calm chart surfaces.
- Make missing states quiet and non-dominating.
- Preserve mobile usability.

## Visual Memory

Preferred style:

- Warm ivory and oatmeal surfaces
- Charcoal text
- Clay/rust accents
- Sage status color
- Thin warm-gray borders
- Subtle surfaces and low shadow
- Refined typography
- Dense but readable data areas

Avoid:

- Purple-blue gradients
- Neon or glossy dashboards
- Dark chart canvases
- Decorative blobs
- Stock-photo atmosphere
- Nested cards
- Long Chinese paragraphs

## Route Memory

Home:

- Upload area is the primary working surface.
- Recent runs stay visible.
- Crawler scripts are compact tiles.

Workspace:

- Left run history.
- Main artifact grid.
- Search, open, download remain available.

Dashboard:

- Two-column chart gallery on desktop.
- Missing charts use quiet placeholders.
- Chart titles stay short.

Insights:

- API key controls are compact.
- Advice output should become structured blocks: Findings, Actions, Risks.
- Export actions remain visible.

Chart detail:

- Large light-theme chart canvas.
- Compact metadata and actions.

Run detail:

- Audit-style combined view for Tables, Logs, Charts.
- No raw log wall or large paragraphs.

Mobile:

- Compact top bar.
- Segmented navigation.
- Sticky action bar.

## Guardrail Memory

`scripts/check_frontend_rebuild_docs.py` should be safe and narrow:

- Read repository changes using Git.
- Detect changed paths under `frontend/` or `src/comment_analyzer/api/`.
- If no guarded path changed, exit successfully.
- If guarded path changed, require all three docs to exist and have non-whitespace content.
- Print actionable messages and exit non-zero on failure.
