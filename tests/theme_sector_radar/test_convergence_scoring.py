"""
综合排名系统测试

覆盖：
- 板块综合分 (board_composite_score)
- Agent趋势/短线分组 (agent_trend_short_split)
- 综合排名分 (convergence_scoring)
"""

import pytest


# ============================================================
# 板块综合分测试
# ============================================================

class TestBoardCompositeScore:
    """测试板块综合分计算"""

    def test_convergence_regime(self):
        """双强共振 → regime=共振, bonus=+10"""
        from theme_sector_radar.scoring.board_composite_score import compute_board_score
        bs, regime, bonus = compute_board_score(70, 70)
        assert regime == "共振"
        assert bonus == 10.0
        assert bs > 60

    def test_trend_only_regime(self):
        """趋势强+短线弱 → regime=趋势独行, bonus=-5"""
        from theme_sector_radar.scoring.board_composite_score import compute_board_score
        bs, regime, bonus = compute_board_score(70, 30)
        assert regime == "趋势独行"
        assert bonus == -5.0

    def test_burst_only_regime(self):
        """短线强+趋势弱 → regime=一日游, bonus=-5"""
        from theme_sector_radar.scoring.board_composite_score import compute_board_score
        bs, regime, bonus = compute_board_score(30, 70)
        assert regime == "一日游"
        assert bonus == -5.0

    def test_weak_regime(self):
        """双弱 → regime=回避"""
        from theme_sector_radar.scoring.board_composite_score import compute_board_score
        bs, regime, bonus = compute_board_score(30, 30)
        assert regime == "回避"
        assert bonus == 0.0

    def test_board_score_formula(self):
        """board_score = trend×0.55 + burst×0.35 + bonus×0.10×10"""
        from theme_sector_radar.scoring.board_composite_score import compute_board_score
        bs, _, _ = compute_board_score(60, 50)
        # 共振? 60<65 → no bonus
        expected = 60 * 0.55 + 50 * 0.35 + 0 * 1.0
        assert bs == pytest.approx(expected, abs=0.1)

    def test_rank_sectors(self):
        """排序应正确"""
        from theme_sector_radar.scoring.board_composite_score import rank_sectors_by_board_score
        sectors = [
            {"name": "A", "trend_score": 30, "burst_score": 30},
            {"name": "B", "trend_score": 70, "burst_score": 70},
            {"name": "C", "trend_score": 50, "burst_score": 50},
        ]
        ranked = rank_sectors_by_board_score(sectors)
        assert ranked[0]["name"] == "B"
        assert ranked[0]["board_rank"] == 1
        assert ranked[2]["name"] == "A"


# ============================================================
# Agent 趋势/短线分组测试
# ============================================================

class TestAgentTrendShortSplit:
    """测试 Agent 趋势/短线分组打分"""

    def _make_agent(self, agent_id, signal, confidence, risk_level="low"):
        return {
            "agent_id": agent_id,
            "signal": signal,
            "confidence": confidence,
            "risk_level": risk_level,
        }

    def test_all_bullish(self):
        """全部看多 → 两组都高分"""
        from theme_sector_radar.scoring.agent_trend_short_split import compute_trend_short_scores
        agents = [
            self._make_agent("warren_buffett", "bullish", 80),
            self._make_agent("china_youzi", "bullish", 75),
            self._make_agent("northbound_flow", "bullish", 70),
            self._make_agent("technical_analyst", "bullish", 65),
            self._make_agent("risk_control_agent", "neutral", 50),
        ]
        result = compute_trend_short_scores(agents)
        assert result["trend_agent_score"] > 60
        assert result["short_agent_score"] > 60

    def test_all_bearish_high_risk(self):
        """全部看空+高风险 → 两组都低分"""
        from theme_sector_radar.scoring.agent_trend_short_split import compute_trend_short_scores
        agents = [
            self._make_agent("warren_buffett", "bearish", 80, "high"),
            self._make_agent("china_youzi", "bearish", 75, "high"),
            self._make_agent("risk_control_agent", "bearish", 80, "high"),
        ]
        result = compute_trend_short_scores(agents)
        assert result["trend_agent_score"] < 40
        assert result["short_agent_score"] < 40
        assert result["risk_penalty"] > 0

    def test_trend_bullish_short_bearish(self):
        """趋势多+短线空 → 趋势分高、短线分低"""
        from theme_sector_radar.scoring.agent_trend_short_split import compute_trend_short_scores
        agents = [
            self._make_agent("warren_buffett", "bullish", 80),
            self._make_agent("ben_graham", "bullish", 70),
            self._make_agent("china_youzi", "bearish", 75),
            self._make_agent("northbound_flow", "bearish", 65),
            self._make_agent("technical_analyst", "bullish", 60),
        ]
        result = compute_trend_short_scores(agents)
        assert result["trend_agent_score"] > 55
        assert result["short_agent_score"] < 50

    def test_empty_agents(self):
        """空数据 → 默认50分"""
        from theme_sector_radar.scoring.agent_trend_short_split import compute_trend_short_scores
        result = compute_trend_short_scores([])
        assert result["trend_agent_score"] == 50.0
        assert result["short_agent_score"] == 50.0


