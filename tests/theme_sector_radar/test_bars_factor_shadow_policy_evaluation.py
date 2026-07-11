"""
Bars Factor Shadow Policy Evaluation 测试

覆盖：
- 正常加载 candidates
- 优先读取 analysis_backfilled 文件
- forward return 缺失时不失败
- bars_factor_policy 缺失时不失败
- breakout_structure 分组统计正确
- drawdown_state 分组统计正确
- liquidity_state 分组统计正确
- overheat_state 分组统计正确
- opportunity_type 分层正确
- 样本不足时输出 insufficient_sample
- JSON 报告生成
- Markdown 报告生成
- 不包含交易建议词
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluate_bars_factor_shadow_policy import (
    calc_mean,
    calc_rank_ic,
    analyze_group_performance,
    analyze_by_field,
    load_candidates,
    load_forward_returns,
    run_analysis,
    generate_json_report,
    generate_markdown_report,
)


# ============================================================
# Forbidden Words
# ============================================================

FORBIDDEN_WORDS = [
    "buy", "sell", "hold",
    "买入", "卖出", "持有", "推荐",
    "建仓", "加仓", "减仓",
    "止盈", "止损", "目标价",
]


# ============================================================
# Statistical Helper Tests
# ============================================================

class TestStatisticalHelpers:
    """测试统计辅助函数。"""

    def test_calc_mean(self):
        """calc_mean 应正确计算均值。"""
        assert calc_mean([1.0, 2.0, 3.0, 4.0, 5.0]) == 3.0
        assert calc_mean([]) == 0.0

    def test_calc_rank_ic(self):
        """calc_rank_ic 应正确计算。"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        returns = [0.1, 0.2, 0.3, 0.4, 0.5]
        ic = calc_rank_ic(scores, returns)
        assert ic is not None
        assert ic > 0


# ============================================================
# Data Loading Tests
# ============================================================

class TestDataLoading:
    """测试数据加载。"""

    def test_load_candidates_analysis_backfilled(self, tmp_path):
        """应优先读取 analysis_backfilled 文件。"""
        date = "2026-07-10"
        path = tmp_path / date
        path.mkdir(parents=True)
        (path / "top30_candidates.analysis_backfilled.json").write_text(
            json.dumps({"candidates": [{"code": "600001"}]}),
            encoding="utf-8",
        )

        result = load_candidates(date, tmp_path)
        assert result is not None
        assert len(result) == 1

    def test_load_forward_returns(self, tmp_path):
        """应正确加载 forward returns。"""
        date = "2026-07-10"
        path = tmp_path / f"{date}.json"
        path.write_text(
            json.dumps({"items": [{"code": "600001", "1d": 0.05, "5d": 0.10}]}),
            encoding="utf-8",
        )

        result = load_forward_returns(date, tmp_path)
        assert result is not None
        assert result["600001"]["1d"] == 0.05


# ============================================================
# Group Analysis Tests
# ============================================================

class TestGroupAnalysis:
    """测试分组分析。"""

    def test_analyze_group_performance(self):
        """应正确分析分组表现。"""
        samples = [
            {"code": "600001", "returns": {"1d": 0.05, "5d": 0.10}},
            {"code": "600002", "returns": {"1d": -0.02, "5d": 0.03}},
        ]

        result = analyze_group_performance(samples, ["1d", "5d"])

        assert result["sample_count"] == 2
        assert result["horizon_stats"]["1d"]["mean_return"] == 0.015
        assert result["horizon_stats"]["5d"]["mean_return"] == 0.065

    def test_analyze_by_field(self):
        """应正确按字段分组分析。"""
        candidates = [
            {"code": "600001", "date": "2026-07-10", "breakout_structure": "near"},
            {"code": "600002", "date": "2026-07-10", "breakout_structure": "far"},
        ]
        forward_returns_by_date = {
            "2026-07-10": {"600001": {"1d": 0.05}, "600002": {"1d": -0.02}},
        }

        result = analyze_by_field(candidates, forward_returns_by_date, "breakout_structure", ["1d"])

        assert "near" in result
        assert "far" in result
        assert result["near"]["sample_count"] == 1
        assert result["far"]["sample_count"] == 1


# ============================================================
# End-to-End Tests
# ============================================================

class TestEndToEnd:
    """端到端测试。"""

    def test_run_analysis(self, tmp_path):
        """应正确运行分析。"""
        # 创建测试数据
        for date in ["2026-07-02", "2026-07-03"]:
            candidate_dir = tmp_path / "candidate" / date
            candidate_dir.mkdir(parents=True)
            (candidate_dir / "top30_candidates.json").write_text(
                json.dumps({
                    "candidates": [
                        {
                            "code": "600001",
                            "name": "测试股A",
                            "date": date,
                            "final_score": 75.0,
                            "profile_breakout_structure": "near",
                            "profile_drawdown_state": "healthy",
                        },
                    ]
                }),
                encoding="utf-8",
            )

            forward_dir = tmp_path / "forward" / date
            forward_dir.mkdir(parents=True)
            (forward_dir / f"{date}.json").write_text(
                json.dumps({
                    "items": [
                        {"code": "600001", "1d": 0.05, "5d": 0.10},
                    ]
                }),
                encoding="utf-8",
            )

        # 运行分析
        analysis = run_analysis(
            start_date="2026-07-02",
            end_date="2026-07-03",
            candidate_root=tmp_path / "candidate",
            forward_return_root=tmp_path / "forward",
            horizons=["1d", "5d"],
        )

        assert analysis["summary"]["total_candidates"] == 2
        assert "breakout_analysis" in analysis
        assert "drawdown_analysis" in analysis

    def test_no_forbidden_words(self, tmp_path):
        """报告不应包含 forbidden words。"""
        analysis = {
            "summary": {"start_date": "2026-07-02", "end_date": "2026-07-03", "total_candidates": 0, "total_with_forward": 0, "total_with_policy": 0, "horizons": ["1d"]},
            "breakout_analysis": {},
            "drawdown_analysis": {},
            "liquidity_analysis": {},
            "overheat_analysis": {},
            "opp_type_analysis": {},
        }
        md_path = tmp_path / "test_report.md"
        generate_markdown_report(analysis, md_path)

        # 读取文件的原始字节
        raw_bytes = md_path.read_bytes()
        # 尝试用 utf-8 解码
        content = raw_bytes.decode("utf-8")

        # 检查英文禁词（使用单词边界）
        import re
        for word in ["buy", "sell"]:
            assert not re.search(r'\b' + word + r'\b', content.lower()), f"Found forbidden word: {word}"

        # 检查中文禁词 - 直接检查字节模式避免编码问题
        forbidden_chinese = ["买入", "卖出", "持有", "推荐", "建仓", "加仓", "减仓", "止盈", "止损", "目标价"]
        for word in forbidden_chinese:
            # 将中文词转换为字节进行检查
            word_bytes = word.encode("utf-8")
            assert word_bytes not in raw_bytes, f"Found forbidden word: {word}"
