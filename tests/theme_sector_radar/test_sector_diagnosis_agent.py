"""
板块诊断 Agent 测试

测试 sector_diagnosis_agent.py 模块的各项功能。
"""

import pytest

from theme_sector_radar.agents.sector_diagnosis import diagnose_sector


class TestSectorDiagnosis:
    """测试板块诊断 Agent"""

    def _create_mock_score_data(self, selection_level: str = "watch") -> dict:
        """创建模拟评分数据"""
        return {
            "sector_name": "test_sector",
            "sector_type": "industry",
            "sector_selection_score": 70.0,
            "selection_level": selection_level,
            "rotation_phase": "improving",
            "benchmark_mode": "sector_median",
            "score_breakdown": {
                "radar_score_component": 20.0,
                "momentum_component": 15.0,
                "relative_strength_component": 10.0,
                "persistence_component": 10.0,
                "drawdown_component": 7.0,
                "volatility_component": 4.0,
                "data_quality_component": 8.0,
                "risk_penalty": 5.0,
                "positive_score": 74.0,
                "final_score": 69.0,
            },
            "strength_reasons": ["日报雷达分较高"],
            "risk_reasons": [],
            "watch_points": ["观察后续表现"],
            "data_warnings": [],
            "radar_score": 70.0,
            "history_days": 5,
        }

    def test_basic_diagnosis(self):
        """测试基本诊断"""
        score_data = self._create_mock_score_data()
        result = diagnose_sector(score_data, "industry")
        assert result["sector_name"] == "test_sector"
        assert result["sector_type"] == "industry"
        assert result["selection_level"] == "watch"

    def test_strength_reasons(self):
        """测试强度原因"""
        score_data = self._create_mock_score_data()
        result = diagnose_sector(score_data)
        assert "strength_reasons" in result
        assert isinstance(result["strength_reasons"], list)

    def test_risk_reasons(self):
        """测试风险原因"""
        score_data = self._create_mock_score_data()
        result = diagnose_sector(score_data)
        assert "risk_reasons" in result
        assert isinstance(result["risk_reasons"], list)

    def test_watch_points(self):
        """测试观察要点"""
        score_data = self._create_mock_score_data()
        result = diagnose_sector(score_data)
        assert "watch_points" in result
        assert isinstance(result["watch_points"], list)

    def test_data_warnings(self):
        """测试数据警告"""
        score_data = self._create_mock_score_data()
        result = diagnose_sector(score_data)
        assert "data_warnings" in result
        assert isinstance(result["data_warnings"], list)

    def test_diagnosis_summary(self):
        """测试诊断摘要"""
        score_data = self._create_mock_score_data("strong_watch")
        result = diagnose_sector(score_data)
        assert "diagnosis_summary" in result
        assert len(result["diagnosis_summary"]) > 0

    def test_concept_sector(self):
        """测试概念板块"""
        score_data = self._create_mock_score_data()
        score_data["sector_type"] = "concept"
        score_data["data_warnings"] = ["概念板块缺少涨跌幅数据"]
        result = diagnose_sector(score_data, "concept")
        assert result["sector_type"] == "concept"
        assert any("涨跌幅" in w for w in result["data_warnings"])

    def test_strong_watch_level(self):
        """测试 strong_watch 等级"""
        score_data = self._create_mock_score_data("strong_watch")
        result = diagnose_sector(score_data)
        # Check that the summary contains appropriate text for strong_watch
        assert "优秀" in result["diagnosis_summary"] or "关注" in result["diagnosis_summary"]

    def test_avoid_level(self):
        """测试 avoid 等级"""
        score_data = self._create_mock_score_data("avoid")
        result = diagnose_sector(score_data)
        assert "回避" in result["diagnosis_summary"]

    def test_insufficient_history(self):
        """测试历史数据不足"""
        score_data = self._create_mock_score_data()
        score_data["history_days"] = 1
        result = diagnose_sector(score_data)
        assert any("历史数据不足" in w for w in result["data_warnings"])
