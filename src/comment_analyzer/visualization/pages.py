"""Rendering helpers for SentiDemand Hub pages."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CrawlerGuideCard:
    """Static guidance card for crawler scripts."""

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
        purpose="用于批量抓取 B 站视频评论，先形成可上传的原始评论表。",
        inputs=("视频链接或 BV 号", "分页范围", "抓取数量上限"),
        outputs=("原始评论 CSV", "请求日志", "异常样本记录"),
        steps=(
            "先用小样本测试列名是否齐全。",
            "确认导出的文件里存在评论正文列。",
            "把导出的 CSV 直接上传到 Hub 进行分析。",
        ),
    ),
    CrawlerGuideCard(
        title="京东评论抓取",
        subtitle="exp2_jd_reviews_connect.py",
        purpose="用于抓取京东商品评论，生成标准化评论数据供后续分析。",
        inputs=("商品链接或 SKU", "时间窗口", "批次参数"),
        outputs=("评论明细表", "请求状态日志", "失败重试清单"),
        steps=(
            "先确认商品链接可正常访问。",
            "检查评论文本、评分、时间列是否完整。",
            "导出的表格可直接上传到 Hub。",
        ),
    ),
    CrawlerGuideCard(
        title="Chrome 调试会话",
        subtitle="start_chrome.ps1",
        purpose="在需要登录态或页面调试时先准备浏览器环境，再配合采集脚本。",
        inputs=("本地 Chrome", "远程调试端口", "登录态"),
        outputs=("复用浏览器会话", "调试入口", "页面排查能力"),
        steps=(
            "先运行脚本并确认 Chrome 进入调试模式。",
            "完成登录后再执行采集脚本。",
            "将采集结果上传到 Hub 继续分析。",
        ),
    ),
)


@lru_cache(maxsize=8)
def _read_asset(filename: str) -> str:
    asset_path = Path(__file__).with_name("templates") / filename
    return asset_path.read_text(encoding="utf-8")


def _shell(
    page_title: str,
    content: str,
    *,
    active_nav: str,
    extra_head: str = "",
    extra_script: str = "",
) -> str:
    html = _read_asset("page_shell.html")
    css = _read_asset("hub.css")
    nav_active = {
        "home": "",
        "workspace": "",
        "legacy": "",
    }
    if active_nav in nav_active:
        nav_active[active_nav] = "is-active"
    return (
        html.replace("{{PAGE_TITLE}}", escape(page_title))
        .replace("{{STYLES}}", css)
        .replace("{{NAV_HOME_CLASS}}", nav_active["home"])
        .replace("{{NAV_WORKSPACE_CLASS}}", nav_active["workspace"])
        .replace("{{NAV_LEGACY_CLASS}}", nav_active["legacy"])
        .replace("{{EXTRA_HEAD}}", extra_head)
        .replace("{{CONTENT}}", content)
        .replace("{{EXTRA_SCRIPT}}", extra_script)
    )


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _json_attr(value: Any) -> str:
    return escape(json.dumps(value, ensure_ascii=False))


def _run_id_from_payload(run: Mapping[str, Any]) -> str:
    run_id = _text(run.get("run_id"))
    if run_id:
        return run_id
    href = _text(run.get("href"))
    match = re.search(r"/runs/([^/?#]+)", href)
    return match.group(1) if match else ""


def _status_class(status: str) -> str:
    lowered = status.lower()
    if lowered in {"completed", "success", "ok", "done"}:
        return "status-pill status-success"
    if lowered in {"failed", "error"}:
        return "status-pill status-failed"
    return "status-pill status-neutral"


def _artifact_links(*, open_url: str | None = None, download_url: str | None = None) -> str:
    links: list[str] = []
    if open_url:
        links.append(
            f'<a class="ghost-link" href="{escape(open_url)}" target="_blank" rel="noopener noreferrer">打开</a>'
        )
    if download_url:
        links.append(f'<a class="ghost-link ghost-link-strong" href="{escape(download_url)}">下载</a>')
    if not links:
        return ""
    return f'<div class="artifact-links">{"".join(links)}</div>'


def _render_history_cards(runs: Sequence[Mapping[str, Any]]) -> str:
    if not runs:
        return """
            <div class="empty-state">
                <h3>还没有运行记录</h3>
                <p>先上传一份评论文件，运行完成后会在这里显示历史记录。</p>
            </div>
        """

    cards: list[str] = []
    for run in runs:
        run_id = _run_id_from_payload(run)
        status = _text(run.get("status"), "unknown")
        cards.append(
            f"""
            <article class="run-card">
                <div class="run-card-topline">
                    <span class="{_status_class(status)}">{escape(status)}</span>
                    <span class="run-card-time">{escape(_text(run.get("created_at")))}</span>
                </div>
                <h3>{escape(_text(run.get("title") or run.get("source_name") or run_id or "未命名运行"))}</h3>
                <p class="run-card-source">{escape(_text(run.get("source_name"), "source"))}</p>
                <p class="run-card-summary">{escape(_text(run.get("summary"), "暂无摘要"))}</p>
                <div class="run-card-actions">
                    <a class="ghost-link" href="/workspace/{escape(run_id)}">表格</a>
                    <a class="ghost-link" href="/dashboard/{escape(run_id)}">仪表盘</a>
                    <a class="ghost-link" href="/insights/{escape(run_id)}">建议</a>
                    <a class="ghost-link ghost-link-strong" href="/runs/{escape(run_id)}">旧版</a>
                </div>
            </article>
            """
        )
    return "".join(cards)


def _render_crawler_guidance(cards: Sequence[CrawlerGuideCard]) -> str:
    blocks: list[str] = []
    for index, card in enumerate(cards, start=1):
        blocks.append(
            f"""
            <article class="crawler-card">
                <span class="crawler-card-kicker">Crawler {index:02d}</span>
                <h3>{escape(card.title)}</h3>
                <p class="crawler-card-subtitle">{escape(card.subtitle)}</p>
                <p class="crawler-card-purpose">{escape(card.purpose)}</p>
                <div class="crawler-card-block"><span>输入</span><p>{escape(", ".join(card.inputs))}</p></div>
                <div class="crawler-card-block"><span>输出</span><p>{escape(", ".join(card.outputs))}</p></div>
                <ol class="crawler-card-steps">
                    {"".join(f"<li>{escape(step)}</li>" for step in card.steps)}
                </ol>
            </article>
            """
        )
    return "".join(blocks)


def _homepage_script() -> str:
    return """
    <script>
    (() => {
      const uploadBtn = document.getElementById("upload-trigger");
      const uploadInput = document.getElementById("upload-input");
      const statusNode = document.getElementById("upload-status");
      if (!uploadBtn || !uploadInput || !statusNode) return;

      uploadBtn.addEventListener("click", () => uploadInput.click());

      uploadInput.addEventListener("change", async () => {
        if (!uploadInput.files || !uploadInput.files.length) return;
        const file = uploadInput.files[0];
        const form = new FormData();
        form.append("file", file);
        uploadBtn.disabled = true;
        uploadBtn.textContent = "上传中...";
        statusNode.textContent = `正在上传并分析: ${file.name}`;
        try {
          const resp = await fetch("/upload", { method: "POST", body: form });
          const payload = await resp.json();
          if (!resp.ok) throw new Error(payload.detail || "上传失败");
          statusNode.textContent = payload.user_message || "上传成功";
          if (payload.run_id) {
            window.setTimeout(() => {
              window.location.href = `/workspace/${payload.run_id}`;
            }, 450);
          }
        } catch (err) {
          statusNode.textContent = err instanceof Error ? err.message : "上传失败，请重试";
        } finally {
          uploadInput.value = "";
          uploadBtn.disabled = false;
          uploadBtn.textContent = "上传并分析";
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
    """Render the redesigned homepage."""

    run_list = list(runs or [])
    guide_list = tuple(crawler_guidance or DEFAULT_CRAWLER_GUIDANCE)
    hero_tags = (
        "Upload 评论数据",
        "结构化表格输出",
        "图表仪表盘拆分",
        "DeepSeek 结论建议",
        "旧版并行入口",
    )
    content = f"""
    <section class="hero-section">
      <div class="hero-copy">
        <span class="hero-eyebrow">SentiDemand Hub v2</span>
        <h1>上传评论后，表格、图表、建议分页面查看</h1>
        <p>这版工作流分成四个独立页面：主页上传、工作台表格、仪表盘图表、建议页输出。页面之间支持一键切换，避免信息堆在同一页。</p>
        <div class="hero-actions">
          <button class="primary-link" id="upload-trigger" type="button">上传并分析</button>
          <a class="ghost-link" href="/workspace">进入工作台</a>
          <a class="ghost-link ghost-link-strong" href="/legacy">查看旧版</a>
        </div>
        <input id="upload-input" type="file" hidden accept=".csv,.xlsx,.xls,.json" />
        <p class="upload-status" id="upload-status">支持 CSV / XLSX / XLS / JSON</p>
      </div>
      <div class="hero-tag-wall">
        {"".join(f"<span>{escape(item)}</span>" for item in hero_tags)}
      </div>
    </section>

    <section class="surface-grid">
      <article class="surface-card accent-upload">
        <span class="surface-card-kicker">Step 1</span>
        <h2>上传数据并触发分析</h2>
        <p>上传后系统会自动运行清洗、情感、主题和需求分析，并生成可追溯的 run 记录。</p>
      </article>
      <article class="surface-card accent-help">
        <span class="surface-card-kicker">Step 2</span>
        <h2>工作台查看表格</h2>
        <p>表格输出单独在工作台展示，支持下载和结构化预览，不再和图表混排。</p>
      </article>
      <article class="surface-card accent-history">
        <span class="surface-card-kicker">Step 3</span>
        <h2>仪表盘查看可视化</h2>
        <p>图表集中在仪表盘页面，支持嵌入预览、独立打开和下载，缺失图表会明确标记原因。</p>
      </article>
      <article class="surface-card accent-crawler">
        <span class="surface-card-kicker">Step 4</span>
        <h2>建议页手动生成结论</h2>
        <p>在建议页手动触发 DeepSeek，总结关键指标并输出行动建议，结果落盘到 insights 目录。</p>
      </article>
    </section>

    <section class="history-section">
      <div class="section-heading">
        <div>
          <span class="section-kicker">Recent Runs</span>
          <h2>最近运行</h2>
        </div>
        <a class="ghost-link" href="/workspace">查看全部</a>
      </div>
      <div class="history-card-grid">{_render_history_cards(run_list[:3])}</div>
    </section>

    <section class="crawler-guidance-section" id="crawler-guidance">
      <div class="section-heading">
        <div>
          <span class="section-kicker">Crawler Guidance</span>
          <h2>采集脚本说明</h2>
        </div>
      </div>
      <div class="crawler-grid">{_render_crawler_guidance(guide_list)}</div>
    </section>
    """

    extra_head = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&'
        'family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">'
    )
    return _shell(
        page_title,
        content,
        active_nav="home",
        extra_head=extra_head,
        extra_script=_homepage_script(),
    )


def _render_table_artifacts(tables: Sequence[Mapping[str, Any]]) -> str:
    if not tables:
        return """
        <div class="empty-state">
          <h3>该运行暂无表格输出</h3>
          <p>请先检查上传文件或查看日志面板定位问题。</p>
        </div>
        """

    cards: list[str] = []
    for idx, table in enumerate(tables):
        preview = table.get("preview") if isinstance(table.get("preview"), Mapping) else {}
        columns = preview.get("columns", [])
        rows = preview.get("rows", [])
        grid_id = f"grid-{idx}"
        cards.append(
            f"""
            <article class="artifact-card">
              <div class="artifact-card-head">
                <h3>{escape(_text(table.get("title") or table.get("name"), "派生表格"))}</h3>
                <span class="status-chip status-chip-ready">{escape(_text(table.get("status"), "ready"))}</span>
              </div>
              <p>{escape(_text(table.get("summary"), "表格预览"))}</p>
              <div class="table-grid" id="{grid_id}" data-columns="{_json_attr(columns)}" data-rows="{_json_attr(rows)}"></div>
              {_artifact_links(open_url=_text(table.get("open_url")), download_url=_text(table.get("download_url")))}
            </article>
            """
        )
    return "".join(cards)


def _workspace_script() -> str:
    return """
    <script src="https://cdn.jsdelivr.net/npm/gridjs/dist/gridjs.umd.js"></script>
    <script>
    (() => {
      const tableNodes = document.querySelectorAll(".table-grid");
      tableNodes.forEach((node) => {
        if (!window.gridjs) return;
        const columns = JSON.parse(node.dataset.columns || "[]");
        const rows = JSON.parse(node.dataset.rows || "[]");
        if (!columns.length) return;
        const data = rows.map((row) => columns.map((col) => String((row || {})[col] ?? "")));
        new window.gridjs.Grid({
          columns,
          data,
          search: true,
          sort: true,
          pagination: { limit: 5 },
          className: {
            table: "gridjs-table",
          }
        }).render(node);
      });
    })();
    </script>
    """


def render_workspace_page(
    runs: Sequence[Mapping[str, Any]] | None = None,
    *,
    selected_run: Mapping[str, Any] | None = None,
    tables: Sequence[Mapping[str, Any]] | None = None,
    page_title: str = "SentiDemand Hub - Workspace",
) -> str:
    """Render workspace page with run list and table-only content."""

    run_list = list(runs or [])
    selected = selected_run or {}
    selected_run_id = _run_id_from_payload(selected) if selected else ""
    table_list = list(tables or [])

    selected_title = _text(selected.get("title") or selected.get("source_name") or selected_run_id, "未选择运行")
    selected_summary = _text(
        selected.get("summary"),
        "从左侧运行列表选择一个 run 查看表格输出。",
    )

    content = f"""
    <section class="workspace-hero">
      <div>
        <span class="hero-eyebrow">Workspace / Tables</span>
        <h1>表格工作台</h1>
        <p>表格和日志信息在工作台管理，图表与建议在其他页面单独查看。</p>
      </div>
      <div class="workspace-hero-actions">
        <a class="primary-link" href="/">回到主页</a>
        <a class="ghost-link" href="/legacy">旧版入口</a>
      </div>
    </section>

    <section class="dual-panel-layout">
      <aside class="left-panel">
        <div class="section-heading compact">
          <h2>运行列表</h2>
        </div>
        <div class="run-list">{_render_history_cards(run_list)}</div>
      </aside>
      <section class="right-panel">
        <div class="section-heading compact">
          <div>
            <h2>{escape(selected_title)}</h2>
            <p class="section-caption">{escape(selected_summary)}</p>
          </div>
          <div class="toolbar-links">
            <a class="ghost-link" href="/dashboard/{escape(selected_run_id)}">图表页</a>
            <a class="ghost-link" href="/insights/{escape(selected_run_id)}">建议页</a>
            <a class="ghost-link ghost-link-strong" href="/runs/{escape(selected_run_id)}">旧版详情</a>
          </div>
        </div>
        <div class="artifact-grid">{_render_table_artifacts(table_list)}</div>
      </section>
    </section>
    """

    extra_head = (
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridjs/dist/theme/mermaid.min.css">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&'
        'family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">'
    )
    return _shell(
        page_title,
        content,
        active_nav="workspace",
        extra_head=extra_head,
        extra_script=_workspace_script(),
    )


def _render_chart_artifacts(charts: Sequence[Mapping[str, Any]]) -> str:
    if not charts:
        return """
        <div class="empty-state">
          <h3>暂无可视化输出</h3>
          <p>请先在工作台确认分析流程是否执行成功。</p>
        </div>
        """
    cards: list[str] = []
    for chart in charts:
        status = _text(chart.get("status"), "ready")
        status_cls = "status-chip-ready" if status == "ready" else "status-chip-missing"
        open_url = _text(chart.get("open_url"))
        reason = _text(chart.get("reason"))
        iframe = ""
        if open_url and status == "ready":
            iframe = f'<iframe class="chart-iframe" loading="lazy" src="{escape(open_url)}" title="{escape(_text(chart.get("title"), "chart"))}"></iframe>'

        cards.append(
            f"""
            <article class="artifact-card chart-card">
              <div class="artifact-card-head">
                <h3>{escape(_text(chart.get("title") or chart.get("name"), "图表"))}</h3>
                <span class="status-chip {status_cls}">{escape(status)}</span>
              </div>
              <p>{escape(_text(chart.get("summary"), "图表输出"))}</p>
              {iframe or f'<div class="chart-missing">{escape(reason or "无可预览内容")}</div>'}
              {_artifact_links(open_url=open_url, download_url=_text(chart.get("download_url")))}
            </article>
            """
        )
    return "".join(cards)


def _dashboard_script() -> str:
    return """
    <script type="module">
      import PhotoSwipeLightbox from 'https://cdn.jsdelivr.net/npm/photoswipe@5.4.4/dist/photoswipe-lightbox.esm.min.js';
      const lightbox = new PhotoSwipeLightbox({
        gallery: '#gallery',
        children: 'a.pswp-link',
        pswpModule: () => import('https://cdn.jsdelivr.net/npm/photoswipe@5.4.4/dist/photoswipe.esm.min.js')
      });
      lightbox.init();
    </script>
    """


def render_dashboard_page(
    run: Mapping[str, Any],
    *,
    charts: Sequence[Mapping[str, Any]] | None = None,
    page_title: str = "SentiDemand Hub - Dashboard",
) -> str:
    """Render dashboard page with chart-only content."""

    run_id = _run_id_from_payload(run)
    chart_list = list(charts or [])
    content = f"""
    <section class="workspace-hero">
      <div>
        <span class="hero-eyebrow">Dashboard</span>
        <h1>{escape(_text(run.get("title") or run.get("source_name") or run_id, "可视化仪表盘"))}</h1>
        <p>此页面只展示可视化输出。缺失图表会标注原因，避免“按钮点了没反应”。</p>
      </div>
      <div class="workspace-hero-actions">
        <a class="ghost-link" href="/workspace/{escape(run_id)}">表格页</a>
        <a class="ghost-link" href="/insights/{escape(run_id)}">建议页</a>
        <a class="ghost-link ghost-link-strong" href="/legacy">旧版入口</a>
      </div>
    </section>
    <section class="artifact-grid" id="gallery">
      {_render_chart_artifacts(chart_list)}
    </section>
    """
    extra_head = (
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/photoswipe@5.4.4/dist/photoswipe.css">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&'
        'family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">'
    )
    return _shell(
        page_title,
        content,
        active_nav="workspace",
        extra_head=extra_head,
        extra_script=_dashboard_script(),
    )


def render_insights_page(
    run: Mapping[str, Any],
    *,
    insight_markdown: str,
    insight_status: str,
    page_title: str = "SentiDemand Hub - Insights",
) -> str:
    """Render insights page with DeepSeek manual trigger."""

    run_id = _run_id_from_payload(run)
    safe_markdown = escape(insight_markdown or "还没有建议内容，请先填写 DeepSeek Key 并点击“生成建议”。")
    content = f"""
    <section class="workspace-hero">
      <div>
        <span class="hero-eyebrow">Insights</span>
        <h1>{escape(_text(run.get("title") or run.get("source_name") or run_id, "建议输出"))}</h1>
        <p>建议页使用 DeepSeek 手动触发，结果会保存为 insights/advice.md 和 insights/advice.json。</p>
      </div>
      <div class="workspace-hero-actions">
        <a class="ghost-link" href="/workspace/{escape(run_id)}">表格页</a>
        <a class="ghost-link" href="/dashboard/{escape(run_id)}">仪表盘</a>
        <a class="ghost-link ghost-link-strong" href="/legacy">旧版入口</a>
      </div>
    </section>
    <section class="insight-panel">
      <div class="insight-controls">
        <label for="deepseek-key">DeepSeek API Key</label>
        <input id="deepseek-key" type="password" placeholder="sk-..." autocomplete="off" />
        <button class="ghost-link" id="save-key" type="button">保存会话密钥</button>
        <button class="primary-link" id="generate-insight" type="button">生成建议</button>
        <span class="status-chip status-chip-neutral" id="insight-status">{escape(insight_status or "not_generated")}</span>
      </div>
      <pre class="insight-markdown" id="insight-markdown">{safe_markdown}</pre>
    </section>
    """

    script = f"""
    <script>
    (() => {{
      const runId = {json.dumps(run_id)};
      const keyInput = document.getElementById("deepseek-key");
      const saveBtn = document.getElementById("save-key");
      const generateBtn = document.getElementById("generate-insight");
      const statusNode = document.getElementById("insight-status");
      const markdownNode = document.getElementById("insight-markdown");
      const storageKey = "sentidemand-deepseek-session-id";

      saveBtn.addEventListener("click", async () => {{
        const key = keyInput.value.trim();
        if (!key) {{
          statusNode.textContent = "missing_key";
          return;
        }}
        statusNode.textContent = "saving_key";
        try {{
          const resp = await fetch("/api/session/deepseek-key", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ api_key: key }}),
          }});
          const payload = await resp.json();
          if (!resp.ok) throw new Error(payload.detail || "密钥保存失败");
          localStorage.setItem(storageKey, payload.session_id);
          statusNode.textContent = "key_saved";
        }} catch (err) {{
          statusNode.textContent = err instanceof Error ? err.message : "密钥保存失败";
        }}
      }});

      generateBtn.addEventListener("click", async () => {{
        const sessionId = localStorage.getItem(storageKey) || "";
        statusNode.textContent = "generating";
        generateBtn.disabled = true;
        try {{
          const resp = await fetch(`/api/runs/${{runId}}/insights/generate`, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ session_id: sessionId }}),
          }});
          const payload = await resp.json();
          if (!resp.ok) throw new Error(payload.detail || "建议生成失败");
          markdownNode.textContent = payload.advice_markdown || "无建议内容";
          statusNode.textContent = payload.insight_status || "generated";
        }} catch (err) {{
          statusNode.textContent = err instanceof Error ? err.message : "建议生成失败";
        }} finally {{
          generateBtn.disabled = false;
        }}
      }});
    }})();
    </script>
    """

    extra_head = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&'
        'family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">'
    )
    return _shell(
        page_title,
        content,
        active_nav="workspace",
        extra_head=extra_head,
        extra_script=script,
    )


def _render_table_panel(tables: Sequence[Mapping[str, Any]]) -> str:
    if not tables:
        return "<p class='panel-placeholder'>暂无派生表格预览</p>"
    rows = []
    for table in tables[:4]:
        rows.append(
            f"""
            <article class="preview-block">
              <h4>{escape(_text(table.get("title") or table.get("name"), "表格"))}</h4>
              <p>{escape(_text(table.get("summary"), "结构预览"))}</p>
              {_artifact_links(open_url=_text(table.get("open_url")), download_url=_text(table.get("download_url")))}
            </article>
            """
        )
    return "".join(rows)


def _render_logs_panel(logs: Sequence[Any]) -> str:
    if not logs:
        return "<p class='panel-placeholder'>暂无日志摘要</p>"
    items: list[str] = []
    for entry in list(logs)[:6]:
        if isinstance(entry, Mapping):
            items.append(
                f"<li><strong>{escape(_text(entry.get('title') or entry.get('category'), '日志'))}</strong>"
                f"<span>{escape(_text(entry.get('message') or entry.get('summary'), ''))}</span>"
                f"{_artifact_links(open_url=_text(entry.get('open_url')), download_url=_text(entry.get('download_url')))}</li>"
            )
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
              <h4>{escape(_text(chart.get("title") or chart.get("name"), "图表"))}</h4>
              <p>{escape(_text(chart.get("summary"), "图表输出"))}</p>
              {_artifact_links(open_url=_text(chart.get("open_url")), download_url=_text(chart.get("download_url")))}
            </article>
            """
        )
    return "".join(cards)


def render_detail_page(
    run: Mapping[str, Any],
    *,
    derived_tables: Sequence[Mapping[str, Any]] | None = None,
    logs: Sequence[Any] | None = None,
    charts: Sequence[Mapping[str, Any]] | None = None,
    page_title: str = "SentiDemand Hub - Legacy Detail",
) -> str:
    """Render legacy combined detail page."""

    run_id = _run_id_from_payload(run)
    content = f"""
    <section class="detail-hero">
      <div>
        <span class="hero-eyebrow">Legacy Detail</span>
        <h1>{escape(_text(run.get("title") or run.get("source_name") or run_id, "旧版详情"))}</h1>
        <p>{escape(_text(run.get("summary"), "旧版页面保留用于对照。"))}</p>
      </div>
      <div class="detail-actions">
        <a class="ghost-link" href="/workspace/{escape(run_id)}">表格页</a>
        <a class="ghost-link" href="/dashboard/{escape(run_id)}">图表页</a>
        <a class="ghost-link" href="/insights/{escape(run_id)}">建议页</a>
      </div>
    </section>
    <section class="detail-grid">
      <article class="detail-panel"><h2>表格</h2>{_render_table_panel(list(derived_tables or []))}</article>
      <article class="detail-panel"><h2>日志</h2>{_render_logs_panel(list(logs or []))}</article>
      <article class="detail-panel"><h2>图表</h2>{_render_chart_panel(list(charts or []))}</article>
    </section>
    """
    extra_head = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&'
        'family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">'
    )
    return _shell(page_title, content, active_nav="legacy", extra_head=extra_head)


def render_legacy_page(
    runs: Sequence[Mapping[str, Any]],
    *,
    page_title: str = "SentiDemand Hub - Legacy",
) -> str:
    """Render legacy entry page."""

    content = f"""
    <section class="workspace-hero">
      <div>
        <span class="hero-eyebrow">Legacy Mode</span>
        <h1>旧版入口</h1>
        <p>这里保留旧版合并视图，便于和新版对照。建议优先使用新版四页面结构。</p>
      </div>
      <div class="workspace-hero-actions">
        <a class="primary-link" href="/">新版主页</a>
        <a class="ghost-link" href="/workspace">新版工作台</a>
      </div>
    </section>
    <section class="history-section">
      <div class="section-heading compact">
        <h2>选择运行进入旧版详情</h2>
      </div>
      <div class="history-card-grid">{_render_history_cards(runs)}</div>
    </section>
    """
    extra_head = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&'
        'family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">'
    )
    return _shell(page_title, content, active_nav="legacy", extra_head=extra_head)

