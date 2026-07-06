"""
L3 Agent 投票聚合器

汇总各 AgentOpinion，生成投票明细。
report-only 的 Agent (metadata.decision_impact == "report_only") 不参与投票计数。
"""

from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_CONFLICT_CONSISTENCY, VOTE_POSITIVE, VOTE_NEUTRAL, VOTE_NEGATIVE


class AgentVoteAggregator:
    """
    L3 Agent 投票聚合器

    汇总各 AgentOpinion，生成投票明细。
    report-only Agent 的 opinion 会被排除在投票统计之外，
    但仍保留在 agent_opinions 中用于报告展示。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def aggregate(
        self,
        opinions: List[AgentOpinion],
    ) -> AgentOpinion:
        """
        聚合投票

        report-only (metadata.decision_impact == "report_only") 的 Agent 不参与投票计数。

        Args:
            opinions: Agent 意见列表 (可能包含 report-only)

        Returns:
            聚合结果
        """
        # 过滤 report-only 和 excluded (low_information) 的 Agent
        # report-only: 仅展示不参与决策
        # excluded: 信息量不足，投票会稀释正向/负向比例
        decision_opinions = [
            o for o in opinions
            if o.metadata.get("decision_impact") != "report_only"
            and o.decision_impact != "excluded"
        ]

        # 统计投票 (仅决策层 Agent)
        positive_votes = sum(1 for o in decision_opinions if o.vote == "positive")
        neutral_votes = sum(1 for o in decision_opinions if o.vote == "neutral")
        negative_votes = sum(1 for o in decision_opinions if o.vote == "negative")
        veto_votes = sum(1 for o in decision_opinions if o.veto)

        # 计算投票摘要
        total_votes = len(decision_opinions)

        # 防止除零：如果所有 opinion 都是 report-only
        if total_votes == 0:
            return AgentOpinion(
                agent_id="vote_aggregator",
                layer=LAYER_CONFLICT_CONSISTENCY,
                label="no_decision_opinions",
                score=0.0,
                confidence=0.0,
                evidence=["所有 Agent 均为 report-only，无决策层投票"],
                vote="neutral",
                metadata={
                    "positive_votes": 0,
                    "neutral_votes": 0,
                    "negative_votes": 0,
                    "veto_votes": 0,
                    "total_votes": 0,
                    "report_only_count": len(opinions),
                },
            )

        positive_ratio = positive_votes / total_votes

        # 确定聚合标签
        if positive_ratio >= 0.6:
            vote_summary = "majority_positive"
        elif positive_ratio >= 0.4:
            vote_summary = "mixed_signals"
        else:
            vote_summary = "majority_negative"

        report_only_count = len(opinions) - total_votes

        # 生成证据
        evidence = [
            f"positive_votes: {positive_votes}",
            f"neutral_votes: {neutral_votes}",
            f"negative_votes: {negative_votes}",
            f"veto_votes: {veto_votes}",
            f"total_decision_votes: {total_votes}",
        ]
        if report_only_count > 0:
            evidence.append(f"report_only_opinions (excluded from voting): {report_only_count}")

        return AgentOpinion(
            agent_id="vote_aggregator",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label=vote_summary,
            score=positive_ratio,
            confidence=0.8,
            vote="positive" if positive_ratio >= 0.6 else "neutral" if positive_ratio >= 0.4 else "negative",
            metadata={
                "positive_votes": positive_votes,
                "neutral_votes": neutral_votes,
                "negative_votes": negative_votes,
                "veto_votes": veto_votes,
                "total_votes": total_votes,
                "report_only_count": report_only_count,
            },
        )
