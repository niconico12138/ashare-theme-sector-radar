"""
L3 置信度校准 Agent

校准 confidence_score，让它继续表示"当前标签可信度"，不是机会强度。
"""

from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_CONFLICT_CONSISTENCY


class ConfidenceCalibrationAgent:
    """
    L3 置信度校准 Agent

    校准 confidence_score，让它继续表示"当前标签可信度"，不是机会强度。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def calibrate(
        self,
        score_data: Dict[str, Any],
        vote_opinion: AgentOpinion,
        conflict_opinion: AgentOpinion,
        veto_opinion: AgentOpinion,
    ) -> AgentOpinion:
        """
        校准置信度

        Args:
            score_data: 评分数据
            vote_opinion: 投票结果
            conflict_opinion: 冲突检测结果
            veto_opinion: Veto 结果

        Returns:
            校准后的置信度结果
        """
        # 提取因素
        # Phase B fix: score_data 中没有 data_quality_score 字段
        # 使用 history_coverage_ratio 作为数据质量代理指标
        data_quality = score_data.get("history_coverage_ratio") or 0.0
        history_coverage = score_data.get("history_coverage_ratio") or 0.0
        # confidence_score 在 score_data 中为 None（由 ConsensusDecisionAgent 计算）
        # 这里基于可用因子自己计算基础置信度
        confidence_score = None

        # 计算置信度因子
        confidence_factors = {}

        # 数据质量因子
        confidence_factors["data_quality"] = data_quality

        # Agent 投票一致性因子
        vote_metadata = vote_opinion.metadata
        positive_ratio = vote_metadata.get("positive_votes", 0) / max(vote_metadata.get("total_votes", 1), 1)
        confidence_factors["vote_consistency"] = positive_ratio

        # 冲突级别因子
        conflict_metadata = conflict_opinion.metadata
        conflict_level = conflict_metadata.get("conflict_level", "none")
        conflict_factor = {"none": 1.0, "low": 0.8, "medium": 0.6, "high": 0.4}.get(conflict_level, 0.5)
        confidence_factors["conflict_factor"] = conflict_factor

        # Veto 因子
        veto_metadata = veto_opinion.metadata
        veto_triggered = veto_metadata.get("veto_triggered", False)
        confidence_factors["veto_factor"] = 0.5 if veto_triggered else 1.0

        # 多窗口覆盖因子
        history_coverage = score_data.get("history_coverage_ratio", 0.0)
        confidence_factors["coverage_factor"] = min(history_coverage, 1.0)

        # 计算校准后的置信度
        # 如果 score_data 没有 confidence_score（通常如此），从因子计算基础分
        if confidence_score is None:
            # 基于因子的加权平均作为基础置信度
            base = (
                confidence_factors["data_quality"] * 0.30
                + confidence_factors["vote_consistency"] * 0.25
                + confidence_factors["conflict_factor"] * 0.20
                + confidence_factors["coverage_factor"] * 0.15
                + (1.0 if confidence_factors["veto_factor"] == 1.0 else 0.5) * 0.10
            )
        else:
            base = confidence_score

        calibrated_score = base
        calibrated_score *= confidence_factors["data_quality"]
        calibrated_score *= confidence_factors["vote_consistency"]
        calibrated_score *= confidence_factors["conflict_factor"]
        calibrated_score *= confidence_factors["veto_factor"]
        calibrated_score *= confidence_factors["coverage_factor"]

        calibrated_score = max(0.0, min(1.0, calibrated_score))

        return AgentOpinion(
            agent_id="confidence_calibration",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label="calibrated",
            score=calibrated_score,
            confidence=0.9,
            evidence=[f"校准后置信度: {calibrated_score:.2f}"],
            metadata={
                "calibrated_confidence_score": calibrated_score,
                "confidence_factors": confidence_factors,
            },
        )
