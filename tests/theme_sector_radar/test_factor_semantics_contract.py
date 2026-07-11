"""
Factor Semantics Contract 测试

覆盖：
- contract 文档存在且包含关键语义
- 生产代码不包含 forbidden trade words
- 生产代码不包含 forbidden legacy semantics
- evaluate 脚本 recommendation 正确
- selection_quality 不输出 trigger_candidate
- stock_explanation 使用新 reason_codes
- 所有候选仍为 watch_only
"""

import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONTRACT_PATH = PROJECT_ROOT / "docs" / "runbooks" / "factor_semantics_contract.md"

# ============================================================
# Forbidden Words (生产输出不得包含)
# ============================================================

FORBIDDEN_TRADE_WORDS = [
    "买入", "卖出", "持有", "推荐",
    "建仓", "加仓", "减仓",
    "止盈", "止损", "目标价",
    "交易触发", "突破触发", "自动剔除", "自动纳入",
]

# ============================================================
# Forbidden Legacy Semantics (生产代码不得作为活跃语义)
# ============================================================

FORBIDDEN_LEGACY_REASONS = [
    "near_breakout_structure",  # 旧 reason_code
    "breakout_structure_watch",  # 旧 reason_code
    "far_from_breakout",  # 旧 reason_code
    "healthy_drawdown",  # 旧 reason_code
    "normal_drawdown",  # 旧 reason_code
    "deep_drawdown_risk",  # 旧 reason_code
    "drawdown_too_deep",  # 旧 invalidation flag
]

FORBIDDEN_POLICY_VALUES = [
    "trigger_candidate",  # 旧 policy
]

# ============================================================
# Production Files to Audit
# ============================================================

PRODUCTION_FILES = [
    "theme_sector_radar/reporting/daily_compact_report.py",
    "theme_sector_radar/reporting/daily_decision_summary.py",
    "theme_sector_radar/reporting/stock_profile.py",
    "theme_sector_radar/reporting/stock_explanation.py",
    "theme_sector_radar/reporting/selection_quality.py",
    "theme_sector_radar/factors/registry.py",
    "theme_sector_radar/factors/calculators.py",
    "scripts/evaluate_bars_factor_shadow_policy.py",
    "scripts/diagnose_bars_factor_definitions.py",
]


# ============================================================
# Contract Document Tests
# ============================================================

class TestContractDocument:
    """测试 factor_semantics_contract.md 存在且包含关键语义。"""

    def test_contract_exists(self):
        """contract 文档必须存在。"""
        assert CONTRACT_PATH.exists(), f"Contract not found: {CONTRACT_PATH}"

    def test_contract_contains_breakout_semantics(self):
        """contract 必须包含 breakout_distance_20 语义。"""
        content = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "breakout_distance_20" in content
        assert "structure_position" in content or "结构位置" in content

    def test_contract_contains_drawdown_semantics(self):
        """contract 必须包含 drawdown_depth_20 语义。"""
        content = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "drawdown_depth_20" in content
        assert "repair_context" in content or "修复上下文" in content

    def test_contract_contains_chasing_risk_semantics(self):
        """contract 必须包含 chasing_risk_score 语义。"""
        content = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "chasing_risk_score" in content
        assert "overheat" in content or "过热" in content

    def test_contract_contains_liquidity_semantics(self):
        """contract 必须包含 liquidity_score 语义。"""
        content = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "liquidity_score" in content
        assert "profile_only" in content

    def test_contract_structure_candidate_not_buy(self):
        """contract 必须明确 structure_candidate 不等于买入触发。"""
        content = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "structure_candidate" in content
        # 不得包含买入触发的肯定表述
        assert "不等于买入触发" in content or "不得解释为买入信号" in content

    def test_contract_repair_context_not_negative(self):
        """contract 必须明确 repair_context 不等于风险恶化。"""
        content = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "repair_context" in content
        assert "不等于风险恶化" in content or "不得自动解释为坏信号" in content

    def test_contract_soft_warning_not_auto_remove(self):
        """contract 必须明确 soft_warning 不等于自动剔除。"""
        content = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "soft_warning" in content
        assert "不等于自动剔除" in content or "不得自动剔除" in content

    def test_contract_contains_forbidden_words_list(self):
        """contract 必须包含 forbidden words 列表。"""
        content = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "禁止词" in content or "forbidden" in content.lower()
        assert "买入" in content
        assert "卖出" in content


# ============================================================
# Production Code Forbidden Words Tests
# ============================================================

class TestProductionForbiddenWords:
    """测试生产代码不包含 forbidden trade words。"""

    @pytest.mark.parametrize("file_rel", PRODUCTION_FILES)
    def test_no_forbidden_trade_words(self, file_rel):
        """生产文件不应包含 forbidden trade words。"""
        file_path = PROJECT_ROOT / file_rel
        if not file_path.exists():
            pytest.skip(f"File not found: {file_rel}")

        content = file_path.read_text(encoding="utf-8")
        violations = []
        for word in FORBIDDEN_TRADE_WORDS:
            if word in content:
                # 找到行号
                for i, line in enumerate(content.split("\n"), 1):
                    if word in line:
                        violations.append(f"  line {i}: {word} in '{line.strip()}'")
                        break
        assert not violations, f"Forbidden trade words in {file_rel}:\n" + "\n".join(violations)


# ============================================================
# Production Code Legacy Semantics Tests
# ============================================================

