"""
板块综合评分 Agent 测试

测试 sector_scoring_agent.py 模块的各项功能。
"""

import pytest

from theme_sector_radar.agents.sector_scoring import calculate_sector_scores
from theme_sector_radar.models import AgentStatus, SectorScore, SectorType


class TestSectorScoringAgent:
    """测试板块综合评分 Agent"""

    def _create_mock_sector(self, name: str, score: float = 50.0) -> SectorScore:
        """创建模拟板块数据"""
        return SectorScore(
            sector_id=f"test_{name}",
            name=name,
            type=SectorType.INDUSTRY,
            score=score,
            positive_score=score,
            risk_penalty=0.0,
            data_quality_score=60.0,
        )

    def test_empty_sectors(self):
        """测试空板块列表"""
        result = calculate_sector_scores(
            radar_sectors=[],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        assert result.status == AgentStatus.OK
        assert result.data["scores"] == []

    def test_single_sector(self):
        """测试单个板块"""
        sector = self._create_mock_sector("test_sector", 70.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        assert result.status == AgentStatus.OK
        assert len(result.data["scores"]) == 1
        assert result.data["scores"][0]["sector_name"] == "test_sector"

    def test_multiple_sectors(self):
        """测试多个板块"""
        sectors = [
            self._create_mock_sector("sector_a", 80.0),
            self._create_mock_sector("sector_b", 60.0),
            self._create_mock_sector("sector_c", 40.0),
        ]
        result = calculate_sector_scores(
            radar_sectors=sectors,
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        assert result.status == AgentStatus.OK
        assert len(result.data["scores"]) == 3
        # 验证按分数排序
        scores = [s["sector_selection_score"] for s in result.data["scores"]]
        assert scores == sorted(scores, reverse=True)

    def test_with_history_data(self):
        """测试有历史数据"""
        sector = self._create_mock_sector("test_sector", 70.0)
        history_data = {
            "test_sector": {
                "recent_returns": [2.0, 1.0, 0.5],
                "total_return": 3.5,
                "positive_days": 2,
                "total_days": 3,
                "max_drawdown": -0.02,
                "volatility": 1.0,
                "history_days": 3,
            }
        }
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data=history_data,
            sector_type=SectorType.INDUSTRY,
        )
        assert result.status == AgentStatus.OK
        assert len(result.data["scores"]) == 1
        assert result.data["scores"][0]["history_days"] == 3

    def test_score_breakdown(self):
        """测试评分拆解"""
        sector = self._create_mock_sector("test_sector", 70.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        score_data = result.data["scores"][0]
        assert "score_breakdown" in score_data
        assert "radar_score_component" in score_data["score_breakdown"]
        assert "momentum_component" in score_data["score_breakdown"]
        assert "relative_strength_component" in score_data["score_breakdown"]
        assert "persistence_component" in score_data["score_breakdown"]
        assert "drawdown_component" in score_data["score_breakdown"]
        assert "volatility_component" in score_data["score_breakdown"]
        assert "data_quality_component" in score_data["score_breakdown"]
        assert "risk_penalty" in score_data["score_breakdown"]

    def test_selection_level(self):
        """测试选择等级"""
        sector = self._create_mock_sector("test_sector", 90.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        score_data = result.data["scores"][0]
        assert "selection_level" in score_data
        assert score_data["selection_level"] in [
            "strong_watch",
            "watch",
            "neutral",
            "cooling",
            "avoid",
        ]

    def test_rotation_phase(self):
        """测试轮动阶段"""
        sector = self._create_mock_sector("test_sector", 70.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        score_data = result.data["scores"][0]
        assert "rotation_phase" in score_data
        assert score_data["rotation_phase"] in [
            "leading",
            "improving",
            "weakening",
            "lagging",
        ]

    def test_diagnostic_info(self):
        """测试诊断信息"""
        sector = self._create_mock_sector("test_sector", 70.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        score_data = result.data["scores"][0]
        assert "strength_reasons" in score_data
        assert "risk_reasons" in score_data
        assert "watch_points" in score_data
        assert "data_warnings" in score_data
        assert isinstance(score_data["strength_reasons"], list)
        assert isinstance(score_data["risk_reasons"], list)
        assert isinstance(score_data["watch_points"], list)
        assert isinstance(score_data["data_warnings"], list)
