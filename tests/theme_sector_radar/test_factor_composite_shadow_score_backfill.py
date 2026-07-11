"""
Factor Composite Shadow Score 回填测试

覆盖：
- dry-run 不写文件
- write-copy 写副本不覆盖原文件
- force 写回原文件
- 已回填文件默认跳过
- 缺失 candidate 文件优雅降级
- forward return 匹配率统计正确
- candidate 原顺序保持不变
- final_score 不被修改
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from backfill_factor_composite_shadow_score import (
    load_top30_candidates,
    find_forward_return_file,
    load_forward_returns,
    is_already_backfilled,
    backfill_candidates,
    calc_forward_return_coverage,
    backfill_date,
)


# ============================================================
# Helper Functions
# ============================================================

def _make_candidate_file(
    path: Path,
    candidates: list[dict],
    include_composite: bool = False,
) -> None:
    """创建测试用的 top30_candidates.json。"""
    data = {
        "schema_version": "1.0",
        "as_of": "2026-07-10",
        "candidates": candidates,
    }
    if include_composite:
        for c in candidates:
            c["factor_composite_shadow_score"] = 50.0
            c["factor_composite_breakdown"] = {}
            c["factor_composite_tags"] = []

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _make_forward_return_file(path: Path, returns: dict[str, float]) -> None:
    """创建测试用的 forward_returns.json。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"returns": returns}, ensure_ascii=False),
        encoding="utf-8",
    )


# ============================================================
# Data Loading Tests
# ============================================================

class TestDataLoading:
    """测试数据加载。"""

    def test_load_top30_candidates_exists(self, tmp_path):
        """存在的文件应正确加载。"""
        path = tmp_path / "top30_candidates.json"
        _make_candidate_file(path, [{"code": "600001"}])

        result = load_top30_candidates(path)
        assert result is not None
        assert len(result["candidates"]) == 1

    def test_load_top30_candidates_missing(self, tmp_path):
        """不存在的文件应返回 None。"""
        result = load_top30_candidates(tmp_path / "nonexistent.json")
        assert result is None

    def test_find_forward_return_file(self, tmp_path):
        """应能找到 forward return 文件。"""
        date = "2026-07-10"
        # 测试不同命名
        (tmp_path / date).mkdir(parents=True, exist_ok=True)
        (tmp_path / date / f"{date}.json").write_text("{}", encoding="utf-8")
        result = find_forward_return_file(date, tmp_path)
        assert result is not None

        (tmp_path / date / f"{date}.json").unlink()
        (tmp_path / date / f"forward_returns_{date}.json").write_text("{}", encoding="utf-8")
        result = find_forward_return_file(date, tmp_path)
        assert result is not None

    def test_find_forward_return_file_missing(self, tmp_path):
        """不存在时应返回 None。"""
        result = find_forward_return_file("2026-07-10", tmp_path)
        assert result is None


# ============================================================
# Backfill Logic Tests
# ============================================================

class TestBackfillLogic:
    """测试回填逻辑。"""

    def test_is_already_backfilled_true(self):
        """已回填的文件应返回 True。"""
        data = {
            "candidates": [
                {"code": "600001", "factor_composite_shadow_score": 50.0}
            ]
        }
        assert is_already_backfilled(data) is True

    def test_is_already_backfilled_false(self):
        """未回填的文件应返回 False。"""
        data = {
            "candidates": [
                {"code": "600001", "final_score": 75.0}
            ]
        }
        assert is_already_backfilled(data) is False

    def test_backfill_candidates(self):
        """回填应添加 factor_snapshot 和 factor_composite_shadow_score。"""
        data = {
            "candidates": [
                {
                    "code": "600001",
                    "name": "测试股",
                    "final_score": 75.0,
                    "stock_trend_score": 70.0,
                    "sector_trend_score": 65.0,
                }
            ]
        }
        result = backfill_candidates(data)

        # 检查原数据未被修改
        assert "factor_snapshot" not in data["candidates"][0]

        # 检查回填结果
        c = result["candidates"][0]
        assert "factor_snapshot" in c
        assert "factor_composite_shadow_score" in c
        assert "factor_composite_breakdown" in c
        assert "factor_composite_tags" in c
        assert 0 <= c["factor_composite_shadow_score"] <= 100

    def test_backfill_preserves_order(self):
        """回填应保持 candidate 顺序。"""
        data = {
            "candidates": [
                {"code": "600001", "name": "A"},
                {"code": "600002", "name": "B"},
                {"code": "600003", "name": "C"},
            ]
        }
        result = backfill_candidates(data)
        codes = [c["code"] for c in result["candidates"]]
        assert codes == ["600001", "600002", "600003"]

    def test_backfill_preserves_final_score(self):
        """回填不应修改 final_score。"""
        data = {
            "candidates": [
                {"code": "600001", "final_score": 75.0}
            ]
        }
        result = backfill_candidates(data)
        assert result["candidates"][0]["final_score"] == 75.0


