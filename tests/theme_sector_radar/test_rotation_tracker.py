"""
轮动追踪器测试

测试 rotation_tracker 的功能。
"""

import pytest

from theme_sector_radar.history.rotation_tracker import calculate_rotation, RotationResult
from theme_sector_radar.models import (
    FocusLevel,
    RiskLevel,
    SectorScore,
    SectorType,
)


class TestRotationTracker:
    """测试轮动追踪器"""

    def _create_sector_score(self, name: str, score: float, **kwargs) -> SectorScore:
        """创建测试板块评分"""
        defaults = {
            "sector_id": f"BK{name}",
            "name": name,
            "type": SectorType.INDUSTRY,
            "score": score,
            "positive_score": score + 5,
            "risk_penalty": 5.0,
            "focus_level": FocusLevel.WATCH,
            "risk_level": RiskLevel.LOW,
        }
        defaults.update(kwargs)
        return SectorScore(**defaults)

    def test_rank_change_calculation(self):
        """测试 rank_change = previous_rank - current_rank"""
        # 当前: [A(排名1), B(排名2), C(排名3)]
        current = [
            self._create_sector_score("A", 90.0),
            self._create_sector_score("B", 85.0),
            self._create_sector_score("C", 80.0),
        ]

        # 历史: [B(排名1), A(排名2), C(排名3)]
        previous_data = {
            "industry_top": [
                {"name": "B", "score": 85.0, "risk_penalty": 5.0, "risk_level": "low"},
                {"name": "A", "score": 90.0, "risk_penalty": 5.0, "risk_level": "low"},
                {"name": "C", "score": 80.0, "risk_penalty": 5.0, "risk_level": "low"},
            ]
        }

        result = calculate_rotation(current, [], previous_data)

        # A: previous_rank=2, current_rank=1, rank_change=1
        a_detail = next(d for d in result.industry_details if d["name"] == "A")
        assert a_detail["rank_change"] == 1  # 2 - 1 = 1

        # B: previous_rank=1, current_rank=2, rank_change=-1
        b_detail = next(d for d in result.industry_details if d["name"] == "B")
        assert b_detail["rank_change"] == -1  # 1 - 2 = -1

    def test_rotation_uses_explicit_competition_ranks(self):
        current = [
            self._create_sector_score("B", 90.0, current_rank=1, rank_tied=True),
            self._create_sector_score("A", 90.0, current_rank=1, rank_tied=True),
        ]
        previous_data = {
            "industry_top": [
                {
                    "name": "A",
                    "score": 95.0,
                    "current_rank": 1,
                    "risk_penalty": 5.0,
                    "risk_level": "low",
                },
                {
                    "name": "B",
                    "score": 80.0,
                    "current_rank": 5,
                    "risk_penalty": 5.0,
                    "risk_level": "low",
                },
            ]
        }

        result = calculate_rotation(current, [], previous_data)
        by_name = {row["name"]: row for row in result.industry_details}

        assert by_name["B"]["current_rank"] == 1
        assert by_name["B"]["previous_rank"] == 5
        assert by_name["B"]["rank_change"] == 4
        assert by_name["B"]["rank_tied"] is True

    def test_score_change_calculation(self):
        """测试 score_change = current_score - previous_score"""
        current = [
            self._create_sector_score("A", 90.0),
        ]

        previous_data = {
            "industry_top": [
                {"name": "A", "score": 80.0, "risk_penalty": 5.0, "risk_level": "low"},
            ]
        }

        result = calculate_rotation(current, [], previous_data)

        a_detail = result.industry_details[0]
        assert a_detail["score_change"] == 10.0  # 90 - 80 = 10

    def test_new_entry_identification(self):
        """测试 new_entry 识别"""
        current = [
            self._create_sector_score("A", 90.0),
            self._create_sector_score("B", 85.0),  # 新板块
        ]

        previous_data = {
            "industry_top": [
                {"name": "A", "score": 80.0, "risk_penalty": 5.0, "risk_level": "low"},
            ]
        }

        result = calculate_rotation(current, [], previous_data)

        # B 是新板块
        b_detail = next(d for d in result.industry_details if d["name"] == "B")
        assert "new_entry" in b_detail["rotation_tags"]

    def test_dropped_out_identification(self):
        """测试 dropped_out 识别"""
        current = [
            self._create_sector_score("A", 90.0),
        ]

        previous_data = {
            "industry_top": [
                {"name": "A", "score": 80.0, "risk_penalty": 5.0, "risk_level": "low"},
                {"name": "C", "score": 75.0, "risk_penalty": 5.0, "risk_level": "low"},
            ]
        }

        result = calculate_rotation(current, [], previous_data)

        # C 被掉出
        assert "C" in result.industry_rotation["dropped_out"]

    def test_rising_fast_identification(self):
        """测试 rising_fast 识别"""
        current = [
            self._create_sector_score("A", 90.0),
        ]

        previous_data = {
            "industry_top": [
                {"name": "A", "score": 80.0, "risk_penalty": 5.0, "risk_level": "low"},
                # A 从排名2升到排名1，rank_change=1
                # 但 score_change=10 >= 8，所以是 rising_fast
            ]
        }

        result = calculate_rotation(current, [], previous_data)

        a_detail = result.industry_details[0]
        # score_change = 10 >= 8，所以是 rising_fast
        assert "rising_fast" in a_detail["rotation_tags"]

    def test_persistent_strength_identification(self):
        """测试 persistent_strength 识别"""
        current = [
            self._create_sector_score("A", 85.0),  # score >= 75
        ]

        previous_data = {
            "industry_top": [
                {"name": "A", "score": 80.0, "risk_penalty": 5.0, "risk_level": "low"},
            ]
        }

        result = calculate_rotation(current, [], previous_data)

        a_detail = result.industry_details[0]
        # 连续两期都在 Top N 且 score >= 75
        assert "persistent_strength" in a_detail["rotation_tags"]

    def test_risk_up_identification(self):
        """测试 risk_up 识别"""
        current = [
            self._create_sector_score("A", 90.0, risk_penalty=12.0),
        ]

        previous_data = {
            "industry_top": [
                {"name": "A", "score": 80.0, "risk_penalty": 5.0, "risk_level": "low"},
            ]
        }

        result = calculate_rotation(current, [], previous_data)

        a_detail = result.industry_details[0]
        # risk_penalty 从 5 增加到 12，增加 7 >= 5
        assert "risk_up" in a_detail["rotation_tags"]

    def test_industry_and_concept_separate(self):
        """测试 industry 和 concept 分开计算"""
        current_industry = [
            self._create_sector_score("A", 90.0),
        ]
        current_concept = [
            self._create_sector_score("X", 85.0, type=SectorType.CONCEPT),
        ]

        previous_data = {
            "industry_top": [
                {"name": "A", "score": 80.0, "risk_penalty": 5.0, "risk_level": "low"},
            ],
            "concept_top": [
                {"name": "X", "score": 75.0, "risk_penalty": 5.0, "risk_level": "low"},
            ],
        }

        result = calculate_rotation(current_industry, current_concept, previous_data)

        # industry 和 concept 应该分开
        assert len(result.industry_details) == 1
        assert len(result.concept_details) == 1
        assert result.industry_details[0]["name"] == "A"
        assert result.concept_details[0]["name"] == "X"

    def test_no_previous_data_marks_all_new(self):
        """测试没有历史数据时所有板块标记为新条目"""
        current = [
            self._create_sector_score("A", 90.0),
            self._create_sector_score("B", 85.0),
        ]

        result = calculate_rotation(current, [], None)

        # 所有板块都应该是 new_entry
        for detail in result.industry_details:
            assert "new_entry" in detail["rotation_tags"]

        assert result.comparison_status == "no_previous_data"
