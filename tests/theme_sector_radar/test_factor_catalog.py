"""Factor catalog contract tests."""

from pathlib import Path

from theme_sector_radar.factors.registry import FACTOR_REGISTRY


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_PATH = PROJECT_ROOT / "docs" / "runbooks" / "factor_catalog.md"


def _catalog_text() -> str:
    return CATALOG_PATH.read_text(encoding="utf-8")


def test_factor_catalog_exists():
    assert CATALOG_PATH.exists()


def test_catalog_lists_all_registered_factors():
    content = _catalog_text()
    missing = [factor_id for factor_id in FACTOR_REGISTRY if f"`{factor_id}`" not in content]
    assert not missing


def test_catalog_defines_usage_layers():
    content = _catalog_text()
    for usage_layer in [
        "official_score",
        "pool_signal",
        "selection_quality",
        "shadow_score",
        "stock_profile",
        "risk_review",
        "explanation_only",
        "research_only",
    ]:
        assert usage_layer in content


def test_catalog_marks_official_and_shadow_boundaries():
    content = _catalog_text()
    assert "| `final_score` |" in content
    assert "Primary official ranking score" in content
    assert "| `factor_composite_shadow_score_v2` |" in content
    assert "Independent opportunity discovery" in content
    assert "shadow-only" in content


def test_catalog_documents_bars_factor_semantics():
    content = _catalog_text()
    assert "| `breakout_distance_20` |" in content
    assert "Structure position only" in content
    assert "| `drawdown_depth_20` |" in content
    assert "Pullback/repair context" in content
    assert "| `chasing_risk_score` |" in content
    assert "Overheat shadow warning" in content
    assert "| `liquidity_score` |" in content
    assert "Profile-only liquidity context" in content


def test_catalog_includes_research_reserve():
    content = _catalog_text()
    for factor_name in ["RS_Return", "RS_Breadth", "MKT", "IND", "SMB", "HML", "LIQ", "Cum_Residual"]:
        assert factor_name in content


def test_catalog_has_promotion_rules():
    content = _catalog_text()
    assert "Promotion Rules" in content
    assert "raw value, score, direction, and lookback" in content
    assert "historical forward returns" in content
    assert "must not change official ranking" in content

