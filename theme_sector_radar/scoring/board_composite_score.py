"""
板块综合分计算模块

将趋势分和短线分合并为一个可排序的板块综合分，
并输出交叉矩阵分类（共振/趋势型/脉冲/回避）。

公式：
  board_score = trend_score × 0.55 + burst_score × 0.35 + consensus_bonus × 0.10

交叉矩阵：
  trend≥65 且 burst≥65 → 🔥共振（consensus_bonus=+10）
  trend≥65 且 burst<40  → 📉趋势独行（consensus_bonus=-5）
  trend<40 且 burst≥65  → ⚠️一日游（consensus_bonus=-5）
  其他 → consensus_bonus=0
"""

from typing import Any, Dict, Optional, Tuple


# ============================================================
# 权重配置
# ============================================================

TREND_WEIGHT = 0.55
BURST_WEIGHT = 0.35
CONSENSUS_BONUS_WEIGHT = 0.10  # 共识加成在 board_score 中的权重（放大后使用）

# 交叉矩阵阈值
TREND_STRONG = 65.0
TREND_WEAK = 40.0
BURST_STRONG = 65.0
BURST_WEAK = 40.0

# 共识加成值
CONVERGENCE_BONUS = 10.0      # 趋势+短线双强
CONVERGENCE_PENALTY_TREND = -5.0   # 趋势好但短线弱
CONVERGENCE_PENALTY_BURST = -5.0   # 短线脉冲但趋势弱
CONVERGENCE_NEUTRAL = 0.0


# ============================================================
# 交叉矩阵分类
# ============================================================

BOARD_REGIMES = {
    "共振": {"label": "🔥共振", "desc": "趋势和短线双重确认"},
    "趋势型": {"label": "📈趋势型", "desc": "趋势强但短线未启动"},
    "趋势独行": {"label": "📉趋势独行", "desc": "趋势好但短线弱"},
    "脉冲": {"label": "⚡脉冲", "desc": "短线爆发但趋势弱"},
    "一日游": {"label": "⚠️一日游", "desc": "短线强但趋势弱，警惕假突破"},
    "震荡": {"label": "➡️震荡", "desc": "趋势和短线都一般"},
    "偏弱": {"label": "📉偏弱", "desc": "趋势和短线都偏弱"},
    "回避": {"label": "🚫回避", "desc": "趋势和短线都弱"},
}


def classify_board_regime(trend_score: float, burst_score: float) -> str:
    """
    根据趋势分和短线分，分类板块所处阶段。

    Args:
        trend_score: 趋势持续分（0~100）
        burst_score: 短线爆发分（0~100）

    Returns:
        板块阶段标签
    """
    if trend_score >= TREND_STRONG and burst_score >= BURST_STRONG:
        return "共振"
    elif trend_score >= TREND_STRONG and burst_score >= BURST_WEAK:
        return "趋势型"
    elif trend_score >= TREND_STRONG and burst_score < BURST_WEAK:
        return "趋势独行"
    elif trend_score >= TREND_WEAK and burst_score >= BURST_STRONG:
        return "脉冲"
    elif trend_score < TREND_WEAK and burst_score >= BURST_STRONG:
        return "一日游"
    elif trend_score >= TREND_WEAK and burst_score >= BURST_WEAK:
        return "震荡"
    elif trend_score < TREND_WEAK and burst_score < BURST_WEAK:
        return "回避"
    else:
        return "偏弱"


def compute_consensus_bonus(trend_score: float, burst_score: float) -> float:
    """
    计算趋势+短线交叉加成。

    Args:
        trend_score: 趋势持续分（0~100）
        burst_score: 短线爆发分（0~100）

    Returns:
        共识加成值（-5 ~ +10）
    """
    if trend_score >= TREND_STRONG and burst_score >= BURST_STRONG:
        return CONVERGENCE_BONUS
    elif trend_score >= TREND_STRONG and burst_score < BURST_WEAK:
        return CONVERGENCE_PENALTY_TREND
    elif trend_score < TREND_WEAK and burst_score >= BURST_STRONG:
        return CONVERGENCE_PENALTY_BURST
    else:
        return CONVERGENCE_NEUTRAL


# ============================================================
# 板块综合分
# ============================================================

def compute_board_score(
    trend_score: float,
    burst_score: float,
    consensus_score: float = 0.0,
) -> Tuple[float, str, float]:
    """
    计算板块综合分。

    公式：
      board_score = trend × 0.55 + burst × 0.35 + consensus_bonus × 0.10
      consensus_bonus = 交叉矩阵加成（-5 ~ +10）

    Args:
        trend_score: 趋势持续分（0~100）
        burst_score: 短线爆发分（0~100）
        consensus_score: 共识分（未使用，预留）

    Returns:
        (board_score, regime, consensus_bonus)
    """
    consensus_bonus = compute_consensus_bonus(trend_score, burst_score)

    board_score = (
        trend_score * TREND_WEIGHT
        + burst_score * BURST_WEIGHT
        + consensus_bonus * CONSENSUS_BONUS_WEIGHT * 10  # 放大10倍使加成有意义
    )

    # 限制在 0~100
    board_score = max(0.0, min(100.0, round(board_score, 2)))

    regime = classify_board_regime(trend_score, burst_score)

    return board_score, regime, consensus_bonus


def enrich_sector_with_board_score(sector: Dict[str, Any]) -> Dict[str, Any]:
    """
    为单个板块数据添加 board_score、regime、consensus_bonus。

    Args:
        sector: 板块数据字典，需包含 trend_score 和 burst_score

    Returns:
        添加了新字段的板块数据字典
    """
    trend_score = sector.get("trend_score", 0) or 0
    burst_score = sector.get("burst_score", 0) or 0
    consensus_score = sector.get("consensus_score", 0) or 0

    board_score, regime, consensus_bonus = compute_board_score(
        trend_score, burst_score, consensus_score
    )

    sector["board_score"] = board_score
    sector["board_regime"] = regime
    sector["consensus_bonus"] = consensus_bonus

    return sector


def rank_sectors_by_board_score(
    sectors: list[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    """
    按 board_score 排序板块列表。

    Args:
        sectors: 板块数据列表

    Returns:
        按 board_score 降序排列的板块列表（原地修改并返回）
    """
    for s in sectors:
        enrich_sector_with_board_score(s)

    sectors.sort(key=lambda x: x.get("board_score", 0), reverse=True)

    for i, s in enumerate(sectors):
        s["board_rank"] = i + 1

    return sectors


def get_board_summary(sectors: list[Dict[str, Any]]) -> Dict[str, Any]:
    """
    生成板块综合摘要。

    Args:
        sectors: 已 enrich 的板块列表

    Returns:
        摘要字典
    """
    regime_counts = {}
    for s in sectors:
        regime = s.get("board_regime", "未知")
        regime_counts[regime] = regime_counts.get(regime, 0) + 1

    top_3 = sectors[:3] if sectors else []
    avg_score = sum(s.get("board_score", 0) for s in sectors) / len(sectors) if sectors else 0

    return {
        "total_sectors": len(sectors),
        "avg_board_score": round(avg_score, 2),
        "regime_distribution": regime_counts,
        "top_3": [
            {
                "name": s.get("name", s.get("sector_name", "")),
                "board_score": s.get("board_score", 0),
                "regime": s.get("board_regime", ""),
                "trend_score": s.get("trend_score", 0),
                "burst_score": s.get("burst_score", 0),
            }
            for s in top_3
        ],
    }
