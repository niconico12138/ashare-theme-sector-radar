"""
Daily Decision Summary 测试

覆盖：
- 正常输入生成完整 summary
- 缺 v2_monitor 不失败
- 缺 trend/burst stocks 不失败
- run_health fail 时 allow_observation=false
- data_quality fail 时 allow_observation=false
- stock item action_state 固定为 watch_only
- 不包含 forbidden trade words
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.daily_decision_summary import build_daily_decision_summary
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from tests.theme_sector_radar.paper_only_contract import (
    FORBIDDEN_WORDS,
    extract_executable_instructions,
)


# ============================================================
# Tests
# ============================================================

class TestDailyDecisionSummary:
    """测试 daily decision summary。"""

    def test_executable_instruction_extractor_ignores_research_text(self):
        payload = {
            "research_note": "buy and hold research only",
            "shadow_status": "paper_hold_observation",
            "Orders": [{"side": "sell"}],
            "command": {"side": "buy"},
            "position_size": 0.5,
            "submit_order": True,
        }

        instruction_keys, instruction_texts = extract_executable_instructions(payload)

        assert instruction_keys == {
            "orders",
            "side",
            "command",
            "position_size",
            "submit_order",
        }
        assert instruction_texts == ["sell", "buy", "0.5", "True"]

    def test_executable_instruction_extractor_rejects_common_order_fields(self):
        payload = {
            "side": "buy",
            "action": "sell",
            "quantity": 100,
            "qty": 25,
            "limit_price": 12.5,
        }

        instruction_keys, instruction_texts = extract_executable_instructions(payload)

        assert instruction_keys == {
            "side",
            "action",
            "quantity",
            "qty",
            "limit_price",
        }
        assert instruction_texts == ["buy", "sell", "100", "25", "12.5"]

    def test_executable_instruction_extractor_rejects_broker_and_live_orders(self):
        payload = {
            "broker_order": {
                "ticker": "600001",
                "shares": 100,
                "direction": "buy",
            },
            "live_order": {
                "ticker": "600002",
                "shares": 200,
                "direction": "sell",
            },
        }

        instruction_keys, instruction_texts = extract_executable_instructions(payload)

        assert instruction_keys == {"broker_order", "live_order", "shares"}
        assert instruction_texts == ["600001", "100", "buy", "600002", "200", "sell"]

    @pytest.mark.parametrize(
        "payload",
        [
            {"position": "FULL"},
            {"trade": {"direction": "BUY", "size": 100, "price": 10.5}},
            {"tradeDirection": "SELL", "allocationPct": 100},
            {
                "execution": {
                    "ticker": "600001",
                    "direction": "BUY",
                    "allocation": 0.5,
                    "units": 100,
                    "price": 10.5,
                    "timeInForce": "DAY",
                }
            },
            *(
                {
                    container: {
                    "ticker": "600001",
                    "direction": "BUY",
                    "allocation": 0.5,
                    "units": 100,
                    "price": 10.5,
                    "timeInForce": "DAY",
                    }
                }
                for container in (
                    "executionData",
                    "execution_data",
                    "executiondata",
                    "execution_assumptions",
                    "executionDetails",
                    "tradeDetails",
                    "transaction",
                    "positionDetails",
                )
            ),
        ],
    )
    def test_paper_only_contract_rejects_common_executable_aliases(self, payload):
        instruction_keys, _ = extract_executable_instructions(payload)

        assert instruction_keys
        with pytest.raises(ValueError, match="executable instruction fields"):
            validate_no_executable_instructions(payload, context="test payload")

    def test_paper_only_contract_rejects_flattened_complete_execution_payload(self):
        payload = {
            "ticker": "600001",
            "direction": "BUY",
            "allocation": 0.5,
            "units": 100,
            "price": 10.5,
            "timeInForce": "DAY",
        }

        with pytest.raises(ValueError, match="executable instruction fields"):
            validate_no_executable_instructions(payload, context="test payload")

    def test_paper_only_contract_rejects_cross_level_complete_execution_payload(self):
        payload = {
            "execution_assumptions": {
                "direction": "BUY",
                "size": 100,
                "asset": {"ticker": "600001"},
            }
        }

        with pytest.raises(ValueError, match="executable instruction fields"):
            validate_no_executable_instructions(payload, context="test payload")

    def test_paper_only_contract_allows_non_executable_research_assumptions(self):
        validate_no_executable_instructions(
            {"execution_assumptions": {"slippage_bps": 10, "latency_model": "paper"}},
            context="test payload",
        )

    def test_paper_only_contract_allows_order_book_research_factor(self):
        validate_no_executable_instructions(
            {"research": {"order_book_imbalance": 0.23}},
            context="test payload",
        )

    def test_normal_input(self):
        """正常输入应生成完整 summary。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
            "trend_top_stocks": [
                {"code": "600001", "name": "测试股A", "sector_name": "半导体", "final_score": 75.0},
            ],
            "burst_top_stocks": [
                {"code": "600002", "name": "测试股B", "sector_name": "传媒", "final_score": 70.0},
            ],
        }
        sectors = [
            {"sector_name": "半导体", "ranking_score": 0.8, "consensus_label": "trend_confirmed", "confidence_score": 0.9},
        ]
        concepts = [
            {"sector_name": "AI概念", "concept_final_rank_score": 85.0, "agent_consensus_label": "hot", "trend_continuation_score": 80.0, "short_term_burst_score": 70.0, "confidence_score": 0.85},
        ]

        result = build_daily_decision_summary("2026-07-10", unified_report, sectors, concepts)

        assert result["schema_version"] == "1.0"
        assert result["as_of"] == "2026-07-10"
        assert result["decision_mode"] == "watch_only"
        assert result["run_status"]["allow_observation"] is True
        assert len(result["stock_pools"]["trend_top"]) == 1
        assert len(result["stock_pools"]["burst_top"]) == 1

    def test_missing_v2_monitor(self):
        """缺 v2_monitor 不失败。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [], v2_monitor=None)

        assert result["stock_pools"]["v2_potential"] == []
        assert result["stock_pools"]["divergence_review"] == []

    def test_missing_trend_burst_stocks(self):
        """缺 trend/burst stocks 不失败。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [])

        assert result["stock_pools"]["trend_top"] == []
        assert result["stock_pools"]["burst_top"] == []

    def test_run_health_fail(self):
        """run_health fail 时 allow_observation=false。"""
        unified_report = {
            "run_health": {"status": "fail", "reasons": ["test reason"]},
            "data_quality": {"status": "pass", "warnings": []},
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [])

        assert result["run_status"]["allow_observation"] is False
        assert "run_health fail" in result["run_status"]["blockers"]

    def test_data_quality_fail(self):
        """data_quality fail 时 allow_observation=false。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "fail", "warnings": ["test warning"]},
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [])

        assert result["run_status"]["allow_observation"] is False
        assert "data_quality fail" in result["run_status"]["blockers"]

    def test_action_state_watch_only(self):
        """stock item action_state 固定为 watch_only。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
            "trend_top_stocks": [
                {"code": "600001", "name": "测试股", "sector_name": "测试", "final_score": 75.0},
            ],
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [])

        for pool in ["trend_top", "burst_top", "v2_potential", "divergence_review"]:
            for item in result["stock_pools"][pool]:
                assert item["action_state"] == "watch_only"

    def test_no_forbidden_trade_words(self):
        """不包含 forbidden trade words。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
            "trend_top_stocks": [
                {"code": "600001", "name": "测试股", "sector_name": "测试", "final_score": 75.0},
            ],
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [])

        instruction_keys, instruction_texts = extract_executable_instructions(result)
        assert not instruction_keys, f"Found executable instruction keys: {sorted(instruction_keys)}"
        executable_text = "\n".join(instruction_texts).casefold()

        for word in FORBIDDEN_WORDS:
            assert word.casefold() not in executable_text, f"Found forbidden word: {word}"

    def test_trend_top_final_score_not_lost(self):
        """trend_top_stocks 中 final_score 不应丢失。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
            "trend_top_stocks": [
                {"code": "600001", "name": "测试股", "sector_name": "测试", "final_score": 75.0},
            ],
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [])

        assert result["stock_pools"]["trend_top"][0]["final_score"] == 75.0

    def test_burst_top_final_score_not_lost(self):
        """burst_top_stocks 中 final_score 不应丢失。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
            "burst_top_stocks": [
                {"code": "600001", "name": "测试股", "sector_name": "测试", "final_score": 70.0},
            ],
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [])

        assert result["stock_pools"]["burst_top"][0]["final_score"] == 70.0

    def test_missing_final_score_stays_none(self):
        """缺失 final_score 时应保持 None，不变 0。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
            "trend_top_stocks": [
                {"code": "600001", "name": "测试股", "sector_name": "测试"},
            ],
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [])

        assert result["stock_pools"]["trend_top"][0]["final_score"] is None

    def test_missing_v2_score_stays_none(self):
        """缺失 v2_score 时应保持 None，不变 0。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
            "trend_top_stocks": [
                {"code": "600001", "name": "测试股", "sector_name": "测试", "final_score": 75.0},
            ],
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [])

        assert result["stock_pools"]["trend_top"][0]["v2_score"] is None

    def test_v2_monitor_sample_mapping(self):
        """v2_monitor 样本应正确映射。"""
        unified_report = {
            "run_health": {"status": "pass", "reasons": []},
            "data_quality": {"status": "pass", "warnings": []},
        }
        v2_monitor = {
            "divergence_samples": [
                {"code": "600001", "name": "古井贡酒", "final_score": 60.2, "factor_composite_shadow_score_v2": 26.66, "reason": "high_final_low_v2"},
                {"code": "600002", "name": "测试股", "final_score": 30.0, "factor_composite_shadow_score_v2": 80.0, "reason": "low_final_high_v2"},
            ],
        }

        result = build_daily_decision_summary("2026-07-10", unified_report, [], [], v2_monitor=v2_monitor)

        # divergence_review 应包含 high_final_low_v2
        div_review = result["stock_pools"]["divergence_review"]
        assert len(div_review) == 1
        assert div_review[0]["code"] == "600001"
        assert div_review[0]["final_score"] == 60.2
        assert div_review[0]["v2_score"] == 26.66
        assert div_review[0]["signal_type"] == "high_final_low_v2"
        assert div_review[0]["action_state"] == "watch_only"

        # v2_potential 应包含 low_final_high_v2
        v2_pot = result["stock_pools"]["v2_potential"]
        assert len(v2_pot) == 1
        assert v2_pot[0]["code"] == "600002"
        assert v2_pot[0]["final_score"] == 30.0
        assert v2_pot[0]["v2_score"] == 80.0
        assert v2_pot[0]["signal_type"] == "low_final_high_v2"
        assert v2_pot[0]["action_state"] == "watch_only"

        instruction_keys, instruction_texts = extract_executable_instructions(result)
        assert not instruction_keys, f"Found executable instruction keys: {sorted(instruction_keys)}"
        executable_text = "\n".join(instruction_texts).casefold()

        for word in FORBIDDEN_WORDS:
            assert word.casefold() not in executable_text, f"Found forbidden word: {word}"
