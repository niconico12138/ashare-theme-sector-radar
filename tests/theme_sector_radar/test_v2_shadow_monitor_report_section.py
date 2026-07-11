"""
V2 Shadow Monitor 报告小节测试

覆盖：
- monitor=None 时输出暂无数据
- yellow 状态灯正常展示
- 分歧样本最多展示 5 个
- 使用边界文案存在
- 不包含买卖建议字样
- 日报生成缺 monitor 文件不失败
- v2 均值显示正确（不是 Rank IC）
- v2 Rank IC 均值显示正确
- 历史表现字段缺失时优雅降级
- 新定位文案正确
- "V2 潜力观察名单" 标题存在
- "V2 分歧复核名单" 标题存在
- 不再出现"风险/防守维度复核"作为主定位
- 不包含"自动剔除"
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.v2_shadow_monitor_section import (
    load_v2_shadow_monitor,
    build_v2_shadow_monitor_markdown,
)


# ============================================================
# Load Monitor Tests
# ============================================================

class TestLoadMonitor:
    """测试加载 monitor 数据。"""

    def test_load_existing_file(self, tmp_path):
        """应正确加载存在的文件。"""
        monitor = {"latest_snapshot": {"date": "2026-07-10"}}
        path = tmp_path / "v2_shadow_monitor.json"
        path.write_text(json.dumps(monitor), encoding="utf-8")

        result = load_v2_shadow_monitor(path)

        assert result is not None
        assert result["latest_snapshot"]["date"] == "2026-07-10"

    def test_load_missing_file(self, tmp_path):
        """不存在的文件应返回 None。"""
        path = tmp_path / "v2_shadow_monitor.json"

        result = load_v2_shadow_monitor(path)

        assert result is None


# ============================================================
# Build Markdown Tests
# ============================================================

class TestBuildMarkdown:
    """测试构建 Markdown 小节。"""

    def test_none_monitor(self):
        """monitor=None 时应输出暂无数据。"""
        result = build_v2_shadow_monitor_markdown(None)

        assert "暂无数据" in result
        assert "update_factor_v2_shadow_monitor.py" in result

    def test_yellow_status(self):
        """yellow 状态灯应正常展示。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "样本不足"},
            "latest_snapshot": {"date": "2026-07-10"},
            "historical_performance": {"v2_ic_mean": 0.02, "sample_days": 30},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "🟡" in result
        assert "yellow" in result
        assert "样本不足" in result

    def test_green_status(self):
        """green 状态灯应正常展示。"""
        monitor = {
            "monitor_status": {"status": "green", "reason": "v2 IC 为正"},
            "latest_snapshot": {},
            "historical_performance": {},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "🟢" in result
        assert "green" in result

    def test_red_status(self):
        """red 状态灯应正常展示。"""
        monitor = {
            "monitor_status": {"status": "red", "reason": "v2 IC 为负"},
            "latest_snapshot": {},
            "historical_performance": {},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "🔴" in result
        assert "red" in result

    def test_divergence_samples_max_5(self):
        """分歧样本最多展示 5 个。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {},
            "historical_performance": {},
            "divergence_samples": [
                {"code": f"60000{i}", "name": f"股票{i}", "final_score": 80, "factor_composite_shadow_score_v2": 30, "reason": "high_final_low_v2"}
                for i in range(1, 11)
            ],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        # 检查最多展示 5 个
        assert result.count("60000") <= 5

    def test_usage_boundary_text(self):
        """使用边界文案应存在。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {},
            "historical_performance": {},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "不参与正式排序" in result
        assert "不构成买卖建议" in result
        assert "独立机会发现与分歧复核" in result
        assert "不自动纳入或剔除" in result

    def test_no_buy_sell_advice(self):
        """不应包含买卖建议字样。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {},
            "historical_performance": {},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "买入" not in result
        assert "卖出" not in result
        assert "仓位" not in result

    def test_snapshot_shows_v2_mean_not_rank_ic(self):
        """最新快照中 v2 均值应显示为 v2 均值，不是 Rank IC。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {
                "date": "2026-07-10",
                "v2_mean": 28.02,
                "v2_std": 2.28,
                "v2_coverage": 100.0,
                "v2_final_correlation": 0.0773,
            },
            "historical_performance": {"v2_ic_mean": 0.0239, "sample_days": 41},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        # v2 均值应显示为 28.02
        assert "v2 均值: 28.02" in result
        # 不应将 28.02 标记为 Rank IC
        assert "v2 Rank IC 均值: 28.02" not in result
        # 应显示当前定位
        assert "当前定位: 独立机会发现 + 分歧复核" in result

    def test_historical_shows_rank_ic_correctly(self):
        """历史表现中 Rank IC 应正确显示。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {
                "date": "2026-07-10",
                "v2_mean": 28.02,
            },
            "historical_performance": {
                "v2_ic_mean": 0.0239,
                "v2_ic_win_rate": 51.22,
                "v2_top5_return": 0.318,
                "v2_bottom5_return": 0.2689,
                "v2_spread": 0.0491,
                "sample_days": 41,
            },
            "lookback_days": 60,
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        # Rank IC 应显示为 0.0239
        assert "v2 Rank IC 均值: 0.0239" in result
        assert "v2 IC Win Rate: 51.22%" in result
        assert "v2 Top5 平均收益: 0.318%" in result
        assert "v2 Bottom5 平均收益: 0.2689%" in result
        assert "v2 Spread: 0.0491%" in result
        # 应显示历史分歧复盘提示
        assert "low_final_high_v2 具备独立观察价值" in result

    def test_missing_historical_performance(self):
        """历史表现字段缺失时应显示暂无数据。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {"date": "2026-07-10"},
            "historical_performance": {},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "暂无历史表现数据" in result

    def test_historical_performance_zero_sample_days(self):
        """历史表现 sample_days=0 时应显示暂无数据。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {"date": "2026-07-10"},
            "historical_performance": {"sample_days": 0},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "暂无历史表现数据" in result

    def test_v2_potential_watchlist_title(self):
        """应显示 "V2 潜力观察名单" 标题。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {},
            "historical_performance": {},
            "divergence_samples": [
                {"code": "600001", "name": "股票A", "final_score": 30, "factor_composite_shadow_score_v2": 80, "reason": "low_final_high_v2"},
            ],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "V2 潜力观察名单" in result
        assert "历史复盘显示具备独立观察价值" in result

    def test_v2_disagreement_review_title(self):
        """应显示 "V2 分歧复核名单" 标题。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {},
            "historical_performance": {},
            "divergence_samples": [
                {"code": "600001", "name": "股票A", "final_score": 80, "factor_composite_shadow_score_v2": 30, "reason": "high_final_low_v2"},
            ],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "V2 分歧复核名单" in result
        assert "仅提示人工复核" in result

    def test_no_risk_defense_positioning(self):
        """不应出现"风险/防守维度复核"作为主定位。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {},
            "historical_performance": {},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "风险/防守维度复核" not in result

    def test_no_auto_exclude(self):
        """不应包含"自动剔除"。"""
        monitor = {
            "monitor_status": {"status": "yellow", "reason": "test"},
            "latest_snapshot": {},
            "historical_performance": {},
            "divergence_samples": [],
        }

        result = build_v2_shadow_monitor_markdown(monitor)

        assert "自动剔除" not in result


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """集成测试。"""

    def test_show_daily_result_with_monitor(self, tmp_path, monkeypatch):
        """日报生成缺 monitor 文件不失败。"""
        # 创建 mock 的 unified_report
        unified_dir = tmp_path / "reports" / "unified" / "2026-07-10"
        unified_dir.mkdir(parents=True)
        (unified_dir / "unified_report.json").write_text(
            json.dumps({"data_source": {}, "run_health": {}, "data_quality": {}}),
            encoding="utf-8",
        )

        # 运行 show_daily_result
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import show_daily_result

        # Monkeypatch 路径
        monkeypatch.setattr(show_daily_result, "UNIFIED_DIR", tmp_path / "reports" / "unified")
        monkeypatch.setattr(show_daily_result, "SECTOR_RESEARCH_DIR", tmp_path / "reports" / "full90" / "sector_research")
        monkeypatch.setattr(show_daily_result, "CONCEPT_RANK_DIR", tmp_path / "reports" / "full_concept" / "unified_rank")
        monkeypatch.setattr(show_daily_result, "V2_SHADOW_MONITOR_PATH", tmp_path / "nonexistent.json")

        # 不应抛出异常
        try:
            show_daily_result.main()
        except SystemExit:
            pass  # argparse 可能会退出
