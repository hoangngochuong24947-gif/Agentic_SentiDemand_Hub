# Frontend Rebuild Memory

This file preserves the working memory for the SentiDemand Hub frontend rebuild so future agents can continue without rediscovering the plan.

## Current State

- Phase 0 is done: documentation, memory, progress tracking, and the doc guard script exist.
- Phase 1 is in progress: the React/Vite frontend exists under `frontend/` and is connected to the current Hub endpoints.
- The FastAPI Hub can serve the built React app at `/app` after `frontend/dist` is generated.

## Implemented This Pass

- Added React routes for Upload, Runs, Tables, Charts, Advice, and Run Detail.
- Added typed adapters for current endpoints: `/api/manifest`, `/api/runs/{run_id}`, `/upload`, `/api/session/deepseek-key`, `/api/runs/{run_id}/insights/generate`.
- Added hooks: `useRuns`, `useRun`, `useUploadRun`, `useRunTables`, `useRunCharts`, `useRunLogs`, `useDeepSeekSession`, `useGenerateInsight`, `useRebuildProgress`, `useFeatureFlag`.
- Added `/app` static serving in `src/comment_analyzer/visualization/gallery.py`.
- Verified `npm run typecheck`, `npm run build`, and `python scripts/check_frontend_rebuild_docs.py`.

## Next Step

- Run the existing backend tests, then start both services for browser verification:
  - Backend: `python -m comment_analyzer.visualization.gallery`
  - Frontend dev: `cd frontend && npm run dev`
  - Built frontend through backend: `http://127.0.0.1:8765/app`

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
