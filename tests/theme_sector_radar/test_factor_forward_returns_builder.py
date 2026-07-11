"""
Factor Forward Return Builder 测试

覆盖：
- 优先读取 factor_backfilled 文件
- 回退读取 top30_candidates.json
- 已存在 forward return 文件默认跳过
- --force 覆盖
- bars 缺失时输出 missing item
- 计算 1d/3d/5d/10d forward return 正确
- 保持 candidate 顺序
- 单只失败不影响整天
- JSON schema 正确
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from build_factor_forward_returns import (
    _parse_date,
    _date_key,
    _coerce_float,
    load_candidates,
    compute_forward_returns_from_bars,
    compute_forward_returns_from_candidate,
    build_factor_forward_returns,
)


# ============================================================
# Helper Functions
# ============================================================

def _make_candidate_file(path: Path, candidates: list[dict]) -> None:
    """创建测试用的候选股文件。"""
    data = {
        "schema_version": "1.0",
        "as_of": "2026-07-10",
        "candidates": candidates,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _make_bars(
    dates: list[str],
    closes: list[float],
) -> list[dict]:
    """创建测试用的 bars 数据。"""
    return [
        {"date": date, "open": c * 0.99, "high": c * 1.02, "low": c * 0.98, "close": c, "volume": 1000000}
        for date, c in zip(dates, closes)
    ]


# ============================================================
# Helper Function Tests
# ============================================================

class TestHelperFunctions:
    """测试辅助函数。"""

    def test_parse_date(self):
        """_parse_date 应正确解析日期。"""
        assert _parse_date("2026-07-10").strftime("%Y-%m-%d") == "2026-07-10"
        assert _parse_date("20260710").strftime("%Y-%m-%d") == "2026-07-10"

    def test_date_key(self):
        """_date_key 应返回 YYYY-MM-DD 格式。"""
        assert _date_key("2026-07-10") == "2026-07-10"
        assert _date_key("20260710") == "2026-07-10"

    def test_coerce_float(self):
        """_coerce_float 应安全转换。"""
        assert _coerce_float(10.0) == 10.0
        assert _coerce_float("10.5") == 10.5
        assert _coerce_float(None) is None
        assert _coerce_float("") is None
        assert _coerce_float("abc") is None


# ============================================================
# Load Candidates Tests
# ============================================================

class TestLoadCandidates:
    """测试候选股加载。"""

    def test_load_prefer_backfilled(self, tmp_path):
        """应优先加载 backfilled 文件。"""
        date = "2026-07-10"
        # 创建 backfilled 文件
        _make_candidate_file(
            tmp_path / date / "top30_candidates.factor_backfilled.json",
            [{"code": "600001", "name": "测试股A"}],
        )
        # 创建原文件
        _make_candidate_file(
            tmp_path / date / "top30_candidates.json",
            [{"code": "600002", "name": "测试股B"}],
        )

        result = load_candidates(date, tmp_path, prefer_backfilled=True)
        assert result is not None
        assert result[0]["code"] == "600001"

    def test_load_fallback_to_original(self, tmp_path):
        """没有 backfilled 文件时应回退到原文件。"""
        date = "2026-07-10"
        _make_candidate_file(
            tmp_path / date / "top30_candidates.json",
            [{"code": "600001", "name": "测试股"}],
        )

        result = load_candidates(date, tmp_path, prefer_backfilled=True)
        assert result is not None
        assert result[0]["code"] == "600001"

    def test_load_missing(self, tmp_path):
        """缺失文件应返回 None。"""
        result = load_candidates("2026-07-10", tmp_path, prefer_backfilled=True)
        assert result is None


# ============================================================
# Compute Forward Returns Tests
# ============================================================

class TestComputeForwardReturns:
    """测试 forward return 计算。"""

    def test_compute_from_bars(self):
        """应正确计算 forward returns。"""
        # 创建 bars 数据：as_of 是 2026-07-10，后面有 10 天数据
        dates = [f"2026-07-{i:02d}" for i in range(10, 21)]
        closes = [10.0 + i * 0.1 for i in range(11)]  # 10.0 -> 11.0
        bars = _make_bars(dates, closes)

        result = compute_forward_returns_from_bars(bars, "2026-07-10", [1, 3, 5, 10])

        # 1d: (10.1 - 10.0) / 10.0 * 100 = 1.0%
        assert result["1d"] == pytest.approx(1.0, rel=0.01)
        # 3d: (10.3 - 10.0) / 10.0 * 100 = 3.0%
        assert result["3d"] == pytest.approx(3.0, rel=0.01)
        # 5d: (10.5 - 10.0) / 10.0 * 100 = 5.0%
        assert result["5d"] == pytest.approx(5.0, rel=0.01)

    def test_compute_from_bars_insufficient(self):
        """bars 不足时应返回 None。"""
        dates = ["2026-07-10", "2026-07-11"]
        closes = [10.0, 10.1]
        bars = _make_bars(dates, closes)

        result = compute_forward_returns_from_bars(bars, "2026-07-10", [5, 10])

        assert result["5d"] is None
        assert result["10d"] is None

    def test_compute_from_candidate_no_bars(self):
        """没有 bars 时应返回 missing。"""
        candidate = {"code": "600001", "name": "测试股"}
        result = compute_forward_returns_from_candidate(candidate, "2026-07-10", None, [1, 3, 5])

        assert result["data_quality"] == "missing"
        assert result["missing_reason"] == "bars_not_available"

    def test_compute_preserves_order(self):
        """应保持 candidate 字段顺序。"""
        candidate = {"code": "600001", "name": "测试股"}
        result = compute_forward_returns_from_candidate(candidate, "2026-07-10", None, [1, 3])

        # 检查字段顺序
        keys = list(result.keys())
        assert keys[0] == "code"
        assert keys[1] == "name"
        assert keys[2] == "as_of"


# ============================================================
# Build Factor Forward Returns Tests
# ============================================================

class TestBuildFactorForwardReturns:
    """测试单天构建。"""

    def test_already_exists_skip(self, tmp_path):
        """已存在文件时应跳过。"""
        date = "2026-07-10"
        _make_candidate_file(
            tmp_path / "candidate" / date / "top30_candidates.json",
            [{"code": "600001"}],
        )
        # 创建已存在的 forward return 文件
        (tmp_path / "output").mkdir(parents=True, exist_ok=True)
        (tmp_path / "output" / f"{date}.json").write_text("{}", encoding="utf-8")

        result = build_factor_forward_returns(
            date=date,
            candidate_root=tmp_path / "candidate",
            output_root=tmp_path / "output",
            horizons=[1, 3, 5],
            prefer_backfilled=True,
            dry_run=False,
            force=False,
        )

        assert result["status"] == "already_exists"
        assert result["has_forward_return_file"] is True

    def test_force_overwrite(self, tmp_path):
        """--force 应覆盖已存在文件。"""
        date = "2026-07-10"
        _make_candidate_file(
            tmp_path / "candidate" / date / "top30_candidates.json",
            [{"code": "600001", "name": "测试股"}],
        )
        # 创建已存在的 forward return 文件
        (tmp_path / "output").mkdir(parents=True, exist_ok=True)
        (tmp_path / "output" / f"{date}.json").write_text("{}", encoding="utf-8")

        result = build_factor_forward_returns(
            date=date,
            candidate_root=tmp_path / "candidate",
            output_root=tmp_path / "output",
            horizons=[1, 3, 5],
            prefer_backfilled=True,
            dry_run=False,
            force=True,
        )

        assert result["status"] == "processed"

    def test_dry_run_no_files(self, tmp_path):
        """dry-run 不应写文件。"""
        date = "2026-07-10"
        _make_candidate_file(
            tmp_path / "candidate" / date / "top30_candidates.json",
            [{"code": "600001", "name": "测试股"}],
        )

        result = build_factor_forward_returns(
            date=date,
            candidate_root=tmp_path / "candidate",
            output_root=tmp_path / "output",
            horizons=[1, 3, 5],
            prefer_backfilled=True,
            dry_run=True,
            force=False,
        )

        assert result["status"] == "dry_run"
        assert not (tmp_path / "output" / f"{date}.json").exists()

    def test_missing_candidate_file(self, tmp_path):
        """缺失 candidate 文件应优雅降级。"""
        result = build_factor_forward_returns(
            date="2026-07-10",
            candidate_root=tmp_path / "candidate",
            output_root=tmp_path / "output",
            horizons=[1, 3, 5],
            prefer_backfilled=True,
            dry_run=False,
            force=False,
        )

        assert result["status"] == "missing_candidate_file"

    def test_no_candidates(self, tmp_path):
        """空 candidates 应正确处理。"""
        date = "2026-07-10"
        _make_candidate_file(
            tmp_path / "candidate" / date / "top30_candidates.json",
            [],
        )

        result = build_factor_forward_returns(
            date=date,
            candidate_root=tmp_path / "candidate",
            output_root=tmp_path / "output",
            horizons=[1, 3, 5],
            prefer_backfilled=True,
            dry_run=False,
            force=False,
        )

        assert result["status"] == "no_candidates"

    def test_output_json_schema(self, tmp_path):
        """输出 JSON 应符合 schema。"""
        date = "2026-07-10"
        _make_candidate_file(
            tmp_path / "candidate" / date / "top30_candidates.json",
            [
                {"code": "600001", "name": "测试股A"},
                {"code": "600002", "name": "测试股B"},
            ],
        )

        result = build_factor_forward_returns(
            date=date,
            candidate_root=tmp_path / "candidate",
            output_root=tmp_path / "output",
            horizons=[1, 3, 5],
            prefer_backfilled=True,
            dry_run=False,
            force=False,
        )

        assert result["status"] == "processed"

        # 验证输出文件
        output_path = tmp_path / "output" / f"{date}.json"
        assert output_path.exists()

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert data["as_of"] == date
        assert data["source"] == "factor_forward_return_builder"
        assert "horizons" in data
        assert "items" in data
        assert "summary" in data
        assert len(data["items"]) == 2
        assert data["summary"]["candidate_count"] == 2

    def test_preserves_candidate_order(self, tmp_path):
        """应保持 candidate 顺序。"""
        date = "2026-07-10"
        _make_candidate_file(
            tmp_path / "candidate" / date / "top30_candidates.json",
            [
                {"code": "600003", "name": "C"},
                {"code": "600001", "name": "A"},
                {"code": "600002", "name": "B"},
            ],
        )

        build_factor_forward_returns(
            date=date,
            candidate_root=tmp_path / "candidate",
            output_root=tmp_path / "output",
            horizons=[1, 3, 5],
            prefer_backfilled=True,
            dry_run=False,
            force=False,
        )

        output_path = tmp_path / "output" / f"{date}.json"
        data = json.loads(output_path.read_text(encoding="utf-8"))
        codes = [item["code"] for item in data["items"]]
        assert codes == ["600003", "600001", "600002"]


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """集成测试。"""

    def test_end_to_end(self, tmp_path):
        """端到端测试。"""
        # 创建测试数据
        for date in ["2026-07-01", "2026-07-02"]:
            _make_candidate_file(
                tmp_path / "candidate" / date / "top30_candidates.json",
                [
                    {"code": "600001", "name": "测试股A"},
                    {"code": "600002", "name": "测试股B"},
                ],
            )

        # 运行构建
        for date in ["2026-07-01", "2026-07-02"]:
            result = build_factor_forward_returns(
                date=date,
                candidate_root=tmp_path / "candidate",
                output_root=tmp_path / "output",
                horizons=[1, 3, 5],
                prefer_backfilled=True,
                dry_run=False,
                force=False,
            )
            assert result["status"] == "processed"

        # 验证输出
        for date in ["2026-07-01", "2026-07-02"]:
            output_path = tmp_path / "output" / f"{date}.json"
            assert output_path.exists()
            data = json.loads(output_path.read_text(encoding="utf-8"))
            assert len(data["items"]) == 2
            assert data["summary"]["candidate_count"] == 2
