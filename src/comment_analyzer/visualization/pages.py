"""Rendering helpers for the Hub homepage, workspace, and detail pages."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CrawlerGuideCard:
    """Static guidance card for a crawler script."""

    title: str
    subtitle: str
    purpose: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    steps: tuple[str, ...]


DEFAULT_CRAWLER_GUIDANCE: tuple[CrawlerGuideCard, ...] = (
    CrawlerGuideCard(
        title="Bilibili 评论抓取",
        subtitle="exp1_bilibili_requests.py",
        purpose="适合从 B 站视频评论区拉取首批评论样本，先建立一份可上传分析的基础评论表。",
        inputs=("视频链接或 ID", "分页范围", "抓取数量上限"),
        outputs=("原始评论 CSV", "请求日志", "异常样本"),
        steps=(
            "先用少量分页测试字段是否齐全。",
            "确认导出的文件里包含评论文本列。",
            "导出后回到首页上传评论文件继续分析。",
        ),
    ),
    CrawlerGuideCard(
        title="京东评论连接采集",
        subtitle="exp2_jd_reviews_connect.py",
        purpose="适合抓取京东商品评论，并为后续清洗、停用词过滤和需求分析准备输入数据。",
        inputs=("商品链接或 SKU", "时间窗口", "采集批次"),
        outputs=("评论数据表", "连接状态日志", "失败重试清单"),
        steps=(
            "先确认商品链接可正常访问。",
            "抓取后检查是否导出了评论、时间、评分等核心字段。",
            "将导出的表格直接上传到 Hub 工作台。",
        ),
    ),
    CrawlerGuideCard(
        title="Chrome 调试启动",
        subtitle="start_chrome.ps1",
        purpose="适合在需要登录态或页面调试时先准备浏览器环境，再配合其它采集脚本使用。",
        inputs=("本机 Chrome", "调试端口", "登录态准备"),
        outputs=("可复用浏览器会话", "调试环境", "页面排查入口"),
        steps=(
            "先启动脚本，确认 Chrome 进入调试模式。",
            "完成登录或页面检查后，再运行对应采集脚本。",
            "将采集产出的评论文件回传到 Hub 上传分析。",
        ),
    ),
)


@lru_cache(maxsize=8)
def _read_asset(filename: str) -> str:
    asset_path = Path(__file__).with_name("templates") / filename
    return asset_path.read_text(encoding="utf-8")


def _shell(page_title: str, content: str, *, extra_head: str = "", extra_script: str = "") -> str:
    html = _read_asset("page_shell.html")
    css = _read_asset("hub.css")
    return (
        html.replace("{{PAGE_TITLE}}", escape(page_title))
        .replace("{{STYLES}}", css)
        .replace("{{EXTRA_HEAD}}", extra_head)
        .replace("{{CONTENT}}", content)
        .replace("{{EXTRA_SCRIPT}}", extra_script)
    )


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _artifact_links(*, open_url: str | None = None, download_url: str | None = None) -> str:
    links: list[str] = []
    if open_url:
        links.append(f'<a class="ghost-link" href="{escape(open_url)}" target="_blank" rel="noopener noreferrer">打开</a>')
    if download_url:
        links.append(f'<a class="ghost-link ghost-link-strong" href="{escape(download_url)}">下载</a>')
    if not links:
        return ""
    return f'<div class="artifact-links">{"".join(links)}</div>'


def _render_run_card(run: Mapping[str, Any], *, highlight: bool = False) -> str:
    title = escape(_text(run.get("title") or run.get("name") or run.get("source_name") or "未命名运行"))
    status = escape(_text(run.get("status") or "unknown"))
    created_at = escape(_text(run.get("created_at") or run.get("timestamp") or ""))
    summary = escape(_text(run.get("summary") or run.get("note") or run.get("description") or "暂无摘要"))
    href = escape(_text(run.get("href") or run.get("detail_url") or "#"))
    source = escape(_text(run.get("source_name") or run.get("source") or "source"))
    badge_class = "status-pill status-success" if status.lower() in {"done", "success", "completed", "ok"} else "status-pill status-neutral"
    featured = " run-card-featured" if highlight else ""
    return f"""
        <article class="run-card{featured}">
            <div class="run-card-topline">
                <span class="{badge_class}">{status}</span>
                <span class="run-card-time">{created_at}</span>
            </div>
            <h3>{title}</h3>
            <p class="run-card-source">{source}</p>
            <p class="run-card-summary">{summary}</p>
            <div class="run-card-actions">
                <a class="ghost-link" href="{href}">查看详情</a>
                <a class="ghost-link ghost-link-strong" href="{href}#quick-actions">快捷操作</a>
            </div>
        </article>
    """


def _render_metric_card(label: str, value: Any, note: str) -> str:
    return f"""
        <article class="metric-card">
            <span class="metric-label">{escape(label)}</span>
            <strong class="metric-value">{escape(_text(value, "0"))}</strong>
            <span class="metric-note">{escape(note)}</span>
        </article>
    """


def _render_history_summary(runs: Sequence[Mapping[str, Any]]) -> str:
    if not runs:
        return """
            <div class="empty-state">
                <h3>还没有历史运行</h3>
                <p>先上传第一份评论文件，或者先按下方的采集说明准备数据。</p>
            </div>
        """

    cards = "".join(_render_run_card(run, highlight=index == 0) for index, run in enumerate(runs[:3]))
    return f'<div class="history-card-grid">{cards}</div>'


def _render_crawler_guidance(cards: Sequence[CrawlerGuideCard]) -> str:
    rendered = []
    for index, card in enumerate(cards, start=1):
        rendered.append(
            f"""
            <article class="crawler-card">
                <div class="crawler-card-kicker">Crawler {index:02d}</div>
                <h3>{escape(card.title)}</h3>
                <p class="crawler-card-subtitle">{escape(card.subtitle)}</p>
                <p class="crawler-card-purpose">{escape(card.purpose)}</p>
                <div class="crawler-card-block">
                    <span>输入</span>
                    <p>{escape(", ".join(card.inputs))}</p>
                </div>
                <div class="crawler-card-block">
                    <span>输出</span>
                    <p>{escape(", ".join(card.outputs))}</p>
                </div>
                <ol class="crawler-card-steps">
                    {"".join(f"<li>{escape(step)}</li>" for step in card.steps)}
                </ol>
            </article>
            """
        )
    return "".join(rendered)


def _homepage_script() -> str:
    return """
    <script>
    (() => {
      const trigger = document.getElementById('upload-trigger');
      const input = document.getElementById('upload-input');
      const status = document.getElementById('upload-status');
      if (!trigger || !input || !status) return;

      trigger.addEventListener('click', () => input.click());

      input.addEventListener('change', async () => {
        if (!input.files || !input.files.length) return;
        const file = input.files[0];
        status.textContent = `正在上传并分析：${file.name}`;
        const form = new FormData();
        form.append('file', file);

        try {
          const response = await fetch('/upload', { method: 'POST', body: form });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.detail || '上传失败');
          }
          status.textContent = payload.user_message || '上传成功，正在跳转详情页...';
          if (payload.run_id) {
            window.setTimeout(() => {
              window.location.href = `/runs/${payload.run_id}`;
            }, 500);
          } else {
            window.setTimeout(() => {
              window.location.href = '/workspace';
            }, 500);
          }
        } catch (error) {
          status.textContent = error instanceof Error ? error.message : '上传失败，请检查文件后重试';
        } finally {
          input.value = '';
        }
      });
    })();
    </script>
    """


def render_homepage_page(
    runs: Sequence[Mapping[str, Any]] | None = None,
    *,
    crawler_guidance: Sequence[CrawlerGuideCard] | None = None,
    page_title: str = "SentiDemand Hub - Home",
) -> str:
    """Render the showcase homepage."""

    recent_runs = list(runs or [])
    guidance = tuple(crawler_guidance or DEFAULT_CRAWLER_GUIDANCE)
    marquee_items = (
        "Upload raw comments",
        "Inspect history",
        "Open derived tables",
        "Review logs",
        "Open charts",
        "Follow crawler guidance",
    )
    marquee = "".join(f"<span>{escape(item)}</span>" for item in marquee_items * 2)
    content = f"""
        <section class="hero-section">
            <div class="hero-copy">
                <span class="hero-eyebrow">Agentic SentiDemand Hub</span>
                <h1>把评论分析做成一个可以回看的工作台，而不是一次性的上传弹窗。</h1>
                <p>首页负责上传和导引，工作台负责管理历史文件，详情页负责拆开看派生表格、日志和图表。每一次上传都会形成一条可追踪的分析运行记录。</p>
                <div class="hero-actions">
                    <a class="primary-link" href="#upload">开始上传</a>
                    <a class="ghost-link" href="/workspace">查看工作台</a>
                </div>
            </div>
            <div class="hero-marquee" aria-hidden="true">
                <div class="hero-marquee-track">{marquee}</div>
            </div>
        </section>
        <section class="surface-grid" id="upload">
            <article class="surface-card accent-upload">
                <span class="surface-card-kicker">Upload</span>
                <h2>上传评论文件并直接进入分析详情</h2>
                <p>支持 CSV、XLSX、XLS、JSON。上传成功后会自动生成派生表格、日志和图表，并跳转到这次运行的详情页。</p>
                <div class="upload-controls">
                    <button type="button" class="primary-link" id="upload-trigger">选择评论文件</button>
                    <a class="ghost-link" href="/workspace">打开工作台</a>
                    <input id="upload-input" type="file" accept=".csv,.xlsx,.xls,.json" hidden />
                </div>
                <p class="upload-status" id="upload-status">建议先上传一份字段简单、行数适中的评论样本，确认列名后再跑大文件。</p>
                <ul class="inline-list upload-guide">
                    <li>文件里至少要有一列是真正的评论文本，常见列名如“评论”“内容”“comment”“review”。</li>
                    <li>不要上传截图、PDF 或只有链接的空表。</li>
                    <li>如果 CSV 打开后是乱码，请另存为 UTF-8 编码后再上传。</li>
                    <li>上传后，历史文件会出现在工作台里，可以反复回看。</li>
                </ul>
            </article>
            <article class="surface-card accent-help">
                <span class="surface-card-kicker">How To</span>
                <h2>常见失败原因和正确上传方式</h2>
                <p>最常见的问题不是“系统坏了”，而是文件本身不满足分析条件。这里先把判断标准说清楚，减少反复试错。</p>
                <ul class="inline-list">
                    <li>文件为空，或只有表头没有评论内容。</li>
                    <li>表里没有可识别的评论文本列。</li>
                    <li>文件格式不支持，或编码损坏导致读取失败。</li>
                    <li>上传后如果提示失败，先回看错误信息，再对照这里重新整理文件。</li>
                </ul>
            </article>
            <article class="surface-card accent-history">
                <span class="surface-card-kicker">History</span>
                <h2>历史运行会保留下来</h2>
                <p>你可以回到之前上传过的文件，继续查看它产生的派生表格、日志和图表，而不是每次都重新找文件。</p>
                <a class="ghost-link" href="/workspace">进入历史工作台</a>
            </article>
            <article class="surface-card accent-crawler">
                <span class="surface-card-kicker">Crawler</span>
                <h2>采集入口先做成说明型卡片</h2>
                <p>这期页面不直接执行采集脚本，而是把 B 站、京东和 Chrome 调试入口的作用、前置条件和产出讲清楚，方便你以后继续扩展成真正的交互入口。</p>
                <a class="ghost-link" href="#crawler-guidance">查看采集说明</a>
            </article>
        </section>
        <section class="history-section" id="workspace">
            <div class="section-heading">
                <div>
                    <span class="section-kicker">History</span>
                    <h2>最近的分析运行</h2>
                </div>
                <a class="ghost-link" href="/workspace">查看全部历史</a>
            </div>
            {_render_history_summary(recent_runs)}
        </section>
        <section class="crawler-guidance-section" id="crawler-guidance">
            <div class="section-heading">
                <div>
                    <span class="section-kicker">Crawler guidance</span>
                    <h2>采集脚本说明卡片</h2>
                </div>
                <span class="section-caption">说明型入口，不直接在网页内执行脚本</span>
            </div>
            <div class="crawler-grid">
                {_render_crawler_guidance(guidance)}
            </div>
        </section>
    """
    extra_head = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;700;800&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">'
    )
    return _shell(page_title, content, extra_head=extra_head, extra_script=_homepage_script())


def render_workspace_page(
    runs: Sequence[Mapping[str, Any]] | None = None,
    *,
    page_title: str = "SentiDemand Hub - Workspace",
) -> str:
    """Render the historical workspace view."""

    run_items = list(runs or [])
    cards = "".join(_render_run_card(run, highlight=index == 0) for index, run in enumerate(run_items))
    metrics = "".join(
        (
            _render_metric_card("运行总数", len(run_items), "历史上传与分析记录"),
            _render_metric_card(
                "最近成功",
                next(
                    (run.get("created_at") for run in run_items if _text(run.get("status")).lower() in {"done", "success", "completed", "ok"}),
                    "暂无",
                ),
                "最近一次成功分析时间",
            ),
            _render_metric_card(
                "待处理",
                sum(1 for run in run_items if _text(run.get("status")).lower() not in {"done", "success", "completed", "ok"}),
                "建议优先回看失败或异常记录",
            ),
        )
    )
    content = f"""
        <section class="workspace-hero">
            <div>
                <span class="hero-eyebrow">Workspace</span>
                <h1>历史文件与分析运行工作台</h1>
                <p>这里按时间倒序保存你的上传记录。点开任意一条运行，都能看到对应的派生表格、日志和图表，不需要重新翻找文件。</p>
            </div>
            <div class="metric-grid">{metrics}</div>
        </section>
        <section class="workspace-toolbar">
            <a class="primary-link" href="/#upload">继续上传新文件</a>
            <a class="ghost-link" href="#runs">查看全部运行</a>
            <a class="ghost-link" href="/#crawler-guidance">查看采集说明</a>
        </section>
        <section class="workspace-runs" id="runs">
            <div class="section-heading">
                <div>
                    <span class="section-kicker">Historical runs</span>
                    <h2>运行列表</h2>
                </div>
                <span class="section-caption">按时间倒序展示</span>
            </div>
            <div class="history-card-grid">{cards}</div>
        </section>
    """
    extra_head = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;700;800&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">'
    )
    return _shell(page_title, content, extra_head=extra_head)


def _render_table_panel(tables: Sequence[Mapping[str, Any]]) -> str:
    sections = []
    for table in tables:
        columns = [escape(_text(value)) for value in table.get("columns", [])]
        rows = table.get("rows", [])
        table_rows = []
        for row in rows[:4]:
            if isinstance(row, Mapping):
                table_rows.append(
                    "<tr>"
                    + "".join(f"<td>{escape(_text(row.get(column), ''))}</td>" for column in table.get("columns", []))
                    + "</tr>"
                )
            else:
                table_rows.append(f"<tr><td colspan='{max(1, len(columns))}'>{escape(_text(row))}</td></tr>")
        sections.append(
            f"""
            <article class="preview-block">
                <div class="preview-block-head">
                    <h4>{escape(_text(table.get('title') or '派生表格'))}</h4>
                    <span>{escape(_text(table.get('summary') or '结构预览'))}</span>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead><tr>{"".join(f"<th>{column}</th>" for column in columns)}</tr></thead>
                        <tbody>{"".join(table_rows)}</tbody>
                    </table>
                </div>
                {_artifact_links(open_url=_text(table.get('open_url')), download_url=_text(table.get('download_url')))}
            </article>
            """
        )
    return "".join(sections) or "<p class='panel-placeholder'>暂无派生表格预览</p>"


def _render_logs_panel(logs: Sequence[Any]) -> str:
    if not logs:
        return "<p class='panel-placeholder'>暂无日志摘要</p>"

    items = []
    for entry in list(logs)[:6]:
        if isinstance(entry, Mapping):
            title = escape(_text(entry.get("title") or entry.get("category") or "日志"))
            message = escape(_text(entry.get("message") or entry.get("summary") or entry.get("content") or ""))
            links = _artifact_links(open_url=_text(entry.get("open_url")), download_url=_text(entry.get("download_url")))
            items.append(f"<li><strong>{title}</strong><span>{message}</span>{links}</li>")
        else:
            items.append(f"<li>{escape(_text(entry))}</li>")
    return f"<ul class='log-list'>{''.join(items)}</ul>"


def _render_chart_panel(charts: Sequence[Mapping[str, Any]]) -> str:
    if not charts:
        return "<p class='panel-placeholder'>暂无图表预览</p>"
    cards = []
    for chart in charts[:6]:
        cards.append(
            f"""
            <article class="chart-preview">
                <span class="chart-preview-kicker">{escape(_text(chart.get('type') or 'chart'))}</span>
                <h4>{escape(_text(chart.get('title') or '图表'))}</h4>
                <p>{escape(_text(chart.get('summary') or '图表已生成，可直接打开查看。'))}</p>
                {_artifact_links(open_url=_text(chart.get('open_url')), download_url=_text(chart.get('download_url')))}
            </article>
            """
        )
    return "".join(cards)


def _render_quick_actions(actions: Sequence[str]) -> str:
    return "".join(f'<button type="button" class="quick-action">{escape(action)}</button>' for action in actions)


def render_detail_page(
    run: Mapping[str, Any],
    *,
    derived_tables: Sequence[Mapping[str, Any]] | None = None,
    logs: Sequence[Any] | None = None,
    charts: Sequence[Mapping[str, Any]] | None = None,
    page_title: str = "SentiDemand Hub - Detail",
) -> str:
    """Render the detail page with three independent panels."""

    title = _text(run.get("title") or run.get("name") or run.get("source_name") or "Run detail")
    status = _text(run.get("status") or "unknown")
    created_at = _text(run.get("created_at") or run.get("timestamp") or "")
    source_name = _text(run.get("source_name") or run.get("source") or "")
    summary = _text(run.get("summary") or run.get("description") or "这一页把本次分析拆成三个面板，方便逐块检查。")
    derived_tables = list(derived_tables or [])
    logs = list(logs or [])
    charts = list(charts or [])
    content = f"""
        <section class="detail-hero">
            <div>
                <span class="hero-eyebrow">Detail</span>
                <h1>{escape(title)}</h1>
                <p>{escape(source_name)} · {escape(created_at)} · {escape(status)}</p>
                <p class="secondary-note">{escape(summary)}</p>
            </div>
            <div class="detail-actions" id="quick-actions">
                <a class="primary-link" href="#tables">表格面板</a>
                <a class="ghost-link" href="#logs">日志面板</a>
                <a class="ghost-link" href="#charts">图表面板</a>
            </div>
        </section>
        <section class="detail-grid">
            <article class="detail-panel" id="tables">
                <div class="panel-head">
                    <div>
                        <span class="section-kicker">Panel 01</span>
                        <h2>派生表格</h2>
                    </div>
                    <div class="panel-mode">
                        <span class="mode-pill mode-pill-active">预览</span>
                        <span class="mode-pill">快捷入口</span>
                    </div>
                </div>
                <div class="panel-layout">
                    <div class="panel-preview">
                        {_render_table_panel(derived_tables)}
                    </div>
                    <div class="panel-actions">
                        {_render_quick_actions(("查看清洗结果", "复制字段结构", "打开表格导出"))}
                    </div>
                </div>
            </article>
            <article class="detail-panel" id="logs">
                <div class="panel-head">
                    <div>
                        <span class="section-kicker">Panel 02</span>
                        <h2>日志</h2>
                    </div>
                    <div class="panel-mode">
                        <span class="mode-pill mode-pill-active">预览</span>
                        <span class="mode-pill">快捷入口</span>
                    </div>
                </div>
                <div class="panel-layout">
                    <div class="panel-preview">
                        {_render_logs_panel(logs)}
                    </div>
                    <div class="panel-actions">
                        {_render_quick_actions(("复制日志", "筛选告警", "打开完整日志"))}
                    </div>
                </div>
            </article>
            <article class="detail-panel" id="charts">
                <div class="panel-head">
                    <div>
                        <span class="section-kicker">Panel 03</span>
                        <h2>图表</h2>
                    </div>
                    <div class="panel-mode">
                        <span class="mode-pill mode-pill-active">预览</span>
                        <span class="mode-pill">快捷入口</span>
                    </div>
                </div>
                <div class="panel-layout">
                    <div class="panel-preview chart-grid">
                        {_render_chart_panel(charts)}
                    </div>
                    <div class="panel-actions">
                        {_render_quick_actions(("刷新图表", "导出图片", "打开图表页面"))}
                    </div>
                </div>
            </article>
        </section>
    """
    extra_head = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;700;800&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">'
    )
    return _shell(page_title, content, extra_head=extra_head)
