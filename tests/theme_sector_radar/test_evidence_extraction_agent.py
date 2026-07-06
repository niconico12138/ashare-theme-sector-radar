"""
EvidenceExtractionAgent 测试

测试证据提取 Agent。
"""

import pytest

from theme_sector_radar.agents.sector_research.evidence_extraction_agent import EvidenceExtractionAgent
from theme_sector_radar.agents.sector_research.opinion import LAYER_DATA_EVIDENCE


class TestEvidenceExtractionAgent:
    """测试 EvidenceExtractionAgent"""

    def test_analyze(self):
        """测试 analyze 方法"""
        agent = EvidenceExtractionAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={
                "trend_continuation_score": 65.0,
                "trend_level": "trend_confirmed",
                "short_term_burst_score": 55.0,
                "data_quality_score": 0.8,
                "risk_level": "risk_low",
                "history_coverage_ratio": 1.0,
                "radar_score": 70.0,
                "benchmark_mode": "market_benchmark",
                "opportunity_score": 0.6,
                "evidence_score": 0.7,
                "risk_control_score": 0.8,
                "confidence_score": 0.7,
            },
            consensus_data={
                "multi_window_label": "multi_window_confirmed",
            },
        )

        assert result.agent_id == "evidence_extraction"
        assert result.layer == LAYER_DATA_EVIDENCE
        assert result.label in ["strong", "moderate", "weak"]
        assert isinstance(result.score, (int, float))
        assert result.confidence > 0
        assert len(result.evidence) > 0
