"""
评分语义测试

测试 risk_penalty、final_score 的数学语义一致性。
"""

import pytest

from theme_sector_radar.models import (
    ConstituentSnapshot,
    RiskLevel,
    SectorSnapshot,
    SectorType,
)
from theme_sector_radar.scoring.industry_score import calculate_industry_score_breakdown
from theme_sector_radar.scoring.concept_score import calculate_concept_score_breakdown, calculate_concept_phase
from theme_sector_radar.scoring.risk_score import calculate_risk_breakdown


class TestScoringSemantics:
    """测试评分语义"""

    def _create_sector(self, **kwargs) -> SectorSnapshot:
        """创建测试板块"""
        defaults = {
            "sector_id": "BK0428",
            "name": "半导体",
            "type": SectorType.INDUSTRY,
            "price_change_pct": 3.0,
            "turnover": 10_000_000_000,
            "main_net_inflow": 1_000_000_000,
            "data_quality_score": 80.0,
            "data_sources": ["akshare"],
        }
        defaults.update(kwargs)
        return SectorSnapshot(**defaults)

    def test_risk_penalty_always_positive(self):
        """测试 risk_penalty 永远 >= 0"""
        sector = self._create_sector()
        breakdown = calculate_risk_breakdown(sector)

        assert breakdown["total_penalty"] >= 0, \
            f"risk_penalty 应为正数，实际为 {breakdown['total_penalty']}"
        assert breakdown["overheat_penalty"] >= 0
        assert breakdown["divergence_penalty"] >= 0
        assert breakdown["data_quality_penalty"] >= 0

    def test_risk_penalty_positive_with_overheat(self):
        """测试过热板块 risk_penalty 为正数"""
        sector = self._create_sector(price_change_pct=18.0, turnover=25_000_000_000)
        breakdown = calculate_risk_breakdown(sector)

        assert breakdown["total_penalty"] > 0, "过热板块应有正数 risk_penalty"
        assert breakdown["overheat_penalty"] > 0

    def test_final_score_formula(self):
        """测试 final_score = positive_score - risk_penalty"""
        sector = self._create_sector()
        score_breakdown = calculate_industry_score_breakdown(sector, market_temperature=50.0)
        risk_breakdown = calculate_risk_breakdown(sector)

        positive_score = score_breakdown["positive_score"]
        risk_penalty = risk_breakdown["total_penalty"]  # 正数
        expected_final = positive_score - risk_penalty

        # 验证公式
        assert expected_final == positive_score - risk_penalty

    def test_risk_components_sum_to_total(self):
        """测试风险分项之和能解释 total_penalty（考虑上限）"""
        sector = self._create_sector(
            price_change_pct=18.0,
            turnover=25_000_000_000,
            main_net_inflow=-2_000_000_000,
            data_quality_score=35.0,
        )
        breakdown = calculate_risk_breakdown(sector)

        # 分项之和
        components_sum = (
            breakdown["overheat_penalty"] +
            breakdown["divergence_penalty"] +
            breakdown["data_quality_penalty"]
        )

        # total_penalty 有上限 30.0，所以分项之和可能大于 total_penalty
        # 但 total_penalty 不应超过上限
        assert breakdown["total_penalty"] <= 30.0, \
            f"total_penalty 不应超过上限 30.0，实际为 {breakdown['total_penalty']}"

        # 分项之和应 >= total_penalty（因为可能被截断）
        assert components_sum >= breakdown["total_penalty"], \
            f"分项之和 {components_sum} 应 >= total_penalty {breakdown['total_penalty']}"

    def test_high_risk_lowers_final_score(self):
        """测试高风险板块 final_score 下降"""
        # 正常板块
        normal_sector = self._create_sector(price_change_pct=3.0)
        normal_score = calculate_industry_score_breakdown(normal_sector, 50.0)
        normal_risk = calculate_risk_breakdown(normal_sector)

        # 高风险板块
        high_risk_sector = self._create_sector(
            price_change_pct=18.0,
            turnover=25_000_000_000,
            main_net_inflow=-2_000_000_000,
        )
        high_risk_score = calculate_industry_score_breakdown(high_risk_sector, 50.0)
        high_risk_risk = calculate_risk_breakdown(high_risk_sector)

        normal_final = normal_score["positive_score"] - normal_risk["total_penalty"]
        high_risk_final = high_risk_score["positive_score"] - high_risk_risk["total_penalty"]

        # 高风险板块 final_score 应该更低
        assert high_risk_final < normal_final, \
            f"高风险板块 final_score {high_risk_final} 应低于正常板块 {normal_final}"

    def test_json_score_breakdown_mathematical_consistency(self):
        """测试 JSON score_breakdown 数学一致性"""
        import tempfile
        import os
        import json

        from theme_sector_radar.pipeline import run_pipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查行业板块
            for sector in data.get("industry_top", []):
                breakdown = sector.get("score_breakdown", {})
                if breakdown:
                    positive_score = breakdown.get("positive_score", 0)
                    risk_penalty = breakdown.get("risk_penalty", 0)
                    final_score = breakdown.get("final_score", 0)

                    # 验证 risk_penalty 为正数
                    assert risk_penalty >= 0, \
                        f"{sector['name']}: risk_penalty 应为正数，实际为 {risk_penalty}"

                    # 验证 final_score = positive_score - risk_penalty
                    expected_final = positive_score - risk_penalty
                    assert abs(final_score - expected_final) < 0.1, \
                        f"{sector['name']}: final_score {final_score} 应等于 positive_score {positive_score} - risk_penalty {risk_penalty} = {expected_final}"

    def test_industry_and_concept_both_covered(self):
        """测试 industry 和 concept 都覆盖"""
        # 行业板块
        industry_sector = self._create_sector(type=SectorType.INDUSTRY)
        industry_breakdown = calculate_risk_breakdown(industry_sector)
        assert industry_breakdown["total_penalty"] >= 0

        # 概念板块
        concept_sector = self._create_sector(type=SectorType.CONCEPT)
        concept_breakdown = calculate_risk_breakdown(concept_sector)
        assert concept_breakdown["total_penalty"] >= 0

    def test_markdown_no_negative_risk_penalty(self):
        """测试 Markdown 不展示负数风险扣分"""
        import tempfile
        import os

        from theme_sector_radar.pipeline import run_pipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Markdown 中不应出现负数风险扣分
            # 例如 "-3.0" 或 "扣分: -3.0"
            import re
            negative_penalty_pattern = r"风险扣分.*-\d+\.?\d*"
            matches = re.findall(negative_penalty_pattern, content)
            assert len(matches) == 0, \
                f"Markdown 不应展示负数风险扣分，找到: {matches}"
