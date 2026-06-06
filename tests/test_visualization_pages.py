from __future__ import annotations

from pathlib import Path

from comment_analyzer.visualization.pages import (
    DEFAULT_CRAWLER_GUIDANCE,
    render_dashboard_page,
    render_homepage_page,
    render_insights_page,
    render_legacy_page,
    render_workspace_page,
)


def test_render_homepage_page_contains_new_navigation_and_actions():
    html = render_homepage_page(
        runs=[
            {
                "run_id": "run-001",
                "title": "Run 001",
                "status": "completed",
                "created_at": "2026-03-18 09:12",
                "source_name": "sample_comments.csv",
                "summary": "Processed 3,240 comments",
                "href": "/workspace/run-001",
            }
        ]
    )

    assert "SentiDemand Hub v2" in html
    assert "上传并分析" in html
    assert "/workspace" in html
    assert "/legacy" in html
    assert "采集脚本说明" in html


def test_render_workspace_page_contains_table_panel_and_cross_page_links():
    html = render_workspace_page(
        runs=[
            {
                "run_id": "run-001",
                "title": "March refresh",
                "status": "success",
                "created_at": "2026-03-17 21:00",
                "source_name": "march.csv",
                "summary": "Healthy refresh",
                "href": "/workspace/run-001",
            }
        ],
        selected_run={
            "run_id": "run-001",
            "title": "March refresh",
            "status": "success",
            "source_name": "march.csv",
            "summary": "Healthy refresh",
        },
        tables=[
            {
                "title": "Sentiment summary",
                "summary": "Derived table preview",
                "status": "ready",
                "preview": {
                    "columns": ["label", "count"],
                    "rows": [{"label": "positive", "count": "42"}],
                },
                "open_url": "/runs/run-001/artifacts/tables/0",
                "download_url": "/runs/run-001/artifacts/tables/0?download=true",
            }
        ],
    )

    assert "表格工作台" in html
    assert "table-grid" in html
    assert "/dashboard/run-001" in html
    assert "/insights/run-001" in html


def test_render_dashboard_page_contains_iframe_and_missing_reason():
    html = render_dashboard_page(
        {"run_id": "run-002", "title": "Run 002"},
        charts=[
            {
                "title": "Sentiment donut",
                "summary": "Chart ready",
                "status": "ready",
                "open_url": "/runs/run-002/artifacts/charts/0",
                "download_url": "/runs/run-002/artifacts/charts/0?download=true",
            },
            {
                "title": "Demand network",
                "summary": "Chart missing",
                "status": "missing",
                "reason": "数据不足或该图表在当前数据条件下被跳过。",
                "open_url": "",
                "download_url": "",
            },
        ],
    )

    assert "Dashboard" in html
    assert "chart-iframe" in html
    assert "数据不足或该图表在当前数据条件下被跳过。" in html


def test_render_insights_page_contains_manual_trigger_controls():
    html = render_insights_page(
        {"run_id": "run-003", "title": "Run 003"},
        insight_markdown="## 建议\\n- 提升物流稳定性",
        insight_status="generated",
    )

    assert "DeepSeek API Key" in html
    assert "生成建议" in html
    assert "/api/session/deepseek-key" in html
    assert "/api/runs/${runId}/insights/generate" in html


def test_render_legacy_page_keeps_parallel_entry():
    html = render_legacy_page(
        runs=[
            {
                "run_id": "run-004",
                "title": "Run 004",
                "status": "completed",
                "source_name": "legacy.csv",
                "summary": "legacy summary",
                "href": "/workspace/run-004",
            }
        ]
    )

    assert "旧版入口" in html
    assert "/runs/run-004" in html


def test_crawler_guidance_cards_are_static_and_complete():
    assert len(DEFAULT_CRAWLER_GUIDANCE) == 3
    html = render_homepage_page(crawler_guidance=DEFAULT_CRAWLER_GUIDANCE)

    assert html.count('<article class="crawler-card">') == 3
    assert "exp1_bilibili_requests.py" in html
    assert "exp2_jd_reviews_connect.py" in html
    assert "start_chrome.ps1" in html


def test_chart_template_is_left_intact():
    base_template = Path("src/comment_analyzer/visualization/templates/base.html").read_text(
        encoding="utf-8"
    )

    assert "echarts.min.js" in base_template
    assert "{{CHART_TITLE}}" in base_template
