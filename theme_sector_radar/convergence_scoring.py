"""
综合排名分计算模块

将板块评分、Agent分析、量化打分融合为一个可排序的综合分。
输出完整的评分拆解，便于追溯每个分数的来源。

公式：
  综合分 = trend_component + short_component + quant_component + convergence

其中：
  trend_component = board_trend × 0.20 + trend_agent × 0.15
  short_component = board_burst × 0.20 + short_agent × 0.15
  quant_component = quant_score × 0.30
  convergence = 共振加分（-5 ~ +10）
"""

from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 权重配置
# ============================================================

# 趋势维度
W_BOARD_TREND = 0.20
W_TREND_AGENT = 0.15

# 短线维度
W_BOARD_BURST = 0.20
W_SHORT_AGENT = 0.15

# 量化维度
W_QUANT = 0.30

# 共振加分阈值
CONVERGENCE_DOUBLE_STRONG_BONUS = 10.0     # 趋势Agent≥60 且 短线Agent≥60 且 量化≥70
CONVERGENCE_DOUBLE_WEAK_BONUS = 5.0        # 趋势Agent≥60 且 短线Agent≥60 但 量化<50
CONVERGENCE_TREND_ONLY_PENALTY = -5.0      # 趋势Agent≥60 且 短线Agent<40
CONVERGENCE_SHORT_ONLY_PENALTY = -3.0      # 趋势Agent<40 且 短线Agent≥60

# 分界阈值
AGENT_STRONG = 60.0
AGENT_WEAK = 40.0
QUANT_STRONG = 70.0
QUANT_WEAK = 50.0


# ============================================================
# 共振加分计算
# ============================================================

def compute_convergence_bonus(
    trend_agent_score: float,
    short_agent_score: float,
    quant_score: float,
) -> Tuple[float, str]:
    """
    计算共振加分。

    Args:
        trend_agent_score: 趋势Agent分（0~100）
        short_agent_score: 短线Agent分（0~100）
        quant_score: 量化分（0~100）

    Returns:
        (convergence_bonus, convergence_label)
    """
    if (trend_agent_score >= AGENT_STRONG
            and short_agent_score >= AGENT_STRONG
            and quant_score >= QUANT_STRONG):
        return CONVERGENCE_DOUBLE_STRONG_BONUS, "双重确认"

    if (trend_agent_score >= AGENT_STRONG
            and short_agent_score >= AGENT_STRONG
            and quant_score < QUANT_WEAK):
        return CONVERGENCE_DOUBLE_WEAK_BONUS, "双Agent确认但量化弱"

    if (trend_agent_score >= AGENT_STRONG
            and short_agent_score < AGENT_WEAK):
        return CONVERGENCE_TREND_ONLY_PENALTY, "趋势好但短线未到"

    if (trend_agent_score < AGENT_WEAK
            and short_agent_score >= AGENT_STRONG):
        return CONVERGENCE_SHORT_ONLY_PENALTY, "短线脉冲但趋势弱"

    return 0.0, "中性"


# ============================================================
# 综合排名分
# ============================================================

def compute_final_score(
    board_trend_score: float = 0.0,
    board_burst_score: float = 0.0,
    trend_agent_score: float = 50.0,
    short_agent_score: float = 50.0,
    quant_score: float = 50.0,
    risk_penalty: int = 0,
) -> Dict[str, Any]:
    """
    计算综合排名分。

    Args:
        board_trend_score: 板块趋势分（0~100）
        board_burst_score: 板块短线分（0~100）
        trend_agent_score: 趋势Agent分（0~100）
        short_agent_score: 短线Agent分（0~100）
        quant_score: 量化分（0~100）
        risk_penalty: 风险扣分

    Returns:
        完整的评分拆解字典
    """
    # 各维度贡献
    trend_component = board_trend_score * W_BOARD_TREND + trend_agent_score * W_TREND_AGENT
    short_component = board_burst_score * W_BOARD_BURST + short_agent_score * W_SHORT_AGENT
    quant_component = quant_score * W_QUANT

    # 共振加分
    convergence_bonus, convergence_label = compute_convergence_bonus(
        trend_agent_score, short_agent_score, quant_score
    )

    # 综合分（风险调整前）
    raw_score = trend_component + short_component + quant_component + convergence_bonus

    # 风险调整
    risk_adjusted = raw_score - risk_penalty

    # 归一化到 0~100
    final_score = max(0.0, min(100.0, round(risk_adjusted, 2)))

    return {
        # 维度贡献
        "trend_component": round(trend_component, 2),
        "short_component": round(short_component, 2),
        "quant_component": round(quant_component, 2),
        "convergence_bonus": round(convergence_bonus, 2),
        "convergence_label": convergence_label,

        # 原始分
        "raw_score": round(raw_score, 2),
        "risk_penalty": risk_penalty,

        # 最终分
        "final_score": final_score,

        # 公式说明
        "formula": f"board_trend×{W_BOARD_TREND} + trend_agent×{W_TREND_AGENT} + board_burst×{W_BOARD_BURST} + short_agent×{W_SHORT_AGENT} + quant×{W_QUANT} + convergence({convergence_label}) - risk({risk_penalty})",
    }


def rank_stocks_by_final_score(
    stocks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    按综合分排序个股列表。

    每个 stock 字典应包含：
    - board_trend_score: 板块趋势分
    - board_burst_score: 板块短线分
    - trend_agent_score: 趋势Agent分
    - short_agent_score: 短线Agent分
    - quant_score: 量化分
    - risk_penalty: 风险扣分

    Args:
        stocks: 个股列表

    Returns:
        按综合分降序排列的个股列表（原地修改并返回）
    """
    for s in stocks:
        result = compute_final_score(
            board_trend_score=s.get("board_trend_score", 0),
            board_burst_score=s.get("board_burst_score", 0),
            trend_agent_score=s.get("trend_agent_score", 50),
            short_agent_score=s.get("short_agent_score", 50),
            quant_score=s.get("quant_score", 50),
            risk_penalty=s.get("risk_penalty", 0),
        )
        s.update(result)
        s["legacy_final_score"] = s.get("final_score", 0)  # 保留旧字段兼容

    stocks.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    for i, s in enumerate(stocks):
        s["rank"] = i + 1

    return stocks


def build_ranking_summary(stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    生成排名摘要。

    Args:
        stocks: 已排序的个股列表

    Returns:
        摘要字典
    """
    if not stocks:
        return {"total": 0, "avg_score": 0, "convergence_distribution": {}}

    # 共振分布
    convergence_dist = {}
    for s in stocks:
        label = s.get("convergence_label", "中性")
        convergence_dist[label] = convergence_dist.get(label, 0) + 1

    avg_score = sum(s.get("final_score", 0) for s in stocks) / len(stocks)

    return {
        "total": len(stocks),
        "avg_final_score": round(avg_score, 2),
        "convergence_distribution": convergence_dist,
        "top_5": [
            {
                "rank": s.get("rank", 0),
                "code": s.get("code", ""),
                "name": s.get("name", ""),
                "final_score": s.get("final_score", 0),
                "convergence_label": s.get("convergence_label", ""),
            }
            for s in stocks[:5]
        ],
    }