# ============================================================
# 综合排名分测试
# ============================================================

class TestConvergenceScoring:
    """测试综合排名分计算"""

    def test_double_convergence(self):
        """双强确认 → bonus=+10"""
        from theme_sector_radar.convergence_scoring import compute_final_score
        r = compute_final_score(
            board_trend_score=70, board_burst_score=65,
            trend_agent_score=72, short_agent_score=68,
            quant_score=78, risk_penalty=0,
        )
        assert r["convergence_bonus"] == 10.0
        assert r["convergence_label"] == "双重确认"
        assert r["final_score"] > 60

    def test_trend_only(self):
        """趋势好+短线弱 → bonus=-5"""
        from theme_sector_radar.convergence_scoring import compute_final_score
        r = compute_final_score(
            board_trend_score=70, board_burst_score=40,
            trend_agent_score=65, short_agent_score=35,
            quant_score=60, risk_penalty=0,
        )
        assert r["convergence_bonus"] == -5.0
        assert r["convergence_label"] == "趋势好但短线未到"

    def test_short_pulse(self):
        """短线脉冲+趋势弱 → bonus=-3"""
        from theme_sector_radar.convergence_scoring import compute_final_score
        r = compute_final_score(
            board_trend_score=35, board_burst_score=70,
            trend_agent_score=35, short_agent_score=65,
            quant_score=55, risk_penalty=0,
        )
        assert r["convergence_bonus"] == -3.0
        assert r["convergence_label"] == "短线脉冲但趋势弱"

    def test_risk_penalty(self):
        """风险扣分应减少综合分"""
        from theme_sector_radar.convergence_scoring import compute_final_score
        r1 = compute_final_score(board_trend_score=70, board_burst_score=65,
                                  trend_agent_score=72, short_agent_score=68,
                                  quant_score=78, risk_penalty=0)
        r2 = compute_final_score(board_trend_score=70, board_burst_score=65,
                                  trend_agent_score=72, short_agent_score=68,
                                  quant_score=78, risk_penalty=8)
        assert r2["final_score"] < r1["final_score"]
        assert r2["risk_penalty"] == 8

    def test_rank_stocks(self):
        """排序应正确"""
        from theme_sector_radar.convergence_scoring import rank_stocks_by_final_score
        stocks = [
            {"code": "A", "board_trend_score": 30, "board_burst_score": 30,
             "trend_agent_score": 30, "short_agent_score": 30, "quant_score": 30, "risk_penalty": 0},
            {"code": "B", "board_trend_score": 70, "board_burst_score": 65,
             "trend_agent_score": 72, "short_agent_score": 68, "quant_score": 78, "risk_penalty": 0},
        ]
        ranked = rank_stocks_by_final_score(stocks)
        assert ranked[0]["code"] == "B"
        assert ranked[0]["rank"] == 1
        assert ranked[0]["final_score"] > ranked[1]["final_score"]

    def test_score_formula(self):
        """验证公式正确"""
        from theme_sector_radar.convergence_scoring import compute_final_score
        r = compute_final_score(
            board_trend_score=80, board_burst_score=60,
            trend_agent_score=70, short_agent_score=50,
            quant_score=65, risk_penalty=0,
        )
        # trend_component = 80×0.20 + 70×0.15 = 16+10.5 = 26.5
        # short_component = 60×0.20 + 50×0.15 = 12+7.5 = 19.5
        # quant_component = 65×0.30 = 19.5
        # convergence: trend≥60 but short<40? No, short=50. → 0
        expected = 26.5 + 19.5 + 19.5 + 0
        assert r["final_score"] == pytest.approx(expected, abs=0.1)
