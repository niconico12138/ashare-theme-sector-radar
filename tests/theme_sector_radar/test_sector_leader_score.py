"""Tests for sector_leader_score module."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "theme_sector_radar" / "scoring"))

from sector_leader_score import compute_sector_leader_scores


class TestComputeSectorLeaderScores:
    """Test compute_sector_leader_scores function."""

    def test_single_stock_sector(self):
        """Single stock in sector gets unknown role."""
        candidates = [
            {"code": "000001", "name": "测试A", "boards": ["半导体"], "change_pct": 5.0, "amount": 50_000_000},
        ]
        result = compute_sector_leader_scores(candidates)
        assert len(result) == 1
        assert result[0]["sector_role"] == "unknown"
        assert result[0]["sector_leader_score"] == 50.0
        assert "single_stock_in_sector" in result[0]["leader_tags"]

    def test_leader高于_follower(self):
        """Leader should have higher leader_score than follower in same sector."""
        candidates = [
            {"code": "000001", "name": "龙头A", "boards": ["半导体"], "change_pct": 8.0, "amount": 100_000_000, "stock_short_score": 80, "stock_trend_score": 75, "final_score": 80},
            {"code": "000002", "name": "中军B", "boards": ["半导体"], "change_pct": 4.0, "amount": 50_000_000, "stock_short_score": 60, "stock_trend_score": 65, "final_score": 60},
            {"code": "000003", "name": "跟风C", "boards": ["半导体"], "change_pct": 1.0, "amount": 20_000_000, "stock_short_score": 40, "stock_trend_score": 45, "final_score": 40},
            {"code": "000004", "name": "落后D", "boards": ["半导体"], "change_pct": -2.0, "amount": 10_000_000, "stock_short_score": 30, "stock_trend_score": 30, "final_score": 25},
        ]
        result = compute_sector_leader_scores(candidates)
        by_code = {r["code"]: r for r in result}

        # Leader should have highest score
        assert by_code["000001"]["sector_leader_score"] > by_code["000003"]["sector_leader_score"]
        assert by_code["000001"]["sector_leader_score"] > by_code["000004"]["sector_leader_score"]

        # Leader should have leader role
        assert by_code["000001"]["sector_role"] == "leader"

        # Laggard should have laggard role
        assert by_code["000004"]["sector_role"] == "laggard"

    def test_multiple_sectors(self):
        """Different sectors are scored independently."""
        candidates = [
            {"code": "000001", "name": "A1", "boards": ["半导体"], "change_pct": 8.0, "amount": 100_000_000},
            {"code": "000002", "name": "A2", "boards": ["半导体"], "change_pct": 2.0, "amount": 30_000_000},
            {"code": "000003", "name": "B1", "boards": ["新能源"], "change_pct": 8.0, "amount": 100_000_000},
            {"code": "000004", "name": "B2", "boards": ["新能源"], "change_pct": 2.0, "amount": 30_000_000},
        ]
        result = compute_sector_leader_scores(candidates)
        by_code = {r["code"]: r for r in result}

        # Leaders in both sectors
        assert by_code["000001"]["sector_role"] == "leader"
        assert by_code["000003"]["sector_role"] == "leader"

    def test_returns_same_list(self):
        """Function should modify and return the same list."""
        candidates = [
            {"code": "000001", "name": "A", "boards": ["半导体"], "change_pct": 5.0, "amount": 50_000_000},
        ]
        result = compute_sector_leader_scores(candidates)
        assert result is candidates

    def test_empty_input(self):
        """Empty input should return empty list."""
        result = compute_sector_leader_scores([])
        assert result == []

    def test_all_fields_present(self):
        """Each result should have sector_leader_score, sector_role, leader_tags."""
        candidates = [
            {"code": "000001", "name": "A", "boards": ["板块1"], "change_pct": 3.0, "amount": 50_000_000},
            {"code": "000002", "name": "B", "boards": ["板块1"], "change_pct": 1.0, "amount": 20_000_000},
        ]
        result = compute_sector_leader_scores(candidates)
        for r in result:
            assert "sector_leader_score" in r
            assert "sector_role" in r
            assert "leader_tags" in r
            assert isinstance(r["leader_tags"], list)

    def test_fallback_sector_name(self):
        """Uses sector_name when boards is empty."""
        candidates = [
            {"code": "000001", "name": "A", "sector_name": "医药", "change_pct": 5.0, "amount": 50_000_000},
            {"code": "000002", "name": "B", "sector_name": "医药", "change_pct": 2.0, "amount": 30_000_000},
        ]
        result = compute_sector_leader_scores(candidates)
        by_code = {r["code"]: r for r in result}
        assert by_code["000001"]["sector_leader_score"] > by_code["000002"]["sector_leader_score"]
