"""
Signal Profile 测试

测试 Agent 信号特征分类。
"""

import pytest

from theme_sector_radar.agents.sector_research.opinion import (
    AGENT_SIGNAL_PROFILES,
    SIGNAL_PROFILE_DESCRIPTIONS,
    SIGNAL_PROFILE_BROAD,
    SIGNAL_PROFILE_SPARSE_HP,
    SIGNAL_PROFILE_LOW_INFO,
    SIGNAL_PROFILE_DEFENSIVE,
)


class TestSignalProfile:
    """测试 Signal Profile"""

    def test_all_agents_have_profiles(self):
        """测试所有管线中活跃的 Agent 都有 signal_profile"""
        expected_agents = [
            "technical_trend", "short_term_heat", "rotation_analysis",
            "risk_control", "data_quality", "market_context",
            "narrative", "persistence_strength", "catalyst_event",
        ]
        for agent_id in expected_agents:
            assert agent_id in AGENT_SIGNAL_PROFILES, f"Agent {agent_id} missing signal_profile"

    def test_persistence_strength_is_sparse_hp(self):
        """测试 persistence_strength 是 sparse_high_precision"""
        assert AGENT_SIGNAL_PROFILES["persistence_strength"] == SIGNAL_PROFILE_SPARSE_HP

    def test_narrative_is_low_information(self):
        """测试 narrative 是 low_information"""
        assert AGENT_SIGNAL_PROFILES["narrative"] == SIGNAL_PROFILE_LOW_INFO

    def test_risk_control_is_defensive(self):
        """测试 risk_control 是 defensive_filter"""
        assert AGENT_SIGNAL_PROFILES["risk_control"] == SIGNAL_PROFILE_DEFENSIVE

    def test_data_quality_is_defensive(self):
        """测试 data_quality 是 defensive_filter"""
        assert AGENT_SIGNAL_PROFILES["data_quality"] == SIGNAL_PROFILE_DEFENSIVE

    def test_short_term_heat_is_broad(self):
        """测试 short_term_heat 是 broad_signal"""
        assert AGENT_SIGNAL_PROFILES["short_term_heat"] == SIGNAL_PROFILE_BROAD

    def test_all_profiles_have_descriptions(self):
        """测试所有 profile 都有说明"""
        for profile in [SIGNAL_PROFILE_BROAD, SIGNAL_PROFILE_SPARSE_HP,
                        SIGNAL_PROFILE_LOW_INFO, SIGNAL_PROFILE_DEFENSIVE]:
            assert profile in SIGNAL_PROFILE_DESCRIPTIONS

    def test_reliability_report_includes_profile(self):
        """测试 reliability 报告包含 signal_profile"""
        from theme_sector_radar.reports.agent_reliability_report import generate_agent_reliability_report

        report_data = {
            "start_date": "2026-06-01",
            "end_date": "2026-06-29",
            "total_samples": 100,
            "agents": {
                "persistence_strength": {
                    "layer": "L2_specialized",
                    "signal_profile": "sparse_high_precision",
                    "sample_count": 6,
                    "vote_distribution": {"positive": 6, "neutral": 0, "negative": 0},
                    "reliability_score": 0.30,
                    "reliability_label": "low_reliability",
                    "diagnosis": "positive vote has high forward returns",
                },
            },
        }

        md = generate_agent_reliability_report(report_data)
        assert "sparse_high_precision" in md
        assert "Signal Profile" in md
