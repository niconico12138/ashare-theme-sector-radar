"""
L1 数据与证据提取 Agent

把 sector_scores、multi_window_consensus、历史窗口、风险、数据质量等输入整理成统一 evidence 包。
"""

from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_DATA_EVIDENCE


class EvidenceExtractionAgent:
    """
    L1 数据与证据提取 Agent

    把 sector_scores、multi_window_consensus、历史窗口、风险、数据质量等输入整理成统一 evidence 包。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def analyze(
        self,
        sector_name: str,
        sector_type: str,
        score_data: Dict[str, Any],
        consensus_data: Dict[str, Any],
    ) -> AgentOpinion:
        """
        提取证据

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            score_data: 评分数据
            consensus_data: 多窗口共识数据

        Returns:
            AgentOpinion
        """
        # 提取趋势评分
        trend_scores = {
            "trend_continuation_score": score_data.get("trend_continuation_score", 0.0),
            "trend_level": score_data.get("trend_level", ""),
        }

        # 提取短线爆发评分
        burst_score = score_data.get("short_term_burst_score", 0.0)

        # 提取多窗口标签
        multi_window_label = consensus_data.get("multi_window_label", "")

        # 提取数据质量
        data_quality = score_data.get("data_quality_score", 0.0)

        # 提取风险等级
        risk_level = score_data.get("risk_level", "")

        # 提取历史覆盖
        history_coverage = score_data.get("history_coverage_ratio", 0.0)

        # 提取雷达分
        radar_score = score_data.get("radar_score", 0.0)

        # 提取基准模式
        benchmark_mode = score_data.get("benchmark_mode", "")

        # 提取关键指标
        key_metrics = {
            "opportunity_score": score_data.get("opportunity_score", 0.0),
            "evidence_score": score_data.get("evidence_score", 0.0),
            "risk_control_score": score_data.get("risk_control_score", 0.0),
            "confidence_score": score_data.get("confidence_score", 0.0),
        }

        # 确定证据强度
        evidence_strength = self._assess_evidence_strength(
            data_quality, history_coverage, trend_scores, burst_score
        )

        # 生成证据列表
        evidence = []
        if trend_scores["trend_level"] in ["trend_confirmed", "trend_forming"]:
            evidence.append("技术面趋势确认或形成中")
        if burst_score >= 50:
            evidence.append("短线热度活跃")
        if multi_window_label in ["multi_window_confirmed", "short_mid_strong_long_weak"]:
            evidence.append("多窗口趋势确认")
        if risk_level in ["risk_low", "risk_moderate"]:
            evidence.append("风险可控")

        # 计算分数
        score_value = {"strong": 0.8, "moderate": 0.5, "weak": 0.2}.get(evidence_strength, 0.5)

        return AgentOpinion(
            agent_id="evidence_extraction",
            layer=LAYER_DATA_EVIDENCE,
            label=evidence_strength,
            score=score_value,
            confidence=0.8,
            evidence=evidence,
            vote="positive" if evidence_strength in ["strong", "moderate"] else "neutral",
        )

    def _assess_evidence_strength(
        self,
        data_quality: float,
        history_coverage: float,
        trend_scores: Dict[str, Any],
        burst_score: float,
    ) -> str:
        """评估证据强度"""
        if data_quality < 0.5 or history_coverage < 0.5:
            return "weak"

        trend_score = trend_scores.get("trend_continuation_score", 0.0)

        if trend_score >= 65 and burst_score >= 50:
            return "strong"
        elif trend_score >= 50 or burst_score >= 50:
            return "moderate"
        else:
            return "weak"
