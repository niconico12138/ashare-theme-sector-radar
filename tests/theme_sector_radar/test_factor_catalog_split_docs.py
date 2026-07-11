from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_ROOT = PROJECT_ROOT / "docs" / "runbooks"


def _read_doc(name: str) -> str:
    return (RUNBOOK_ROOT / name).read_text(encoding="utf-8")


def test_split_catalog_docs_exist():
    assert (RUNBOOK_ROOT / "sector_factor_catalog.md").exists()
    assert (RUNBOOK_ROOT / "stock_factor_catalog.md").exists()
    assert (RUNBOOK_ROOT / "factor_usage_policy.md").exists()


def test_sector_catalog_documents_sector_factor_groups():
    text = _read_doc("sector_factor_catalog.md")

    for required in [
        "sector_trend_score",
        "sector_burst_score",
        "sector_support_score",
        "RS_Return",
        "RS_Breadth",
        "RS_Flow",
        "conflict_score",
        "catalyst_strength_score",
        "Sector-to-Stock Routing Rules",
    ]:
        assert required in text


def test_stock_catalog_documents_stock_factor_groups():
    text = _read_doc("stock_factor_catalog.md")

    for required in [
        "final_score",
        "stock_trend_score",
        "stock_short_score_v2",
        "factor_composite_shadow_score_v2",
        "breakout_distance_20",
        "drawdown_depth_20",
        "chasing_risk_score",
        "liquidity_score",
        "Stock Profile States",
    ]:
        assert required in text


def test_usage_policy_defines_layers_strategy_protocols_and_guardrails():
    text = _read_doc("factor_usage_policy.md")

    for required in [
        "official_score",
        "pool_signal",
        "selection_quality",
        "shadow_score",
        "stock_profile",
        "risk_review",
        "explanation_only",
        "research_only",
        "Trend-follow watch-only",
        "V2 opportunity watch-only",
        "Short-burst watch-only",
        "No factor may directly produce price levels or execution actions",
    ]:
        assert required in text
