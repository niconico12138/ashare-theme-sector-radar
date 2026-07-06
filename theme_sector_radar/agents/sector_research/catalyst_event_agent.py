"""
催化事件智能体

读取已缓存的催化事件，判断当前板块是否存在外部事件证据。
仅用于复盘解释，不参与当前评分和标签决策。
"""

from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_SPECIALIZED


# 催化事件标签解释
CATALYST_LABEL_CN = {
    "catalyst_observed": "观察到外部事件",
    "catalyst_sparse": "事件稀少或置信度低",
    "no_catalyst_observed": "未观察到匹配事件",
    "catalyst_unknown": "事件数据不足",
}


class CatalystEventAgent:
    """
    催化事件智能体

    读取已缓存的催化事件，判断当前板块是否存在外部事件证据。
    仅用于复盘解释，不参与当前评分和标签决策。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def analyze(
        self,
        sector_name: str,
        sector_type: str,
        as_of_date: str,
        current_result: Dict[str, Any],
        catalyst_events: List[Dict[str, Any]],
        source_status: Optional[Dict[str, Any]] = None,
    ) -> AgentOpinion:
        """
        分析催化事件

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            as_of_date: 日期
            current_result: 当前板块研究结果
            catalyst_events: 催化事件列表
            source_status: 数据源状态

        Returns:
            AgentOpinion (report-only)
        """
        warnings = ["外部事件仅用于复盘解释，不参与当前评分和标签决策"]
        evidence = []

        # 检查 cache 是否存在
        if not catalyst_events:
            return AgentOpinion(
                agent_id="catalyst_event",
                layer=LAYER_SPECIALIZED,
                label="catalyst_unknown",
                score=0.0,
                confidence=0.3,
                evidence=["未读取到事件缓存"],
                warnings=warnings,
                vote="neutral",
                veto=False,
                veto_reason="",
                decision_impact="report_only",
                metadata={
                    "decision_impact": "report_only",
                    "matched_event_count": 0,
                    "source_ids": [],
                    "event_ids": [],
                },
            )

        # 匹配事件到当前板块
        matched_events = self._match_events(
            sector_name, sector_type, catalyst_events
        )

        if not matched_events:
            return AgentOpinion(
                agent_id="catalyst_event",
                layer=LAYER_SPECIALIZED,
                label="no_catalyst_observed",
                score=0.0,
                confidence=0.5,
                evidence=["当前板块未匹配到外部事件"],
                warnings=warnings,
                vote="neutral",
                veto=False,
                veto_reason="",
                decision_impact="report_only",
                metadata={
                    "decision_impact": "report_only",
                    "matched_event_count": 0,
                    "source_ids": [],
                    "event_ids": [],
                },
            )

        # 分析匹配的事件
        label = self._determine_label(matched_events)
        score = self._calculate_score(matched_events)
        confidence = self._calculate_confidence(matched_events)
        evidence = self._generate_evidence(matched_events)

        # 收集 source_ids 和 event_ids
        source_ids = list(set(e.get("source", "") for e in matched_events))
        event_ids = [e.get("event_id", "") for e in matched_events]

        return AgentOpinion(
            agent_id="catalyst_event",
            layer=LAYER_SPECIALIZED,
            label=label,
            score=score,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            vote="neutral",  # report-only，永远 neutral
            veto=False,      # report-only，永远不 veto
            veto_reason="",
            decision_impact="report_only",
            metadata={
                "decision_impact": "report_only",
                "matched_event_count": len(matched_events),
                "source_ids": source_ids,
                "event_ids": event_ids,
            },
        )

    def _match_events(
        self,
        sector_name: str,
        sector_type: str,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """匹配事件到当前板块"""
        matched = []

        for event in events:
            # 1. sector_name in event.related_industries
            if sector_name in event.get("related_industries", []):
                matched.append(event)
                continue

            # 2. sector_name in event.related_concepts
            if sector_name in event.get("related_concepts", []):
                matched.append(event)
                continue

            # 3-4. 成分股匹配（需要外部数据，当前简化处理）
            # 如果有 related_symbols 或 related_symbol_names，检查是否包含板块名称
            symbols = event.get("related_symbols", [])
            symbol_names = event.get("related_symbol_names", [])
            if sector_name in symbol_names:
                matched.append(event)
                continue

        return matched

    def _determine_label(self, matched_events: List[Dict[str, Any]]) -> str:
        """确定催化事件标签"""
        if not matched_events:
            return "no_catalyst_observed"

        # 检查事件质量
        high_quality = 0
        for event in matched_events:
            freshness = event.get("freshness", "unknown")
            confidence = event.get("confidence", 0.5)

            if freshness in ["same_day", "recent"] and confidence >= 0.5:
                high_quality += 1

        if high_quality >= 1:
            return "catalyst_observed"
        else:
            return "catalyst_sparse"

    def _calculate_score(self, matched_events: List[Dict[str, Any]]) -> float:
        """计算催化事件分数"""
        if not matched_events:
            return 0.0

        # 基于事件数量和质量
        score = min(0.5, len(matched_events) * 0.15)

        # 高质量事件加分
        for event in matched_events:
            confidence = event.get("confidence", 0.5)
            if confidence >= 0.7:
                score += 0.1
            elif confidence >= 0.5:
                score += 0.05

        return round(min(1.0, score), 2)

    def _calculate_confidence(self, matched_events: List[Dict[str, Any]]) -> float:
        """计算置信度"""
        if not matched_events:
            return 0.3

        # 基于事件数量和质量
        confidence = 0.5

        if len(matched_events) >= 3:
            confidence += 0.2
        elif len(matched_events) >= 1:
            confidence += 0.1

        # 高质量事件加分
        high_quality = sum(
            1 for e in matched_events
            if e.get("freshness") in ["same_day", "recent"] and e.get("confidence", 0) >= 0.5
        )
        if high_quality >= 2:
            confidence += 0.1

        return round(min(1.0, confidence), 2)

    def _generate_evidence(self, matched_events: List[Dict[str, Any]]) -> List[str]:
        """生成证据"""
        evidence = []

        evidence.append(f"匹配到 {len(matched_events)} 条外部事件")

        # 收集来源
        sources = list(set(e.get("source", "") for e in matched_events))
        if sources:
            evidence.append(f"事件来源: {', '.join(sources)}")

        # 显示前 2 条事件标题
        for event in matched_events[:2]:
            title = event.get("title", "")
            if title:
                evidence.append(f"事件示例: {title[:50]}")

        return evidence
