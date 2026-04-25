# Frontend Rebuild Progress

Last updated: 2026-04-25.

## Phase Status

| Phase | Name | Status | Notes |
| --- | --- | --- | --- |
| Phase 0 | Rebuild memory and guardrails | In progress | Creating required docs and a lightweight check script. |
| Phase 1 | Interface rebuild preparation | In progress | Translating the user-provided visual plan into route-level requirements. |
| Phase 2 | Frontend implementation | Not started | Frontend source is intentionally untouched in this pass. |
| Phase 3 | Browser verification | Not started | To be run after frontend implementation starts. |
| Phase 4 | Polish and hardening | Not started | Copy, spacing, chart states, accessibility. |

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
