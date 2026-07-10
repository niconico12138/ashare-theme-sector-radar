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
        """测试不同权重（自适应）"""
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
        # CV大 → trending → 20日权重0.55，基础分=0*0.15+0*0.30+100*0.55=55
        # 动量=(0-0)*0.3+(0-100)*0.3=-30 → cap -10
        # 最终=55-10=45
        assert result["consensus_score"] == 45.0
        assert result["market_regime"] == "trending"


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
                    "base_consensus": 55.0,
                    "momentum_bonus": 0.0,
                    "volume_confirmation_ratio": 1.0,
                    "market_regime": "oscillating",
                    "adaptive_weights": {"5": 0.35, "10": 0.35, "20": 0.30},
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


class TestAdaptiveWeights:
    """测试 A. 自适应权重"""

    def test_detect_market_regime_trending(self):
        """测试趋势行情检测：CV > 0.15"""
        agent = MultiWindowConsensusAgent()
        # 20日远高于5日和10日 → CV大
        scores = {"5": 40.0, "10": 50.0, "20": 70.0}
        regime = agent._detect_market_regime(scores)
        assert regime == "trending"

    def test_detect_market_regime_oscillating(self):
        """测试震荡行情检测：CV < 0.08"""
        agent = MultiWindowConsensusAgent()
        # 三个窗口分数接近 → CV小
        scores = {"5": 50.0, "10": 51.0, "20": 52.0}
        regime = agent._detect_market_regime(scores)
        assert regime == "oscillating"

    def test_detect_market_regime_breakout(self):
        """测试突破行情检测：0.08 <= CV <= 0.15"""
        agent = MultiWindowConsensusAgent()
        scores = {"5": 55.0, "10": 50.0, "20": 45.0}
        regime = agent._detect_market_regime(scores)
        assert regime == "breakout"

    def test_adaptive_weights_trending(self):
        """测试趋势行情权重：20日最大"""
        agent = MultiWindowConsensusAgent()
        weights = agent._get_adaptive_weights({"5": 40.0, "10": 50.0, "20": 70.0})
        assert weights["20"] > weights["10"] > weights["5"]
        assert weights["20"] == 0.55

    def test_adaptive_weights_oscillating(self):
        """测试震荡行情权重：5日最大"""
        agent = MultiWindowConsensusAgent()
        weights = agent._get_adaptive_weights({"5": 50.0, "10": 51.0, "20": 52.0})
        assert weights["5"] >= weights["10"]
        assert weights["5"] == 0.35

    def test_adaptive_consensus_score(self):
        """测试自适应权重下的共识分数"""
        agent = MultiWindowConsensusAgent()
        # 趋势行情：20日权重0.55
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 40.0, "trend_level": "cooling", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 50.0, "trend_level": "neutral", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 70.0, "trend_level": "watch", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        # 基础分 = 40*0.15 + 50*0.30 + 70*0.55 = 6 + 15 + 38.5 = 59.5
        assert result["base_consensus"] == 59.5
        assert result["market_regime"] == "trending"
        assert result["adaptive_weights"]["20"] == 0.55


class TestMomentumBonus:
    """测试 B. 动量方向加分"""

    def test_momentum_acceleration(self):
        """测试趋势加速：5日 > 10日 > 20日 → 正加分"""
        agent = MultiWindowConsensusAgent()
        bonus = agent._calculate_momentum_bonus({"5": 70.0, "10": 60.0, "20": 50.0})
        # (70-60)*0.3 + (60-50)*0.3 = 3 + 3 = 6
        assert bonus == 6.0

    def test_momentum_deceleration(self):
        """测试趋势减速：5日 < 10日 < 20日 → 负加分"""
        agent = MultiWindowConsensusAgent()
        bonus = agent._calculate_momentum_bonus({"5": 40.0, "10": 50.0, "20": 60.0})
        # (40-50)*0.3 + (50-60)*0.3 = -3 + -3 = -6
        assert bonus == -6.0

    def test_momentum_cap_positive(self):
        """测试正加分上限 +10"""
        agent = MultiWindowConsensusAgent()
        bonus = agent._calculate_momentum_bonus({"5": 100.0, "10": 50.0, "20": 0.0})
        # (100-50)*0.3 + (50-0)*0.3 = 15 + 15 = 30 → cap at 10
        assert bonus == 10.0

    def test_momentum_cap_negative(self):
        """测试负加分下限 -10"""
        agent = MultiWindowConsensusAgent()
        bonus = agent._calculate_momentum_bonus({"5": 0.0, "10": 50.0, "20": 100.0})
        # (0-50)*0.3 + (50-100)*0.3 = -15 + -15 = -30 → cap at -10
        assert bonus == -10.0

    def test_momentum_flat(self):
        """测试平盘：三窗口相同 → 0"""
        agent = MultiWindowConsensusAgent()
        bonus = agent._calculate_momentum_bonus({"5": 50.0, "10": 50.0, "20": 50.0})
        assert bonus == 0.0


