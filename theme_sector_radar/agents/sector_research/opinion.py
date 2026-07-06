"""
Agent 统一意见结构

定义 AgentOpinion 用于各层级 Agent 之间的信息传递。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentOpinion:
    """
    Agent 统一意见结构
    用于各层级 Agent 之间的信息传递。
    """
    agent_id: str
    layer: str  # L1_data_evidence / L2_specialized / L3_conflict_consistency / L4_decision
    label: str
    score: float = 0.0
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    vote: str = "neutral"  # positive / neutral / negative
    veto: bool = False
    veto_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Phase B: 新增信号特征和决策影响字段
    signal_profile: str = ""  # broad_signal / sparse_high_precision / low_information / defensive_filter / sparse_event_signal
    decision_impact: str = "participates"  # participates / report_only / excluded

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "agent_id": self.agent_id,
            "layer": self.layer,
            "label": self.label,
            "score": self.score,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "warnings": self.warnings,
            "vote": self.vote,
            "veto": self.veto,
            "veto_reason": self.veto_reason,
            "metadata": self.metadata,
            "signal_profile": self.signal_profile,
            "decision_impact": self.decision_impact,
        }
        return result


# Agent 层级定义
LAYER_DATA_EVIDENCE = "L1_data_evidence"
LAYER_SPECIALIZED = "L2_specialized"
LAYER_CONFLICT_CONSISTENCY = "L3_conflict_consistency"
LAYER_DECISION = "L4_decision"

# 投票类型
VOTE_POSITIVE = "positive"
VOTE_NEUTRAL = "neutral"
VOTE_NEGATIVE = "negative"

# Agent 信号特征分类
SIGNAL_PROFILE_BROAD = "broad_signal"          # 高覆盖普通信号
SIGNAL_PROFILE_SPARSE_HP = "sparse_high_precision"  # 低覆盖高命中信号
SIGNAL_PROFILE_LOW_INFO = "low_information"     # 低信息 Agent
SIGNAL_PROFILE_DEFENSIVE = "defensive_filter"   # 防守过滤 Agent
SIGNAL_PROFILE_SPARSE_EVENT = "sparse_event_signal"  # 低覆盖事件驱动信号

# Agent 信号特征说明
SIGNAL_PROFILE_DESCRIPTIONS = {
    SIGNAL_PROFILE_BROAD: "高覆盖普通信号，大部分样本都有投票，区分度中等",
    SIGNAL_PROFILE_SPARSE_HP: "低覆盖高命中信号，少数样本出手但质量很高",
    SIGNAL_PROFILE_LOW_INFO: "低信息 Agent，当前数据不足以产生有效信号",
    SIGNAL_PROFILE_DEFENSIVE: "防守过滤 Agent，主要识别风险和数据问题",
    SIGNAL_PROFILE_SPARSE_EVENT: "低覆盖事件驱动信号，需后续验证命中率",
}

# Agent 信号特征分配
AGENT_SIGNAL_PROFILES = {
    "technical_trend": SIGNAL_PROFILE_BROAD,
    "short_term_heat": SIGNAL_PROFILE_BROAD,
    "rotation_analysis": SIGNAL_PROFILE_BROAD,
    "risk_control": SIGNAL_PROFILE_DEFENSIVE,
    "data_quality": SIGNAL_PROFILE_DEFENSIVE,
    "market_context": SIGNAL_PROFILE_BROAD,
    "narrative": SIGNAL_PROFILE_LOW_INFO,
    "persistence_strength": SIGNAL_PROFILE_SPARSE_HP,
    "catalyst_event": SIGNAL_PROFILE_SPARSE_EVENT,
}
