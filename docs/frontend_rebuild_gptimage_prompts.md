# SentiDemand Hub Frontend Rebuild Prompts

Generated after Playwright review on 2026-04-25.

## Current Frontend Map

Core routes:

- `/`: Home, upload entry, recent runs, crawler guidance.
- `/workspace`: Run list plus table workspace.
- `/workspace/{run_id}`: Selected run tables, searchable previews, open/download actions.
- `/dashboard/{run_id}`: Chart gallery with embedded previews, open/download actions, missing chart states.
- `/insights/{run_id}`: DeepSeek API key input, generate advice action, generated markdown advice panel.
- `/runs/{run_id}`: Legacy combined detail page with tables, logs, charts.
- `/chart/{chart_id}`: Standalone ECharts detail page.

Main functional objects:

- Upload files: CSV, XLSX, XLS, JSON.
- Run history: status, timestamp, source file, links to tables/charts/advice/legacy.
- Tables: processed data, sentiment distribution, model reports, top keywords, topics, demand intensity, demand correlation.
- Charts: sentiment donut, feature bars, lollipop, heatmap, TF-IDF scatter, topic rose, bubble matrix, radar, demand network, plus missing chart placeholders.
- Insights: DeepSeek key, save key, generate advice, output markdown/advice files.
- Legacy: combined artifact view for backwards compatibility.

## Rebuild Direction

The current UI is structurally complete but text-heavy. The redesign should keep all functions while reducing visible copy by about 70 percent. Prioritize calm hierarchy, clear routes, compact labels, fewer explanations, and a comfortable Anthropic-inspired visual language: warm ivory background, charcoal text, clay/rust accent, restrained borders, soft paper-like surfaces, generous spacing, and quiet data visualization.

Do not include long paragraphs. Prefer labels like `Upload`, `Runs`, `Tables`, `Charts`, `Advice`, `Open`, `Download`, `Ready`, `Missing`.

## Shared Style Prompt

Use this style block inside every image prompt:

```text
Visual style: Anthropic-inspired calm product interface, warm ivory and soft oatmeal background, charcoal typography, muted clay/rust accent, subtle sage status color, thin warm-gray borders, no glossy gradients, no neon, no purple-blue SaaS look, no heavy shadows. Spacious but operational, quiet enterprise analytics tool, comfortable and editorial but still a real dashboard. Minimal Chinese UI copy, labels only, no paragraphs. Rounded corners max 8px except small pills, refined typography, large whitespace, dense data areas where needed, no nested cards, no decorative blobs, no stock photos.
```

## Image 01 - Home / Upload Command Center

```text
Create a desktop web app screenshot, 1440x1000.

Subject: SentiDemand Hub home screen for review intelligence.

Layout:
- Top nav: brand "SentiDemand", tabs "Upload", "Runs", "Tables", "Charts", "Advice".
- First viewport is the usable app, not a marketing landing page.
- Left: compact upload panel with drag-and-drop zone, accepted file chips "CSV XLSX JSON", one primary button "Analyze".
- Right: recent runs list with 4 rows, each row has status dot, filename, date, and tiny action icons for tables, charts, advice.
- Bottom strip: three crawler script tiles, very compact, just names: "Bilibili", "JD", "Chrome".

Content rules:
- Very little text. No explanatory paragraphs.
- Use Chinese labels where needed: 上传, 运行, 表格, 图表, 建议.
- Show a calm empty/ready state, not a marketing hero.

Visual style: Anthropic-inspired calm product interface, warm ivory and soft oatmeal background, charcoal typography, muted clay/rust accent, subtle sage status color, thin warm-gray borders, no glossy gradients, no neon, no purple-blue SaaS look, no heavy shadows. Spacious but operational, quiet enterprise analytics tool, comfortable and editorial but still a real dashboard. Minimal Chinese UI copy, labels only, no paragraphs. Rounded corners max 8px except small pills, refined typography, large whitespace, dense data areas where needed, no nested cards, no decorative blobs, no stock photos.
```

## Image 02 - Workspace / Tables