class TestVolumeConfirmation:
    """测试 D. 量价共振确认"""

    def test_volume_high_trend_high(self):
        """测试放量+趋势高 → ratio = 1.1"""
        agent = MultiWindowConsensusAgent()
        ratio = agent._calculate_volume_confirmation_ratio(
            {"5": {"volume_or_heat_component": 8.0}},
            consensus_score=60.0,
        )
        assert ratio == 1.1

    def test_volume_low_trend_high(self):
        """测试缩量+趋势高 → ratio = 0.9"""
        agent = MultiWindowConsensusAgent()
        ratio = agent._calculate_volume_confirmation_ratio(
            {"5": {"volume_or_heat_component": 2.0}},
            consensus_score=60.0,
        )
        assert ratio == 0.9

    def test_volume_high_trend_low(self):
        """测试放量+趋势低 → ratio = 1.0（不调整）"""
        agent = MultiWindowConsensusAgent()
        ratio = agent._calculate_volume_confirmation_ratio(
            {"5": {"volume_or_heat_component": 8.0}},
            consensus_score=40.0,
        )
        assert ratio == 1.0

    def test_volume_none(self):
        """测试无量能数据 → ratio = 1.0"""
        agent = MultiWindowConsensusAgent()
        ratio = agent._calculate_volume_confirmation_ratio(
            {"5": {}},
            consensus_score=60.0,
        )
        assert ratio == 1.0

    def test_volume_neutral(self):
        """测试量能中性 → ratio = 1.0"""
        agent = MultiWindowConsensusAgent()
        ratio = agent._calculate_volume_confirmation_ratio(
            {"5": {"volume_or_heat_component": 5.0}},
            consensus_score=60.0,
        )
        assert ratio == 1.0


class TestV2Integration:
    """测试 v2 整合效果"""

    def test_v2_result_has_new_fields(self):
        """测试 v2 结果包含新字段"""
        agent = MultiWindowConsensusAgent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 60.0, "trend_level": "neutral", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok", "volume_or_heat_component": 8.0},
                "10": {"trend_continuation_score": 55.0, "trend_level": "neutral", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 50.0, "trend_level": "neutral", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        # 检查新字段存在
        assert "base_consensus" in result
        assert "momentum_bonus" in result
        assert "volume_confirmation_ratio" in result
        assert "market_regime" in result
        assert "adaptive_weights" in result

    def test_v2_consensus_score_formula(self):
        """测试 v2 共识分 = (基础分 + 动量加分) × 量价比"""
        agent = MultiWindowConsensusAgent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 70.0, "trend_level": "watch", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok", "volume_or_heat_component": 8.0},
                "10": {"trend_continuation_score": 60.0, "trend_level": "neutral", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 50.0, "trend_level": "neutral", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        # CV=8.16/60=0.136 → breakout（0.08~0.15之间）
        # 基础分（breakout）= 70*0.40 + 60*0.35 + 50*0.25 = 28 + 21 + 12.5 = 61.5
        # 动量加分 = (70-60)*0.3 + (60-50)*0.3 = 3 + 3 = 6.0
        # 量价比 = 1.1（放量8.0 + 趋势分61.5+6=67.5 >= 50）
        # 最终 = (61.5 + 6.0) × 1.1 = 74.25
        assert result["market_regime"] == "breakout"
        assert result["base_consensus"] == 61.5
        assert result["momentum_bonus"] == 6.0
        assert result["volume_confirmation_ratio"] == 1.1
        assert result["consensus_score"] == 74.25

    def test_v2_backward_compatible_label(self):
        """测试 v2 不改变标签逻辑"""
        agent = MultiWindowConsensusAgent()
        result = agent.analyze_sector(
            sector_name="测试板块",
            sector_type="industry",
            windows={
                "5": {"trend_continuation_score": 55.0, "trend_level": "neutral", "actual_history_days": 5, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "10": {"trend_continuation_score": 52.0, "trend_level": "neutral", "actual_history_days": 10, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
                "20": {"trend_continuation_score": 51.0, "trend_level": "neutral", "actual_history_days": 20, "history_coverage_ratio": 1.0, "trend_window_status": "ok"},
            },
        )
        # 标签逻辑不变
        assert result["multi_window_label"] == "multi_window_confirmed"
