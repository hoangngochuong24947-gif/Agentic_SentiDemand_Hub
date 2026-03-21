from __future__ import annotations

from pathlib import Path

from comment_analyzer.visualization.pages import (
    DEFAULT_CRAWLER_GUIDANCE,
    render_detail_page,
    render_homepage_page,
    render_workspace_page,
)


def test_render_homepage_page_contains_showcase_sections():
    html = render_homepage_page(
        runs=[
            {
                "title": "Run 2026-03-18",
                "status": "completed",
                "created_at": "2026-03-18 09:12",
                "source_name": "sample_comments.csv",
                "summary": "Processed 3,240 comments",
                "href": "/runs/2026-03-18",
            }
        ]
    )

    assert "Agentic SentiDemand Hub" in html
    assert "hero-marquee-track" in html
    assert "选择评论文件" in html
    assert "上传评论文件并直接进入分析详情" in html
    assert "surface-card accent-help" in html
    assert "surface-card accent-history" in html
    assert "surface-card accent-crawler" in html
    assert "history-card-grid" in html
    assert "crawler-guidance-section" in html
    assert "Crawler 01" in html
    assert "采集脚本说明卡片" in html


def test_render_workspace_page_lists_runs():
    html = render_workspace_page(
        runs=[
            {
                "title": "March refresh",
                "status": "success",
                "created_at": "2026-03-17 21:00",
                "source_name": "march.csv",
                "summary": "Healthy refresh",
                "href": "/runs/march-refresh",
            },
            {
                "title": "Previous import",
                "status": "failed",
                "created_at": "2026-03-16 08:30",
                "source_name": "april.csv",
                "summary": "Retry needed",
                "href": "/runs/previous-import",
            },
        ]
    )

    assert "Historical runs" in html
    assert "March refresh" in html
    assert "Previous import" in html
    assert "运行总数" in html
    assert "最近成功" in html
    assert "待处理" in html


def test_render_detail_page_includes_three_panels_and_quick_actions():
    html = render_detail_page(
        {
            "title": "Run 2026-03-18",
            "status": "completed",
            "created_at": "2026-03-18 09:12",
            "source_name": "sample_comments.csv",
        },
        derived_tables=[
            {
                "title": "Sentiment summary",
                "summary": "Derived table preview",
                "columns": ["label", "count"],
                "rows": [
                    {"label": "positive", "count": 42},
                    {"label": "neutral", "count": 18},
                ],
                "open_url": "/runs/test/artifacts/tables/0",
            }
        ],
        logs=[
            {
                "title": "Pipeline summary",
                "message": "step 2 completed",
                "open_url": "/runs/test/artifacts/logs/0",
            }
        ],
        charts=[
            {
                "type": "line",
                "title": "Demand over time",
                "summary": "Chart preview placeholder",
                "open_url": "/chart/1234",
            }
        ],
    )

    assert "Panel 01" in html
    assert "派生表格" in html
    assert "Panel 02" in html
    assert "日志" in html
    assert "Panel 03" in html
    assert "图表" in html
    assert "预览" in html
    assert "快捷入口" in html
    assert "打开表格导出" in html
    assert "复制日志" in html
    assert "打开图表页面" in html
    assert "/chart/1234" in html


def test_crawler_guidance_cards_are_static_and_complete():
    assert len(DEFAULT_CRAWLER_GUIDANCE) == 3
    html = render_homepage_page(crawler_guidance=DEFAULT_CRAWLER_GUIDANCE)

    assert html.count('<article class="crawler-card">') == 3
    assert "exp1_bilibili_requests.py" in html
    assert "exp2_jd_reviews_connect.py" in html
    assert "start_chrome.ps1" in html
    assert "说明型入口，不直接在网页内执行脚本" in html


def test_chart_template_is_left_intact():
    base_template = Path("src/comment_analyzer/visualization/templates/base.html").read_text(
        encoding="utf-8"
    )

    assert "echarts.min.js" in base_template
    assert "{{CHART_TITLE}}" in base_template
