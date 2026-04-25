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

Status: in progress.

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

Status: in progress.

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

## Later Phases

Phase 2: implement frontend route and component changes.

Phase 3: verify with browser screenshots across desktop and mobile.

Phase 4: polish copy, chart states, spacing, and accessibility.