# ============================================================
# Forward Return Coverage Tests
# ============================================================

class TestForwardReturnCoverage:
    """测试 forward return 匹配率。"""

    def test_coverage_with_matching(self):
        """有匹配时应返回正确覆盖率。"""
        candidates = [{"code": "600001"}, {"code": "600002"}, {"code": "600003"}]
        forward_returns = {"600001": 0.05, "600002": -0.02, "600004": 0.03}

        result = calc_forward_return_coverage(candidates, forward_returns)
        assert result["has_forward_return"] is True
        assert result["matched_count"] == 2
        assert result["coverage_rate"] == pytest.approx(66.67, rel=0.01)

    def test_coverage_without_forward_returns(self):
        """没有 forward returns 时应返回 0。"""
        candidates = [{"code": "600001"}]
        result = calc_forward_return_coverage(candidates, None)
        assert result["has_forward_return"] is False
        assert result["coverage_rate"] == 0.0

    def test_coverage_empty_candidates(self):
        """空 candidates 应返回 0。"""
        result = calc_forward_return_coverage([], {"600001": 0.05})
        assert result["coverage_rate"] == 0.0


# ============================================================
# Backfill Date Tests
# ============================================================

class TestBackfillDate:
    """测试单天回填。"""

    def test_dry_run_no_files(self, tmp_path):
        """dry-run 不应写文件。"""
        candidate_dir = tmp_path / "agent_bridge" / "2026-07-10"
        _make_candidate_file(
            candidate_dir / "top30_candidates.json",
            [{"code": "600001", "final_score": 75.0}],
        )

        result = backfill_date(
            date="2026-07-10",
            candidate_root=tmp_path / "agent_bridge",
            forward_return_root=tmp_path / "forward_returns",
            output_root=tmp_path / "output",
            dry_run=True,
        )

        assert result["status"] == "dry_run"
        assert result["backfilled"] is True
        # 检查没有写文件
        assert not (tmp_path / "output" / "2026-07-10").exists()

    def test_write_copy(self, tmp_path):
        """write-copy 应写副本不覆盖原文件。"""
        candidate_dir = tmp_path / "agent_bridge" / "2026-07-10"
        original_path = candidate_dir / "top30_candidates.json"
        _make_candidate_file(
            original_path,
            [{"code": "600001", "final_score": 75.0}],
        )
        original_content = original_path.read_text(encoding="utf-8")

        result = backfill_date(
            date="2026-07-10",
            candidate_root=tmp_path / "agent_bridge",
            forward_return_root=tmp_path / "forward_returns",
            output_root=tmp_path / "output",
            write_copy=True,
        )

        assert result["status"] == "processed"
        # 检查原文件未被修改
        assert original_path.read_text(encoding="utf-8") == original_content
        # 检查副本已创建
        copy_path = tmp_path / "output" / "2026-07-10" / "top30_candidates.factor_backfilled.json"
        assert copy_path.exists()
        copy_data = json.loads(copy_path.read_text(encoding="utf-8"))
        assert "factor_composite_shadow_score" in copy_data["candidates"][0]

    def test_force_overwrite(self, tmp_path):
        """force 应写回原文件。"""
        candidate_dir = tmp_path / "agent_bridge" / "2026-07-10"
        original_path = candidate_dir / "top30_candidates.json"
        _make_candidate_file(
            original_path,
            [{"code": "600001", "final_score": 75.0}],
        )

        result = backfill_date(
            date="2026-07-10",
            candidate_root=tmp_path / "agent_bridge",
            forward_return_root=tmp_path / "forward_returns",
            output_root=tmp_path / "output",
            force=True,
        )

        assert result["status"] == "processed"
        # 检查原文件已被修改
        modified_data = json.loads(original_path.read_text(encoding="utf-8"))
        assert "factor_composite_shadow_score" in modified_data["candidates"][0]

    def test_already_backfilled_skip(self, tmp_path):
        """已回填文件默认应跳过。"""
        candidate_dir = tmp_path / "agent_bridge" / "2026-07-10"
        _make_candidate_file(
            candidate_dir / "top30_candidates.json",
            [{"code": "600001", "final_score": 75.0}],
            include_composite=True,
        )

        result = backfill_date(
            date="2026-07-10",
            candidate_root=tmp_path / "agent_bridge",
            forward_return_root=tmp_path / "forward_returns",
            output_root=tmp_path / "output",
        )

        assert result["status"] == "already_backfilled"

    def test_missing_candidate_file(self, tmp_path):
        """缺失 candidate 文件应优雅降级。"""
        result = backfill_date(
            date="2026-07-10",
            candidate_root=tmp_path / "agent_bridge",
            forward_return_root=tmp_path / "forward_returns",
            output_root=tmp_path / "output",
        )

        assert result["status"] == "missing_candidate_file"
        assert result["candidate_count"] == 0

    def test_no_candidates(self, tmp_path):
        """空 candidates 应正确处理。"""
        candidate_dir = tmp_path / "agent_bridge" / "2026-07-10"
        _make_candidate_file(
            candidate_dir / "top30_candidates.json",
            [],
        )

        result = backfill_date(
            date="2026-07-10",
            candidate_root=tmp_path / "agent_bridge",
            forward_return_root=tmp_path / "forward_returns",
            output_root=tmp_path / "output",
        )

        assert result["status"] == "no_candidates"

    def test_forward_return_coverage(self, tmp_path):
        """应正确计算 forward return 匹配率。"""
        candidate_dir = tmp_path / "agent_bridge" / "2026-07-10"
        _make_candidate_file(
            candidate_dir / "top30_candidates.json",
            [{"code": "600001"}, {"code": "600002"}],
        )
        _make_forward_return_file(
            tmp_path / "forward_returns" / "2026-07-10" / "2026-07-10.json",
            {"600001": 0.05},
        )

        result = backfill_date(
            date="2026-07-10",
            candidate_root=tmp_path / "agent_bridge",
            forward_return_root=tmp_path / "forward_returns",
            output_root=tmp_path / "output",
        )

        assert result["forward_return_coverage"] == 50.0
        assert "matched 1/2" in result["forward_return_status"]


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """集成测试。"""

    def test_end_to_end_write_copy(self, tmp_path):
        """端到端测试：write-copy 模式。"""
        # 创建测试数据
        for date in ["2026-07-01", "2026-07-02"]:
            _make_candidate_file(
                tmp_path / "agent_bridge" / date / "top30_candidates.json",
                [
                    {"code": "600001", "final_score": 75.0, "stock_trend_score": 70.0},
                    {"code": "600002", "final_score": 70.0, "stock_trend_score": 65.0},
                ],
            )
            _make_forward_return_file(
                tmp_path / "forward_returns" / date / f"{date}.json",
                {"600001": 0.05, "600002": -0.02},
            )

        # 运行回填
        from backfill_factor_composite_shadow_score import backfill_date

        for date in ["2026-07-01", "2026-07-02"]:
            result = backfill_date(
                date=date,
                candidate_root=tmp_path / "agent_bridge",
                forward_return_root=tmp_path / "forward_returns",
                output_root=tmp_path / "output",
                write_copy=True,
            )
            assert result["status"] == "processed"

        # 验证输出
        for date in ["2026-07-01", "2026-07-02"]:
            output_path = tmp_path / "output" / date / "top30_candidates.factor_backfilled.json"
            assert output_path.exists()
            data = json.loads(output_path.read_text(encoding="utf-8"))
            assert len(data["candidates"]) == 2
            for c in data["candidates"]:
                assert "factor_composite_shadow_score" in c
                assert "factor_snapshot" in c
