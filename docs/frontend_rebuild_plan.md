# Frontend Rebuild Plan

Source: user-provided rebuild direction and the generated visual prompts in `docs/frontend_rebuild_gptimage_prompts.md`.

## Scope

This plan tracks the documentation and memory layer for the frontend rebuild. The current implementation pass must not modify frontend source code.

Guarded paths:

- `frontend/`
- `src/comment_analyzer/api/`

Required rebuild memory docs:

- `docs/frontend_rebuild_plan.md`
- `docs/frontend_rebuild_memory.md`
- `docs/frontend_rebuild_progress.md`

## Product Direction

Keep the existing SentiDemand Hub functions while rebuilding the interface into a calmer, more operational analytics app.

Core routes to preserve:

- Home upload command center
- Workspace tables
- Run detail
- Dashboard chart gallery
- Insights advice
- Standalone chart detail

Functional objects to preserve:

- Upload: CSV, XLSX, XLS, JSON
- Run history and status
- Table artifacts and previews
- Chart artifacts and missing states
- DeepSeek advice generation
- Open and download actions
- Legacy combined run detail compatibility

## Design Direction

Use a warm, restrained product interface:

- Warm ivory/oatmeal background
- Charcoal typography
- Muted clay or rust accent
- Subtle sage success/status color
- Thin warm-gray borders
- Light chart surfaces
- Rounded corners up to 8px except small pills
- Compact, label-first copy

Avoid:

- Long explanatory paragraphs
- Marketing landing-page hero treatment
- Nested cards
- Glossy blue SaaS styling
- Purple gradients
- Neon or dark chart canvases
- Decorative blobs
- Heavy shadows
- Large warning panels

## Phase 0 - Rebuild Memory And Guardrails

Status: complete enough for handoff.

Goals:

- Record the rebuild plan in docs.
- Maintain a persistent memory file for future agents.
- Maintain a progress file that can be updated after each rebuild pass.
- Add a lightweight check script that requires these docs whenever frontend or API files change.
- Avoid touching frontend source during this documentation pass.

Exit criteria:

- Required docs exist and are non-empty.
- `scripts/check_frontend_rebuild_docs.py` exists.
- The check script passes when guarded paths are changed only if docs are present and non-empty.

## Phase 1 - Interface Rebuild Preparation

Status: complete enough for handoff.

Goals:

- Translate the visual prompts into implementation-ready route requirements.
- Keep all current routes and user workflows intact.
- Reduce visible copy by roughly 70 percent.
- Prefer compact labels: Upload, Runs, Tables, Charts, Advice, Open, Download, Ready, Missing.
- Prepare route-by-route acceptance notes before frontend source changes begin.

Phase 1 route targets:

- Home: upload panel, recent runs, crawler script tiles.
- Workspace: run list, artifact panels, searchable previews, open/download actions.
- Dashboard: chart grid, missing placeholders, light chart previews.
- Insights: API key row, generate action, structured advice blocks.
- Chart detail: large inspectable chart canvas with compact metadata.
- Run detail: audit-style Tables, Logs, Charts columns.
- Mobile: compact top bar, segmented navigation, sticky actions.

## Phase 2 - Versioned API Contract And Integration

Status: complete.

Working split:

- Backend/API worker owns `/api/v1` contract design and implementation.
- Frontend worker owns route integration against the versioned contract.
- Documentation/memory worker owns progress, memory, README, and Hub runbook updates.

Contract goals:

- Add new versioned endpoints under `/api/v1`.
- Keep existing Hub routes and legacy pages available during migration.
- Stabilize payloads for runs, run detail, table artifacts, chart artifacts, logs, insights, upload jobs, job status, artifact open/download metadata, and errors.
- Treat upload analysis as an explicit async flow: submit upload, poll job status, then open the completed run.

Validation commands:

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`

Completed:

- `/api/v1` is mounted into the existing Hub while legacy routes remain available.
- Upload analysis is now an async job flow: submit upload, poll job status, then open the completed run.
- React prefers v1 endpoints with legacy fallback and polls upload job progress.
- Browser smoke checks continue under Phase 3.

## Phase 3 - Browser Verification And Structured Outputs

Status: complete enough for Phase 4 handoff.

Working split:

- Browser verification worker owns `/app` and Vite route smoke checks, including desktop and mobile viewport notes.
- Chart structure worker owns review of chart-facing payloads and metadata.
- Advice structure worker owns review of insight/advice payloads and UI-ready sections.
- Documentation/memory worker owns progress, memory, README, and Hub runbook updates.

Goals:

- Verify the React rebuild works through the FastAPI-served `/app` path and Vite dev routes.
- Confirm structured chart payloads can support chart cards, chart detail, missing states, status/reason text, and open/download actions.
- Confirm structured advice can support compact blocks for Findings, Actions, Risks, and supporting context.
- Keep legacy ECharts HTML available through open links and iframe fallback. Structured chart rendering should enhance the route UI, not remove compatibility with existing generated HTML.

Completed:

- Structured chart endpoint/card data is available so React can render native cards with title, type, status, reason, preview/open/download metadata, and quiet missing states.
- Structured advice sections are available for Findings, Actions, Risks, and supporting context.
- Markdown/plain text advice output and iframe chart rendering remain the required fallback policy.

Validation commands:

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`

Browser smoke target:

- Start Hub: `python -m comment_analyzer.visualization.gallery`
- Start Vite: `cd frontend && npm run dev`
- Check built app: `http://127.0.0.1:8765/app`
- Check Vite routes for Upload, Runs, Workspace, Dashboard, Insights, and Run Detail.

## Phase 4 - Storage, Export, Session, And Job Controls

Status: active.

Working split:

- Backend/API worker owns the storage abstraction, `POST /api/v1/export/results`, session hardening prep, local concurrency limits, cancel status, and retry-friendly job failure state.
- Frontend worker owns export and cancel/control UI, keeping upload polling and existing route fallbacks stable.
- Documentation/memory worker owns progress, memory, README, and Hub runbook updates only.

Goals:

- Introduce a run storage abstraction while preserving current JSON/file-mode behavior.
- Add a unified results export endpoint through `POST /api/v1/export/results`.
- Prepare session hardening so DeepSeek keys are not written to disk as plain secrets.
- Add job control primitives for local operation: cancel, concurrency limits, and retry-friendly failed/canceled states.
- Surface export/cancel controls in React once API contracts are available.

Validation target:

- `python scripts/check_frontend_rebuild_docs.py`
- `PYTHONPATH=src pytest tests/test_api_v1.py tests/test_visualization.py tests/test_run_registry.py`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- HTTP smoke for `POST /api/v1/export/results`, job status/control endpoints, and built React export/cancel flows.

## Later Phases

Polish copy, chart states, spacing, and accessibility after the Phase 4 storage/export/job-control surfaces settle.