```text
Create a desktop web app screenshot, 1440x1200.

Subject: SentiDemand Hub table workspace.

Layout:
- Persistent top nav, active tab "Tables".
- Left sidebar: run history list, 5 compact rows, selected run highlighted with a thin clay accent.
- Main content: title row with filename shortened, status "Ready", quick actions "Charts" and "Advice".
- Below: responsive grid of data artifact panels: processed_data.csv, sentiment_distribution.csv, top_keywords.csv, topics.csv, demand_intensity.csv, demand_correlation.csv.
- Each artifact panel contains: file name, tiny category tag, search field icon, 5-row table preview, icon buttons for open/download.

Content rules:
- No long summaries.
- Use very short labels: 搜索, 打开, 下载, Ready.
- Tables should feel readable and precise, not decorative.

Visual style: Anthropic-inspired calm product interface, warm ivory and soft oatmeal background, charcoal typography, muted clay/rust accent, subtle sage status color, thin warm-gray borders, no glossy gradients, no neon, no purple-blue SaaS look, no heavy shadows. Spacious but operational, quiet enterprise analytics tool, comfortable and editorial but still a real dashboard. Minimal Chinese UI copy, labels only, no paragraphs. Rounded corners max 8px except small pills, refined typography, large whitespace, dense data areas where needed, no nested cards, no decorative blobs, no stock photos.
```

## Image 03 - Dashboard / Chart Gallery

```text
Create a desktop analytics dashboard screenshot, 1440x1300.

Subject: SentiDemand Hub chart gallery for one analysis run.

Layout:
- Top nav active "Charts".
- Header row: compact filename, three metric chips: "9 charts", "9 tables", "6 logs".
- Main area: two-column chart grid.
- Chart cards: sentiment donut, keyword lollipop, feature comparison bars, topic rose, bubble matrix, radar, demand network.
- Missing chart cards appear as quiet outlined placeholders with a small "Missing" badge and no red warning block.
- Each chart card has minimal title, preview image area, status badge, open/download icon buttons.

Content rules:
- Keep titles short.
- No explanatory chart descriptions.
- Chart previews should be lighter and more refined than current dark ECharts theme.

Visual style: Anthropic-inspired calm product interface, warm ivory and soft oatmeal background, charcoal typography, muted clay/rust accent, subtle sage status color, thin warm-gray borders, no glossy gradients, no neon, no purple-blue SaaS look, no heavy shadows. Spacious but operational, quiet enterprise analytics tool, comfortable and editorial but still a real dashboard. Minimal Chinese UI copy, labels only, no paragraphs. Rounded corners max 8px except small pills, refined typography, large whitespace, dense data areas where needed, no nested cards, no decorative blobs, no stock photos.
```

## Image 04 - Insights / Advice

```text
Create a desktop web app screenshot, 1440x900.

Subject: SentiDemand Hub AI advice page.

Layout:
- Top nav active "Advice".
- Header: filename, status "Generated", buttons "Tables", "Charts".
- Main panel: a single compact API key row with password input and two actions: "Save" and "Generate".
- Advice output shown as structured insight blocks, not raw markdown text:
  1. Findings
  2. Actions
  3. Risks
- Each block has 3 concise bullet rows, with small severity or priority markers.
- Right rail: export actions for advice.md and advice.json.

Content rules:
- Avoid raw markdown symbols.
- No long paragraphs.
- Use concise Chinese labels: 发现, 行动, 风险, 导出.

Visual style: Anthropic-inspired calm product interface, warm ivory and soft oatmeal background, charcoal typography, muted clay/rust accent, subtle sage status color, thin warm-gray borders, no glossy gradients, no neon, no purple-blue SaaS look, no heavy shadows. Spacious but operational, quiet enterprise analytics tool, comfortable and editorial but still a real dashboard. Minimal Chinese UI copy, labels only, no paragraphs. Rounded corners max 8px except small pills, refined typography, large whitespace, dense data areas where needed, no nested cards, no decorative blobs, no stock photos.
```

## Image 05 - Standalone Chart Detail

```text
Create a standalone chart page screenshot, 1440x900.

Subject: sentiment donut chart detail page for SentiDemand Hub.

Layout:
- Minimal top header with back button, chart title "Sentiment", metadata chips: source, date, chart type.
- Main area is one large chart canvas, full-width, light theme.
- Donut chart centered, with three clean labels: Positive, Neutral, Negative.
- Right side has a narrow summary rail with only 3 metric numbers.
- Footer has subtle "Open data" and "Download" actions.

Content rules:
- No dark chart background.
- No long title or verbose metadata.
- Make the page feel inspectable and calm.

Visual style: Anthropic-inspired calm product interface, warm ivory and soft oatmeal background, charcoal typography, muted clay/rust accent, subtle sage status color, thin warm-gray borders, no glossy gradients, no neon, no purple-blue SaaS look, no heavy shadows. Spacious but operational, quiet enterprise analytics tool, comfortable and editorial but still a real dashboard. Minimal Chinese UI copy, labels only, no paragraphs. Rounded corners max 8px except small pills, refined typography, large whitespace, dense data areas where needed, no nested cards, no decorative blobs, no stock photos.
```

