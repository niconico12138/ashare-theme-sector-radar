"""
多窗口趋势共识 Agent 测试

测试 MultiWindowConsensusAgent 的各项功能。
"""

import pytest

from theme_sector_radar.agents.multi_window_consensus import MultiWindowConsensusAgent


class TestMultiWindowConsensusLabels:
    """测试多窗口标签规则"""

    def _create_agent(self):
        return MultiWindowConsensusAgent()

    def test_multi_window_confirmed(self):
        """测试 multi_window_confirmed: 5/10/20 均 >= 50"""
        agent = self._create_agent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 55.0, "trend_level": "neutral", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 52.0, "trend_level": "neutral", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 51.0, "trend_level": "neutral", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["multi_window_label"] == "multi_window_confirmed"

    def test_short_mid_strong_long_weak(self):
        """测试 short_mid_strong_long_weak: 5/10 >= 45, 20 < 45"""
        agent = self._create_agent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 48.0, "trend_level": "cooling", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 46.0, "trend_level": "cooling", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 30.0, "trend_level": "avoid", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["multi_window_label"] == "short_mid_strong_long_weak"

    def test_short_active_only(self):
        """测试 short_active_only: 5 >= 50, 10/20 < 45"""
        agent = self._create_agent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 52.0, "trend_level": "neutral", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 40.0, "trend_level": "cooling", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 35.0, "trend_level": "cooling", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["multi_window_label"] == "short_active_only"

    def test_long_stable_short_cooling(self):
        """测试 long_stable_short_cooling: 20 >= 50, 5 < 45"""
        agent = self._create_agent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 40.0, "trend_level": "cooling", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 48.0, "trend_level": "cooling", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 52.0, "trend_level": "neutral", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["multi_window_label"] == "long_stable_short_cooling"

    def test_weak_all_windows(self):
        """测试 weak_all_windows: 5/10/20 均 < 45"""
        agent = self._create_agent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 40.0, "trend_level": "cooling", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 35.0, "trend_level": "cooling", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 30.0, "trend_level": "avoid", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["multi_window_label"] == "weak_all_windows"

    def test_insufficient_history_priority(self):
        """测试 insufficient_history 优先级最高"""
        agent = self._create_agent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 55.0, "trend_level": "neutral", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 52.0, "trend_level": "neutral", "actual_history_days": 10, "history_coverage_ratio": 0.5, "trend_window_status": "ok"},  # coverage 不足
                "20": {"trend_continuation_score": 51.0, "trend_level": "neutral", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["multi_window_label"] == "insufficient_history"


class TestConsensusScore:
    """测试共识分数计算"""

    def test_consensus_score_weighted_average(self):
        """测试加权平均: 0.25/0.35/0.40"""
        agent = MultiWindowConsensusAgent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 100.0, "trend_level": "neutral", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 100.0, "trend_level": "neutral", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 100.0, "trend_level": "neutral", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        # 所有窗口都是 100，共识分数应该是 100
        assert result["consensus_score"] == 100.0

    def test_consensus_score_different_weights(self):
        """测试不同权重"""
        agent = MultiWindowConsensusAgent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 0.0, "trend_level": "avoid", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 0.0, "trend_level": "avoid", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 100.0, "trend_level": "strong_watch", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        # 20日权重 0.40，分数 100，共识分数应该是 40
        assert result["consensus_score"] == 40.0


class TestConsensusStrength:
    """测试共识强度"""

    def test_strong(self):
        """测试 strong: >= 65"""
        agent = MultiWindowConsensusAgent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 70.0, "trend_level": "watch", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 70.0, "trend_level": "watch", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 70.0, "trend_level": "watch", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["consensus_strength"] == "strong"

    def test_medium(self):
        """测试 medium: >= 50"""
        agent = MultiWindowConsensusAgent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 55.0, "trend_level": "neutral", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 55.0, "trend_level": "neutral", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 55.0, "trend_level": "neutral", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["consensus_strength"] == "medium"

    def test_weak(self):
        """测试 weak: >= 35"""
        agent = MultiWindowConsensusAgent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 40.0, "trend_level": "cooling", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 40.0, "trend_level": "cooling", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 40.0, "trend_level": "cooling", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["consensus_strength"] == "weak"

    def test_very_weak(self):
        """测试 very_weak: < 35"""
        agent = MultiWindowConsensusAgent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 30.0, "trend_level": "avoid", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 30.0, "trend_level": "avoid", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 30.0, "trend_level": "avoid", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        assert result["consensus_strength"] == "very_weak"


class TestMultiWindowConsensusReport:
    """测试多窗口共识报告"""

    def test_json_report_contract(self):
        """测试 JSON 报告字段完整"""
        from theme_sector_radar.reports.multi_window_consensus_report import generate_multi_window_consensus_report

        report_data = {
            "as_of_date": "2026-06-29",
            "sector_type": "industry",
            "report_type": "multi_window_consensus",
            "trend_weight_profile": "trend_confirmation",
            "windows": [5, 10, 20],
            "metadata": {
                "history_start_date": "2026-05-20",
                "history_end_date": "2026-06-30",
                "benchmark": "hs300",
                "top_n": 20,
            },
            "consensus": [
                {
                    "sector_name": "测试板块",
                    "multi_window_label": "multi_window_confirmed",
                    "consensus_score": 55.0,
                    "consensus_strength": "medium",
                    "window_scores": {"5": 55.0, "10": 55.0, "20": 55.0},
                    "window_levels": {"5": "neutral", "10": "neutral", "20": "neutral"},
                    "window_conflicts": [],
                    "watch_points": ["观察趋势是否持续"],
                    "data_warnings": [],
                }
            ],
            "warnings": [],
            "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
        }

        report = generate_multi_window_consensus_report(report_data)

        assert "多窗口趋势共识报告" in report
        assert "测试板块" in report
        assert "multi_window_confirmed" in report
        assert "55.0" in report

    def test_markdown_report_contract(self):
        """测试 Markdown 报告字段完整"""
        from theme_sector_radar.reports.multi_window_consensus_report import generate_multi_window_consensus_report

        report_data = {
            "as_of_date": "2026-06-29",
            "sector_type": "industry",
            "report_type": "multi_window_consensus",
            "trend_weight_profile": "trend_confirmation",
            "windows": [5, 10, 20],
            "metadata": {
                "history_start_date": "2026-05-20",
                "history_end_date": "2026-06-30",
                "benchmark": "hs300",
                "top_n": 20,
            },
            "consensus": [],
            "warnings": [],
            "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
        }

        report = generate_multi_window_consensus_report(report_data)

        assert "多窗口趋势共识报告" in report
        assert "参数" in report
        assert "共识" in report
        assert "免责声明" in report

    def test_report_has_no_trade_advice_words(self):
        """测试报告不包含禁止词"""
        from theme_sector_radar.reports.multi_window_consensus_report import generate_multi_window_consensus_report

        report_data = {
            "as_of_date": "2026-06-29",
            "sector_type": "industry",
            "report_type": "multi_window_consensus",
            "trend_weight_profile": "trend_confirmation",
            "windows": [5, 10, 20],
            "metadata": {},
            "consensus": [],
            "warnings": [],
            "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
        }

        report = generate_multi_window_consensus_report(report_data)

        # 禁止词检查
        forbidden_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐", "建仓", "加仓", "减仓", "止盈", "止损", "目标价"]
        for word in forbidden_words:
            assert word not in report.lower(), f"报告包含禁止词: {word}"
