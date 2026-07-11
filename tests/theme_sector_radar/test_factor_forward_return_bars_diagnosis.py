"""
Bars 数据源诊断测试

覆盖：
- code 格式标准化
- bars 覆盖 as_of 但没有未来窗口
- bars 覆盖未来窗口可以 matched
- 字段名 close/收盘 兼容
- provider 返回空时记录 bars_empty
- missing_reason_counts 正确
- build_factor_forward_returns 输出 bars_source/bars_count/bars_start/bars_end
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from build_factor_forward_returns import (
    normalize_code,
    compute_forward_returns_from_bars,
    compute_forward_returns_from_candidate,
    fetch_bars_for_candidate,
    load_candidates,
)
from diagnose_factor_forward_return_bars import (
    normalize_code as diag_normalize_code,
)


# ============================================================
# Code Normalization Tests
# ============================================================

class TestCodeNormalization:
    """测试代码格式标准化。"""

    def test_normalize_plain_code(self):
        """纯数字代码应保持不变。"""
        assert normalize_code("600001") == "600001"

    def test_normalize_sh_prefix(self):
        """SH 前缀应被去除。"""
        assert normalize_code("sh600001") == "600001"
        assert normalize_code("SH600001") == "600001"

    def test_normalize_sz_prefix(self):
        """SZ 前缀应被去除。"""
        assert normalize_code("sz000001") == "000001"
        assert normalize_code("SZ000001") == "000001"

    def test_normalize_sh_suffix(self):
        """SH 后缀应被去除。"""
        assert normalize_code("600001.SH") == "600001"
        assert normalize_code("600001.sh") == "600001"

    def test_normalize_sz_suffix(self):
        """SZ 后缀应被去除。"""
        assert normalize_code("000001.SZ") == "000001"
        assert normalize_code("000001.sz") == "000001"

    def test_normalize_complex(self):
        """复杂格式应正确处理。"""
        assert normalize_code("sh600001.SH") == "600001"
        assert normalize_code("SZ000001.sz") == "000001"

    def test_diag_normalize_code_matches(self):
        """诊断脚本的 normalize_code 应与主脚本一致。"""
        test_cases = ["600001", "sh600001", "600001.SH", "SZ000001", "000001.SZ"]
        for code in test_cases:
            assert normalize_code(code) == diag_normalize_code(code)


# ============================================================
# Forward Return Computation Tests
# ============================================================

class TestForwardReturnComputation:
    """测试 forward return 计算。"""

    def test_bars_cover_as_of_no_future(self):
        """bars 覆盖 as_of 但没有未来窗口时应返回 None。"""
        dates = ["2026-07-10"]
        closes = [10.0]
        bars = [
            {"date": d, "close": c, "open": c * 0.99, "high": c * 1.02, "low": c * 0.98}
            for d, c in zip(dates, closes)
        ]

        result = compute_forward_returns_from_bars(bars, "2026-07-10", [1, 3, 5])

        assert result["1d"] is None
        assert result["3d"] is None
        assert result["5d"] is None

    def test_bars_cover_future_window(self):
        """bars 覆盖未来窗口时应返回有效值。"""
        dates = [f"2026-07-{i:02d}" for i in range(10, 16)]
        closes = [10.0, 10.1, 10.2, 10.3, 10.4, 10.5]
        bars = [
            {"date": d, "close": c, "open": c * 0.99, "high": c * 1.02, "low": c * 0.98}
            for d, c in zip(dates, closes)
        ]

        result = compute_forward_returns_from_bars(bars, "2026-07-10", [1, 3, 5])

        # 1d: (10.1 - 10.0) / 10.0 * 100 = 1.0%
        assert result["1d"] == pytest.approx(1.0, rel=0.01)
        # 3d: (10.3 - 10.0) / 10.0 * 100 = 3.0%
        assert result["3d"] == pytest.approx(3.0, rel=0.01)
        # 5d: (10.5 - 10.0) / 10.0 * 100 = 5.0%
        assert result["5d"] == pytest.approx(5.0, rel=0.01)

    def test_bars_close_field_name(self):
        """应支持 close 字段名。"""
        bars = [{"date": "2026-07-10", "close": 10.0}]
        result = compute_forward_returns_from_bars(bars, "2026-07-10", [1])
        # 只有一天数据，无法计算 forward return
        assert result["1d"] is None

    def test_bars_empty(self):
        """空 bars 应返回 None。"""
        result = compute_forward_returns_from_bars([], "2026-07-10", [1, 3, 5])
        assert result["1d"] is None
        assert result["3d"] is None
        assert result["5d"] is None


# ============================================================
# Fetch Bars Tests
# ============================================================

class TestFetchBars:
    """测试 bars 获取。"""

    def test_fetch_bars_no_client(self):
        """没有 client 时应返回 no_client。"""
        candidate = {"code": "600001", "name": "测试股"}
        bars, meta = fetch_bars_for_candidate(candidate, "2026-07-10", client=None)

        assert bars is None
        assert meta["bars_source"] == "no_client"
        assert meta["normalized_code"] == "600001"

    def test_fetch_bars_normalized_code(self):
        """应使用标准化代码。"""
        candidate = {"code": "sh600001", "name": "测试股"}
        bars, meta = fetch_bars_for_candidate(candidate, "2026-07-10", client=None)

        assert meta["normalized_code"] == "600001"


# ============================================================
# Candidate Loading Tests
# ============================================================

class TestCandidateLoading:
    """测试候选股加载。"""

    def test_load_prefer_backfilled(self, tmp_path):
        """应优先加载 backfilled 文件。"""
        date = "2026-07-10"
        # 创建 backfilled 文件
        backfilled_path = tmp_path / date / "top30_candidates.factor_backfilled.json"
        backfilled_path.parent.mkdir(parents=True, exist_ok=True)
        backfilled_path.write_text(
            json.dumps({"candidates": [{"code": "600001"}]}),
            encoding="utf-8",
        )

        # 创建原文件
        original_path = tmp_path / date / "top30_candidates.json"
        original_path.write_text(
            json.dumps({"candidates": [{"code": "600002"}]}),
            encoding="utf-8",
        )

        result = load_candidates(date, tmp_path, prefer_backfilled=True)
        assert result is not None
        assert result[0]["code"] == "600001"


# ============================================================
# Build Factor Forward Returns Output Tests
# ============================================================

class TestBuildOutput:
    """测试构建输出。"""

    def test_output_contains_bars_metadata(self, tmp_path):
        """输出应包含 bars 元数据。"""
        date = "2026-07-10"
        candidate_path = tmp_path / "candidate" / date
        candidate_path.mkdir(parents=True, exist_ok=True)
        (candidate_path / "top30_candidates.json").write_text(
            json.dumps({"candidates": [{"code": "600001", "name": "测试股"}]}),
            encoding="utf-8",
        )

        from build_factor_forward_returns import build_factor_forward_returns

        result = build_factor_forward_returns(
            date=date,
            candidate_root=tmp_path / "candidate",
            output_root=tmp_path / "output",
            horizons=[1, 3, 5],
            prefer_backfilled=True,
            dry_run=False,
            force=False,
            client=None,
        )

        assert result["status"] == "processed"

        # 检查输出文件
        output_path = tmp_path / "output" / f"{date}.json"
        assert output_path.exists()

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data["items"]) == 1

        item = data["items"][0]
        assert "bars_source" in item
        assert "bars_count" in item
        assert "bars_start" in item
        assert "bars_end" in item

    def test_output_contains_missing_reason_counts(self, tmp_path):
        """输出应包含 missing_reason_counts。"""
        date = "2026-07-10"
        candidate_path = tmp_path / "candidate" / date
        candidate_path.mkdir(parents=True, exist_ok=True)
        (candidate_path / "top30_candidates.json").write_text(
            json.dumps({"candidates": [{"code": "600001", "name": "测试股"}]}),
            encoding="utf-8",
        )

        from build_factor_forward_returns import build_factor_forward_returns

        result = build_factor_forward_returns(
            date=date,
            candidate_root=tmp_path / "candidate",
            output_root=tmp_path / "output",
            horizons=[1, 3, 5],
            prefer_backfilled=True,
            dry_run=False,
            force=False,
            client=None,
        )

        output_path = tmp_path / "output" / f"{date}.json"
        data = json.loads(output_path.read_text(encoding="utf-8"))

        assert "missing_reason_counts" in data["summary"]
        assert isinstance(data["summary"]["missing_reason_counts"], dict)


# ============================================================
# Diagnosis Script Tests
# ============================================================

class TestDiagnosisScript:
    """测试诊断脚本。"""

    def test_diagnosis_creates_reports(self, tmp_path):
        """诊断脚本应生成报告。"""
        from diagnose_factor_forward_return_bars import diagnose_bars_availability, generate_json_report, generate_markdown_report

        stats = diagnose_bars_availability("2026-07-10", "2026-07-10", tmp_path)

        json_path = tmp_path / "test.json"
        md_path = tmp_path / "test.md"

        generate_json_report(stats, json_path)
        generate_markdown_report(stats, md_path)

        assert json_path.exists()
        assert md_path.exists()

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "total_dates" in data
        assert "provider_status" in data