## Image 06 - Run Detail / Legacy Replacement

```text
Create a desktop web app screenshot, 1440x1000.

Subject: replacement for legacy combined run detail page.

Layout:
- Top nav active "Runs".
- Header: compact run identity, status, timestamp.
- Three vertical columns: Tables, Logs, Charts.
- Tables column: compact artifact list with open/download icons.
- Logs column: short timeline, 5 events max.
- Charts column: compact list with small thumbnails and status badges.
- Add a subtle notice chip "Legacy view" but avoid making it look outdated.

Content rules:
- The page is for quick audit, not deep reading.
- Do not show large paragraphs or raw logs.

Visual style: Anthropic-inspired calm product interface, warm ivory and soft oatmeal background, charcoal typography, muted clay/rust accent, subtle sage status color, thin warm-gray borders, no glossy gradients, no neon, no purple-blue SaaS look, no heavy shadows. Spacious but operational, quiet enterprise analytics tool, comfortable and editorial but still a real dashboard. Minimal Chinese UI copy, labels only, no paragraphs. Rounded corners max 8px except small pills, refined typography, large whitespace, dense data areas where needed, no nested cards, no decorative blobs, no stock photos.
```

## Image 07 - Upload Progress / Processing State

```text
Create a desktop web app screenshot, 1440x900.

Subject: upload and analysis progress state for SentiDemand Hub.

Layout:
- Same home shell, upload area active.
- A centered processing panel with filename, progress steps, and small live status.
- Steps: Upload, Clean, Sentiment, Topics, Demand, Charts.
- Completed steps use sage checkmarks, current step uses clay accent.
- Recent runs remain visible but muted behind the active panel.

Content rules:
- No verbose helper text.
- Use concise labels only.
- Include a clear cancel/close icon button.

Visual style: Anthropic-inspired calm product interface, warm ivory and soft oatmeal background, charcoal typography, muted clay/rust accent, subtle sage status color, thin warm-gray borders, no glossy gradients, no neon, no purple-blue SaaS look, no heavy shadows. Spacious but operational, quiet enterprise analytics tool, comfortable and editorial but still a real dashboard. Minimal Chinese UI copy, labels only, no paragraphs. Rounded corners max 8px except small pills, refined typography, large whitespace, dense data areas where needed, no nested cards, no decorative blobs, no stock photos.
```

## Image 08 - Mobile Layout

```text
Create a mobile web app screenshot, 390x844.

Subject: SentiDemand Hub mobile home and run navigation.

Layout:
- Compact top bar with brand and menu icon.
- Primary upload block at top with one "Analyze" button.
- Segmented control: Runs, Tables, Charts, Advice.
- Run list as clean rows, not big cards.
- Bottom sticky action bar with Upload, Runs, Charts.

Content rules:
- Minimal Chinese UI text.
- No paragraph copy.
- Avoid cramped buttons; text must fit.

Visual style: Anthropic-inspired calm product interface, warm ivory and soft oatmeal background, charcoal typography, muted clay/rust accent, subtle sage status color, thin warm-gray borders, no glossy gradients, no neon, no purple-blue SaaS look, no heavy shadows. Spacious but operational, quiet enterprise analytics tool, comfortable and editorial but still a real dashboard. Minimal Chinese UI copy, labels only, no paragraphs. Rounded corners max 8px except small pills, refined typography, large whitespace, dense data areas where needed, no nested cards, no decorative blobs, no stock photos.
```

## Negative Prompt

```text
Avoid: long explanatory Chinese paragraphs, marketing landing page hero, oversized slogans, nested cards, glossy blue SaaS dashboard, purple gradients, neon cyber charts, dark chart canvases, crowded badges, decorative blobs, stock photos, excessive shadows, tiny unreadable table text, raw markdown output, warning panels that dominate the page, huge pill buttons, cartoon illustrations.
```

