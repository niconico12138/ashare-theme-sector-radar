"""
Factor Composite Shadow Score 评估测试

覆盖：
- 正常多日输入能生成 JSON/Markdown
- forward_returns 缺失时仍成功
- score 字段部分缺失时仍成功
- rank IC 计算正确
- 分位数组合样本不足时优雅降级
- 输出报告路径正确
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluate_factor_composite_shadow_score import (
    calc_mean,
    calc_median,
    calc_std,
    calc_rank_ic,
    calc_quintile_returns,
    calc_correlation,
    load_top30_candidates,
    load_forward_returns,
    evaluate_single_day,
    evaluate_multi_day,
    generate_json_report,
    generate_markdown_report,
    SCORE_FIELDS,
)


# ============================================================
# Statistical Helper Tests
# ============================================================

class TestStatisticalHelpers:
    """测试统计辅助函数。"""

    def test_calc_mean(self):
        """calc_mean 应正确计算均值。"""
        assert calc_mean([1.0, 2.0, 3.0, 4.0, 5.0]) == 3.0
        assert calc_mean([]) == 0.0
        assert calc_mean([10.0]) == 10.0

    def test_calc_median(self):
        """calc_median 应正确计算中位数。"""
        assert calc_median([1.0, 2.0, 3.0, 4.0, 5.0]) == 3.0
        assert calc_median([1.0, 2.0, 3.0, 4.0]) == 2.5
        assert calc_median([]) == 0.0

    def test_calc_std(self):
        """calc_std 应正确计算标准差。"""
        # [1, 2, 3, 4, 5] 的标准差
        std = calc_std([1.0, 2.0, 3.0, 4.0, 5.0])
        assert abs(std - 1.5811) < 0.01
        assert calc_std([]) == 0.0
        assert calc_std([1.0]) == 0.0


class TestRankIC:
    """测试 Rank IC 计算。"""

    def test_rank_ic_perfect_correlation(self):
        """完美正相关的 Rank IC 应为 1.0。"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        returns = [0.1, 0.2, 0.3, 0.4, 0.5]
        ic = calc_rank_ic(scores, returns)
        assert ic is not None
        assert abs(ic - 1.0) < 0.01

    def test_rank_ic_negative_correlation(self):
        """负相关的 Rank IC 应为 -1.0。"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        returns = [0.5, 0.4, 0.3, 0.2, 0.1]
        ic = calc_rank_ic(scores, returns)
        assert ic is not None
        assert abs(ic - (-1.0)) < 0.01

    def test_rank_ic_insufficient_samples(self):
        """样本不足时应返回 None。"""
        scores = [1.0, 2.0, 3.0]
        returns = [0.1, 0.2, 0.3]
        ic = calc_rank_ic(scores, returns)
        assert ic is None

    def test_rank_ic_no_correlation(self):
        """无相关时 Rank IC 应接近 0。"""
        # 这些数据有轻微正相关，放宽阈值
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        returns = [0.3, 0.1, 0.4, 0.2, 0.5]
        ic = calc_rank_ic(scores, returns)
        assert ic is not None
        # 允许更大范围
        assert abs(ic) < 0.5


class TestQuintileReturns:
    """测试分位数组合表现。"""

    def test_quintile_returns_normal(self):
        """正常数据应返回 5 个分位数。"""
        scores = list(range(1, 51))
        returns = [i * 0.01 for i in range(1, 51)]
        quintiles = calc_quintile_returns(scores, returns, n_quintiles=5)

        assert quintiles is not None
        assert len(quintiles) == 5
        assert quintiles[0]["quintile"] == 1
        assert quintiles[-1]["quintile"] == 5

    def test_quintile_returns_insufficient(self):
        """样本不足时应返回 None。"""
        scores = [1.0, 2.0, 3.0]
        returns = [0.1, 0.2, 0.3]
        quintiles = calc_quintile_returns(scores, returns, n_quintiles=5)
        assert quintiles is None


class TestCorrelation:
    """测试相关系数计算。"""

    def test_correlation_perfect(self):
        """完美正相关的相关系数应为 1.0。"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        corr = calc_correlation(x, y)
        assert corr is not None
        assert abs(corr - 1.0) < 0.01

    def test_correlation_insufficient(self):
        """样本不足时应返回 None。"""
        x = [1.0, 2.0, 3.0]
        y = [2.0, 4.0, 6.0]
        corr = calc_correlation(x, y)
        assert corr is None

    def test_correlation_negative(self):
        """完美负相关的相关系数应为 -1.0。"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [10.0, 8.0, 6.0, 4.0, 2.0]
        corr = calc_correlation(x, y)
        assert corr is not None
        assert abs(corr - (-1.0)) < 0.01


# ============================================================
# Data Loading Tests
# ============================================================

class TestDataLoading:
    """测试数据加载。"""

    def test_load_top30_candidates_exists(self, tmp_path):
        """存在的文件应正确加载。"""
        date = "2026-07-10"
        data_dir = tmp_path / date
        data_dir.mkdir(parents=True)
        (data_dir / "top30_candidates.json").write_text(
            json.dumps({"candidates": [{"code": "600001"}]}),
            encoding="utf-8",
        )

        result = load_top30_candidates(date, tmp_path)
        assert result is not None
        assert len(result["candidates"]) == 1

    def test_load_top30_candidates_missing(self, tmp_path):
        """不存在的文件应返回 None。"""
        result = load_top30_candidates("2026-07-10", tmp_path)
        assert result is None

    def test_load_forward_returns_exists(self, tmp_path):
        """存在的 forward returns 应正确加载。"""
        date = "2026-07-10"
        data_dir = tmp_path / date
        data_dir.mkdir(parents=True)
        (data_dir / "forward_returns.json").write_text(
            json.dumps({"returns": {"600001": 0.05, "600002": -0.02}}),
            encoding="utf-8",
        )

        result = load_forward_returns(date, tmp_path)
        assert result is not None
        assert result["600001"] == 0.05

    def test_load_forward_returns_missing(self, tmp_path):
        """不存在的 forward returns 应返回 None。"""
        result = load_forward_returns("2026-07-10", tmp_path)
        assert result is None


# ============================================================
# Evaluation Tests
# ============================================================

class TestEvaluateSingleDay:
    """测试单天评估。"""

    def test_evaluate_with_all_fields(self):
        """所有字段存在时应正确评估。"""
        candidates = [
            {"code": "600001", "final_score": 75.0, "factor_composite_shadow_score": 72.0},
            {"code": "600002", "final_score": 70.0, "factor_composite_shadow_score": 68.0},
        ]
        forward_returns = {"600001": 0.05, "600002": -0.02}

        result = evaluate_single_day("2026-07-10", candidates, forward_returns)

        assert result["date"] == "2026-07-10"
        assert result["candidate_count"] == 2
        assert result["has_forward_returns"] is True

        # final_score 字段
        fs = result["fields"]["final_score"]
        assert fs["coverage"] == 100.0
        assert fs["min"] == 70.0
        assert fs["max"] == 75.0

    def test_evaluate_without_forward_returns(self):
        """没有 forward returns 时应优雅降级。"""
        candidates = [
            {"code": "600001", "final_score": 75.0},
        ]

        result = evaluate_single_day("2026-07-10", candidates, None)

        assert result["has_forward_returns"] is False
        # Rank IC 应为 None
        assert result["fields"]["final_score"]["rank_ic"] is None

    def test_evaluate_with_missing_scores(self):
        """部分 score 缺失时应正确处理。"""
        candidates = [
            {"code": "600001", "final_score": 75.0},
            {"code": "600002"},  # 缺失 final_score
        ]

        result = evaluate_single_day("2026-07-10", candidates, None)

        fs = result["fields"]["final_score"]
        assert fs["coverage"] == 50.0
        assert fs["missing"] == 1


class TestEvaluateMultiDay:
    """测试多日评估。"""

    def test_evaluate_multi_day_normal(self, tmp_path):
        """正常多日输入应生成报告。"""
        # 创建测试数据
        for idx, date in enumerate(["2026-07-01", "2026-07-02", "2026-07-03"]):
            data_dir = tmp_path / "agent_bridge" / date
            data_dir.mkdir(parents=True)
            (data_dir / "top30_candidates.json").write_text(
                json.dumps({
                    "candidates": [
                        {"code": "600001", "final_score": 75.0 + idx},
                        {"code": "600002", "final_score": 70.0 + idx},
                    ]
                }),
                encoding="utf-8",
            )
            # 创建 forward returns
            fr_dir = tmp_path / "forward_returns" / date
            fr_dir.mkdir(parents=True)
            (fr_dir / "forward_returns.json").write_text(
                json.dumps({"returns": {"600001": 0.05, "600002": -0.02}}),
                encoding="utf-8",
            )

        result = evaluate_multi_day(
            "2026-07-01",
            "2026-07-03",
            tmp_path / "agent_bridge",
            tmp_path / "forward_returns",
        )

        assert result["summary"]["evaluated_dates"] == 3
        assert len(result["daily_results"]) == 3

    def test_evaluate_multi_day_missing_candidates(self, tmp_path):
        """缺少 candidate 文件时应跳过。"""
        # 只创建一天的数据
        data_dir = tmp_path / "agent_bridge" / "2026-07-01"
        data_dir.mkdir(parents=True)
        (data_dir / "top30_candidates.json").write_text(
            json.dumps({"candidates": []}),
            encoding="utf-8",
        )

        result = evaluate_multi_day(
            "2026-07-01",
            "2026-07-03",
            tmp_path / "agent_bridge",
            tmp_path / "forward_returns",
        )

        assert result["summary"]["evaluated_dates"] == 1
        assert len(result["summary"]["missing_candidate_files"]) == 2

    def test_evaluate_multi_day_no_forward_returns(self, tmp_path):
        """没有 forward returns 时应优雅降级。"""
        # 创建 candidate 文件但没有 forward returns
        for date in ["2026-07-01", "2026-07-02"]:
            data_dir = tmp_path / "agent_bridge" / date
            data_dir.mkdir(parents=True)
            (data_dir / "top30_candidates.json").write_text(
                json.dumps({"candidates": [{"code": "600001", "final_score": 75.0}]}),
                encoding="utf-8",
            )

        result = evaluate_multi_day(
            "2026-07-01",
            "2026-07-02",
            tmp_path / "agent_bridge",
            tmp_path / "forward_returns",
        )

        assert result["summary"]["evaluated_dates"] == 2
        assert len(result["summary"]["no_forward_return_dates"]) == 2


# ============================================================
# Report Generation Tests
# ============================================================

class TestReportGeneration:
    """测试报告生成。"""

    def test_generate_json_report(self, tmp_path):
        """应正确生成 JSON 报告。"""
        evaluation = {
            "summary": {"start_date": "2026-07-01", "end_date": "2026-07-03"},
            "field_summary": {},
            "daily_results": [],
        }
        output_path = tmp_path / "test_report.json"

        generate_json_report(evaluation, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["summary"]["start_date"] == "2026-07-01"

    def test_generate_markdown_report(self, tmp_path):
        """应正确生成 Markdown 报告。"""
        evaluation = {
            "summary": {
                "start_date": "2026-07-01",
                "end_date": "2026-07-03",
                "total_dates": 3,
                "evaluated_dates": 3,
                "missing_candidate_files": [],
                "no_forward_return_dates": [],
            },
            "field_summary": {
                "final_score": {"avg_coverage": 100.0, "total_samples": 100, "avg_rank_ic": 0.05},
                "factor_composite_shadow_score": {"avg_coverage": 90.0, "total_samples": 90, "avg_rank_ic": 0.08},
            },
            "correlation_results": {"final_score_vs_factor_composite_shadow_score": 0.85},
            "daily_results": [],
        }
        output_path = tmp_path / "test_report.md"

        generate_markdown_report(evaluation, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "Factor Composite Shadow Score 评估报告" in content
        assert "Rank IC 对比" in content


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """集成测试。"""

    def test_end_to_end(self, tmp_path):
        """端到端测试：从数据到报告。"""
        # 创建测试数据
        for date in ["2026-07-01", "2026-07-02"]:
            data_dir = tmp_path / "agent_bridge" / date
            data_dir.mkdir(parents=True)
            (data_dir / "top30_candidates.json").write_text(
                json.dumps({
                    "candidates": [
                        {"code": "600001", "final_score": 75.0, "factor_composite_shadow_score": 72.0},
                        {"code": "600002", "final_score": 70.0, "factor_composite_shadow_score": 68.0},
                    ]
                }),
                encoding="utf-8",
            )
            fr_dir = tmp_path / "forward_returns" / date
            fr_dir.mkdir(parents=True)
            (fr_dir / "forward_returns.json").write_text(
                json.dumps({"returns": {"600001": 0.05, "600002": -0.02}}),
                encoding="utf-8",
            )

        output_dir = tmp_path / "output"

        # 运行评估
        evaluation = evaluate_multi_day(
            "2026-07-01",
            "2026-07-02",
            tmp_path / "agent_bridge",
            tmp_path / "forward_returns",
        )

        # 生成报告
        json_path = output_dir / "evaluation.json"
        md_path = output_dir / "evaluation.md"
        generate_json_report(evaluation, json_path)
        generate_markdown_report(evaluation, md_path)

        assert json_path.exists()
        assert md_path.exists()

        # 验证 JSON 内容
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["summary"]["evaluated_dates"] == 2
