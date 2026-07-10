"""
Agent 趋势/短线分组打分模块

将24个Agent分为趋势组和短线组，独立计算两个分数。
风控组（risk_control）两组共用，用于扣分。

趋势组：回答"趋势是否健康"
短线组：回答"现在是否是好的进场点"
风控组：回答"风险可控吗"
"""

from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Agent 分组定义
# ============================================================

# 方向映射
DIRECTION_MAP = {
    "buy": 1.0, "bullish": 1.0,
    "hold": 0.0, "neutral": 0.0,
    "sell": -1.0, "bearish": -1.0,
}

# 风险扣分
RISK_PENALTY = {"low": 0, "medium": 3, "high": 8, "unknown": 1}

# 趋势组 Agent（回答"趋势是否健康"）
TREND_GROUP = {
    "warren_buffett": 0.20,
    "ben_graham": 0.15,
    "industry_rotation": 0.15,
    "fundamentals_analyst": 0.10,
    "growth_analyst": 0.10,
    "charlie_munger": 0.10,
    "valuation_analyst": 0.10,
    "technical_analyst": 0.10,
}

# 短线组 Agent（回答"现在是否是好的进场点"）
SHORT_GROUP = {
    "china_youzi": 0.25,
    "northbound_flow": 0.20,
    "china_sentiment": 0.15,
    "technical_analyst": 0.15,
    "news_sentiment_analyst": 0.10,
    "sentiment_analyst": 0.10,
    "cathie_wood": 0.05,
    "nassim_taleb": 0.05,
}

# 风控组
RISK_GROUP = {
    "risk_control_agent": 1.0,
    "michael_burry": 0.5,
    "nassim_taleb": 0.5,
}

# technical_analyst 同时出现在两组中（趋势看MA排列，短线看量价突破）
# 这是合理的，因为它既看趋势也看短线


# ============================================================
# 打分函数
# ============================================================

def _compute_group_score(
    agent_results: List[Dict[str, Any]],
    group_weights: Dict[str, float],
) -> Tuple[float, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    计算一组 Agent 的加权分数。

    Args:
        agent_results: Agent 分析结果列表
        group_weights: 该组的权重配置 {agent_id: weight}

    Returns:
        (score 0~100, 有效Agent详情, 降级Agent详情)
    """
    # 1. 分类：ok / fallback / error
    ok_agents = []
    fallback_agents = []
    for ar in agent_results:
        agent_id = ar.get("agent_id", "")
        if agent_id not in group_weights:
            continue  # 不在本组的Agent跳过
        if ar.get("status") == "error":
            continue
        elif ar.get("confidence", 0) > 0:
            ok_agents.append(ar)
        else:
            fallback_agents.append(ar)

    # 2. 如果没有有效Agent，返回中性分50
    if not ok_agents:
        return 50.0, [], [{"agent": ar.get("agent_id", ""), "reason": "no_confidence"} for ar in fallback_agents]

    # 3. 获取权重并归一化
    raw_weights = {}
    for ar in ok_agents:
        agent_id = ar.get("agent_id", "")
        raw_weights[agent_id] = group_weights.get(agent_id, 0.05)

    total_raw_weight = sum(raw_weights.values())
    if total_raw_weight <= 0:
        for ar in ok_agents:
            raw_weights[ar.get("agent_id", "")] = 1.0 / len(ok_agents)
        total_raw_weight = 1.0

    # 4. 计算加权信号分
    weighted_sum = 0.0
    details = []
    for ar in ok_agents:
        agent_id = ar.get("agent_id", "")
        weight = raw_weights[agent_id] / total_raw_weight
        direction = DIRECTION_MAP.get(ar.get("signal", "neutral"), 0.0)
        norm_conf = max(0.0, min(1.0, ar.get("confidence", 50.0) / 100.0))
        contribution = weight * direction * norm_conf
        weighted_sum += contribution
        details.append({
            "agent": agent_id,
            "signal": ar.get("signal", "neutral"),
            "confidence": ar.get("confidence", 0),
            "weight": round(weight, 4),
            "contribution": round(contribution, 4),
        })

    # 5. 归一化到 0~100（weighted_sum 范围 -1 ~ +1）
    score = 50.0 + weighted_sum * 50.0
    score = max(0.0, min(100.0, round(score, 1)))

    fallback_details = [
        {"agent": ar.get("agent_id", ""), "reason": ar.get("error", "data_insufficient")}
        for ar in fallback_agents
    ]

    return score, details, fallback_details


def _compute_risk_penalty(agent_results: List[Dict[str, Any]]) -> Tuple[int, str]:
    """
    计算风险扣分。

    Args:
        agent_results: Agent 分析结果列表

    Returns:
        (penalty值, 主要风险等级)
    """
    risk_counts = {}
    for ar in agent_results:
        agent_id = ar.get("agent_id", "")
        if agent_id in RISK_GROUP or agent_id == "risk_control_agent":
            rl = ar.get("risk_level", "medium")
            risk_counts[rl] = risk_counts.get(rl, 0) + 1

    if not risk_counts:
        return RISK_PENALTY["unknown"], "unknown"

    avg_risk = max(risk_counts, key=risk_counts.get)
    return RISK_PENALTY.get(avg_risk, 1), avg_risk


def compute_trend_short_scores(
    agent_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    计算趋势分和短线分。

    Args:
        agent_results: Agent 分析结果列表

    Returns:
        {
            "trend_agent_score": float,      # 趋势Agent分 0~100
            "short_agent_score": float,      # 短线Agent分 0~100
            "risk_level": str,               # 风险等级
            "risk_penalty": int,             # 风险扣分
            "trend_agents_detail": list,     # 趋势组Agent详情
            "short_agents_detail": list,     # 短线组Agent详情
            "trend_fallback_agents": list,   # 趋势组降级Agent
            "short_fallback_agents": list,   # 短线组降级Agent
            "bullish_count": int,            # 看多Agent数
            "neutral_count": int,            # 中性Agent数
            "bearish_count": int,            # 看空Agent数
        }
    """
    # 1. 趋势组打分
    trend_score, trend_details, trend_fallback = _compute_group_score(
        agent_results, TREND_GROUP
    )

    # 2. 短线组打分
    short_score, short_details, short_fallback = _compute_group_score(
        agent_results, SHORT_GROUP
    )

    # 3. 风险扣分
    risk_penalty, risk_level = _compute_risk_penalty(agent_results)

    # 4. 统计投票
    bullish = sum(1 for ar in agent_results
                  if DIRECTION_MAP.get(ar.get("signal", "neutral"), 0) > 0)
    neutral = sum(1 for ar in agent_results
                  if DIRECTION_MAP.get(ar.get("signal", "neutral"), 0) == 0)
    bearish = sum(1 for ar in agent_results
                  if DIRECTION_MAP.get(ar.get("signal", "neutral"), 0) < 0)

    return {
        "trend_agent_score": trend_score,
        "short_agent_score": short_score,
        "risk_level": risk_level,
        "risk_penalty": risk_penalty,
        "trend_agents_detail": trend_details,
        "short_agents_detail": short_details,
        "trend_fallback_agents": trend_fallback,
        "short_fallback_agents": short_fallback,
        "bullish_count": bullish,
        "neutral_count": neutral,
        "bearish_count": bearish,
    }