class TestProductionLegacySemantics:
    """测试生产代码不使用 forbidden legacy reason_codes 作为活跃语义。"""

    def test_selection_quality_no_trigger_candidate(self):
        """selection_quality.py 不得输出 trigger_candidate policy。"""
        file_path = PROJECT_ROOT / "theme_sector_radar/reporting/selection_quality.py"
        content = file_path.read_text(encoding="utf-8")

        # 检查是否有 trigger_candidate 作为 policy 值
        # 允许在注释或文档字符串中出现，但不允许作为实际 policy 值
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # 跳过注释和文档字符串
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                continue
            if '"trigger_candidate"' in stripped or "'trigger_candidate'" in stripped:
                pytest.fail(f"trigger_candidate found as policy value at line {i}: {stripped}")

    def test_stock_explanation_no_legacy_reason_codes(self):
        """stock_explanation.py 不得输出旧 reason_codes。"""
        file_path = PROJECT_ROOT / "theme_sector_radar/reporting/stock_explanation.py"
        content = file_path.read_text(encoding="utf-8")

        legacy_codes = [
            "near_breakout_structure",
            "breakout_structure_watch",
            "far_from_breakout",
            "healthy_drawdown",
            "normal_drawdown",
            "deep_drawdown_risk",
        ]

        for code in legacy_codes:
            # 检查是否有 append("旧code") 的模式
            pattern = f'append("{code}")'
            if pattern in content:
                pytest.fail(f"Legacy reason_code '{code}' found in stock_explanation.py")


# ============================================================
# Evaluate Script Tests
# ============================================================

class TestEvaluateScript:
    """测试 evaluate 脚本的 recommendation 输出。"""

    def test_evaluate_no_keep_trigger_candidate(self):
        """evaluate 脚本不得输出 keep_trigger_candidate。"""
        file_path = PROJECT_ROOT / "scripts/evaluate_bars_factor_shadow_policy.py"
        content = file_path.read_text(encoding="utf-8")
        assert "keep_trigger_candidate" not in content

    def test_evaluate_contains_keep_structure_candidate(self):
        """evaluate 脚本应包含 keep_structure_candidate。"""
        file_path = PROJECT_ROOT / "scripts/evaluate_bars_factor_shadow_policy.py"
        content = file_path.read_text(encoding="utf-8")
        assert "keep_structure_candidate" in content

    def test_evaluate_contains_keep_repair_context(self):
        """evaluate 脚本应包含 keep_repair_context。"""
        file_path = PROJECT_ROOT / "scripts/evaluate_bars_factor_shadow_policy.py"
        content = file_path.read_text(encoding="utf-8")
        assert "keep_repair_context" in content

    def test_evaluate_contains_insufficient_sample(self):
        """evaluate 脚本应包含 insufficient_sample。"""
        file_path = PROJECT_ROOT / "scripts/evaluate_bars_factor_shadow_policy.py"
        content = file_path.read_text(encoding="utf-8")
        assert "insufficient_sample" in content


# ============================================================
# Watch Only Tests
# ============================================================

class TestWatchOnly:
    """测试所有候选仍为 watch_only。"""

    def test_selection_quality_action_state(self):
        """selection_quality 输出的 action_state 应恒定为 watch_only。"""
        from theme_sector_radar.reporting.selection_quality import classify_stock_candidate

        # 测试多种场景
        test_cases = [
            {"code": "600001", "name": "A", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok"},
            {"code": "600002", "name": "B", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok",
             "chasing_risk_score": 80.0},
            {"code": "600003", "name": "C", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok",
             "breakout_distance_20": 2.0},
            {"code": "600004", "name": "D", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok",
             "drawdown_depth_20": 25.0},
        ]

        for candidate in test_cases:
            result = classify_stock_candidate(candidate, "trend_top")
            assert result["action_state"] == "watch_only", \
                f"action_state should be watch_only for {candidate.get('code')}"


# ============================================================
# Reason Code Contract Tests
# ============================================================

class TestReasonCodeContract:
    """测试 reason_codes 使用新语义。"""

    def test_stock_explanation_uses_new_reason_codes(self):
        """stock_explanation.py 应使用新 reason_codes。"""
        from theme_sector_radar.reporting.stock_explanation import build_stock_explanation

        # test structure_near_high_position
        candidate = {"selection_bucket": "core_watch", "breakout_distance_20": 2.0}
        result = build_stock_explanation(candidate)
        assert "structure_near_high_position" in result["reason_codes"]

        # test deep_pullback_repair_context
        candidate = {"selection_bucket": "core_watch", "drawdown_depth_20": 20.0}
        result = build_stock_explanation(candidate)
        assert "deep_pullback_repair_context" in result["reason_codes"]

        # test shallow_pullback_state
        candidate = {"selection_bucket": "core_watch", "drawdown_depth_20": 3.0}
        result = build_stock_explanation(candidate)
        assert "shallow_pullback_state" in result["reason_codes"]

    def test_no_legacy_reason_codes_in_output(self):
        """stock_explanation 输出不应包含旧 reason_codes。"""
        from theme_sector_radar.reporting.stock_explanation import build_stock_explanation

        # 用各种 candidate 组合测试
        test_cases = [
            {"selection_bucket": "core_watch", "breakout_distance_20": 2.0},
            {"selection_bucket": "core_watch", "breakout_distance_20": 7.0},
            {"selection_bucket": "core_watch", "breakout_distance_20": 15.0},
            {"selection_bucket": "core_watch", "drawdown_depth_20": 3.0},
            {"selection_bucket": "core_watch", "drawdown_depth_20": 20.0},
        ]

        legacy_codes = [
            "near_breakout_structure",
            "breakout_structure_watch",
            "far_from_breakout",
            "healthy_drawdown",
            "normal_drawdown",
            "deep_drawdown_risk",
        ]

        for candidate in test_cases:
            result = build_stock_explanation(candidate)
            for code in legacy_codes:
                assert code not in result["reason_codes"], \
                    f"Legacy reason_code '{code}' found in output for {candidate}"
