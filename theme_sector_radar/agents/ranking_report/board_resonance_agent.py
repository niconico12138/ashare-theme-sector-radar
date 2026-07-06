"""
Board Resonance Agent (Phase 44)

计算行业与概念板块的共振评分。

共振评分公式（Phase 44 更新）：
resonance_score =
  industry_strength_score * 0.25
+ concept_strength_score * 0.20
+ overlap_score * 0.20
+ semantic_match_score * 0.20
+ label_alignment_score * 0.10
+ risk_adjustment_score * 0.05
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# 语义映射配置路径
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_RESONANCE_MAP_PATH = _CONFIG_DIR / "board_resonance_map.json"


def _load_resonance_map() -> dict[str, list[str]]:
    """加载语义映射配置"""
    if not _RESONANCE_MAP_PATH.exists():
        return {}
    try:
        with open(_RESONANCE_MAP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _normalize_name(name: str) -> str:
    """标准化名称"""
    # 去掉"概念""概念股"
    name = name.replace("概念股", "").replace("概念", "")
    # 去掉空格
    name = name.replace(" ", "")
    # 统一大小写（中文无影响）
    return name.strip()


def _calculate_semantic_match_score(
    industry_name: str,
    concept_name: str,
    resonance_map: dict[str, list[str]],
) -> tuple[float, str]:
    """计算语义匹配分"""
    # Exact mapping match
    if industry_name in resonance_map:
        mapped_concepts = resonance_map[industry_name]
        if concept_name in mapped_concepts:
            return 100.0, f"exact_match: {industry_name} → {concept_name}"

        # Normalized name match
        norm_concept = _normalize_name(concept_name)
        for mapped in mapped_concepts:
            if _normalize_name(mapped) == norm_concept:
                return 80.0, f"normalized_match: {industry_name} → {mapped}"

        # Same keyword family
        industry_chars = set(industry_name)
        concept_chars = set(concept_name)
        common_chars = industry_chars & concept_chars
        if len(common_chars) >= 2:
            return 60.0, f"keyword_family: {industry_name} ∩ {concept_name} ({''.join(common_chars)})"

    # Check reverse mapping (concept → industry)
    for ind, concepts in resonance_map.items():
        if concept_name in concepts:
            return 50.0, f"reverse_match: {concept_name} ∈ {ind}"

    return 0.0, "no_match"


@dataclass
class ResonancePair:
    """共振组合"""
    rank: int
    industry: str
    concept: str
    resonance_type: str
    resonance_score: float
    resonance_bonus: float
    overlap_stock_count: int
    overlap_stocks: list[dict]
    industry_strength: float
    concept_strength: float
    confidence: str
    reason: str
    industry_data: dict = field(default_factory=dict)
    concept_data: dict = field(default_factory=dict)
    # Phase 44 新增字段
    semantic_match_score: float = 0.0
    semantic_match_reason: str = ""
    original_rank: int = 0
    resonance_rank: int = 0
    rank_delta: int = 0
    score_breakdown: dict = field(default_factory=dict)


def calculate_board_resonance(
    industry_top: list[dict],
    concept_top: list[dict],
    industry_constituents: dict[str, list[dict]] | None = None,
    concept_constituents: dict[str, list[dict]] | None = None,
    top_n: int = 10,
) -> dict[str, Any]:
    """
    计算行业与概念板块的共振评分。

    Args:
        industry_top: 行业 Top N 评分列表
        concept_top: 概念 Top N 评分列表
        industry_constituents: 行业成分股字典（可选）
        concept_constituents: 概念成分股字典（可选）
        top_n: Top N 数量

    Returns:
        共振结果字典
    """
    # 加载语义映射
    resonance_map = _load_resonance_map()

    resonance_pairs = []
    warnings = []

    # 获取 Top N 的行业和概念
    top_industry_names = {item.get("sector_name", "") for item in industry_top[:top_n]}
    top_concept_names = {item.get("sector_name", "") for item in concept_top[:top_n]}

    # 构建评分字典
    industry_score_dict = {item.get("sector_name", ""): item for item in industry_top}
    concept_score_dict = {item.get("sector_name", ""): item for item in concept_top}

    # 检查所有行业-概念组合
    for industry_item in industry_top[:top_n]:
        industry_name = industry_item.get("sector_name", "")
        industry_type = industry_item.get("sector_type", "industry")

        for concept_item in concept_top[:top_n]:
            concept_name = concept_item.get("sector_name", "")
            concept_type = concept_item.get("sector_type", "concept")

            try:
                # 计算成分股重合
                overlap_count = 0
                overlap_stocks = []

                if industry_constituents and concept_constituents:
                    industry_codes = {s.get("code", "") for s in industry_constituents.get(industry_name, [])}
                    concept_codes = {s.get("code", "") for s in concept_constituents.get(concept_name, [])}
                    overlap_codes = industry_codes & concept_codes
                    overlap_count = len(overlap_codes)

                    # 获取重合股票详情
                    for code in list(overlap_codes)[:10]:
                        for s in industry_constituents.get(industry_name, []):
                            if s.get("code") == code:
                                overlap_stocks.append({"code": code, "name": s.get("name", "")})
                                break

                # Phase 44: 计算语义匹配分
                semantic_score, semantic_reason = _calculate_semantic_match_score(
                    industry_name, concept_name, resonance_map
                )

                # 计算共振分
                resonance_score, score_breakdown = _calculate_resonance_score(
                    industry_item=industry_item,
                    concept_item=concept_item,
                    overlap_count=overlap_count,
                    semantic_score=semantic_score,
                    top_industry_names=top_industry_names,
                    top_concept_names=top_concept_names,
                )

                # 计算共振加分
                resonance_bonus = min(8.0, resonance_score / 100 * 8.0)

                # Phase 44: 弱风险边界
                risk_adjustment = score_breakdown.get("risk_adjustment_score", 100)
                resonance_type_raw = _determine_resonance_type(
                    industry_item=industry_item,
                    concept_item=concept_item,
                    overlap_count=overlap_count,
                    resonance_score=resonance_score,
                )
                if resonance_type_raw == "weak_or_conflicted":
                    resonance_bonus = min(resonance_bonus, 1.0)
                if risk_adjustment == 0:
                    resonance_bonus = 0.0

                # 确定共振类型
                resonance_type = resonance_type_raw

                # 计算行业强度分
                industry_strength = _calculate_industry_strength(industry_item)

                # 计算概念强度分
                concept_strength = _calculate_concept_strength(concept_item)

                # Phase 44: 确定置信度
                confidence = _determine_confidence(
                    resonance_score, overlap_count, semantic_score, risk_adjustment
                )

                # 生成说明
                reason = _generate_reason(
                    industry_item=industry_item,
                    concept_item=concept_item,
                    overlap_count=overlap_count,
                    resonance_type=resonance_type,
                    semantic_score=semantic_score,
                )

                resonance_pairs.append(ResonancePair(
                    rank=0,  # 后续排序
                    industry=industry_item.get("sector_name", ""),
                    concept=concept_item.get("sector_name", ""),
                    resonance_type=resonance_type,
                    resonance_score=round(resonance_score, 2),
                    resonance_bonus=round(resonance_bonus, 2),
                    overlap_stock_count=overlap_count,
                    overlap_stocks=overlap_stocks,
                    industry_strength=round(industry_strength, 2),
                    concept_strength=round(concept_strength, 2),
                    confidence=confidence,
                    reason=reason,
                    industry_data=industry_item,
                    concept_data=concept_item,
                    # Phase 44 新增字段
                    semantic_match_score=round(semantic_score, 2),
                    semantic_match_reason=semantic_reason,
                    original_rank=concept_item.get("rank", 0),
                    score_breakdown=score_breakdown,
                ))

            except Exception as e:
                warnings.append(
                    f"计算共振 {industry_item.get('sector_name')}-{concept_item.get('sector_name')} 失败: {str(e)}"
                )

    # 按共振分排序
    resonance_pairs.sort(key=lambda x: x.resonance_score, reverse=True)

    # 设置排名和 rank_delta
    for i, pair in enumerate(resonance_pairs):
        pair.rank = i + 1
        pair.resonance_rank = i + 1
        pair.rank_delta = pair.original_rank - pair.resonance_rank

    # Phase 44: 统计信息
    high_confidence = sum(1 for p in resonance_pairs if p.confidence == "high")
    medium_confidence = sum(1 for p in resonance_pairs if p.confidence == "medium")
    semantic_resonance = sum(1 for p in resonance_pairs if p.resonance_type == "semantic_resonance")
    max_bonus = max((p.resonance_bonus for p in resonance_pairs), default=0)

    return {
        "as_of": industry_top[0].get("as_of_date", "") if industry_top else "",
        "resonance_pairs": [pair.__dict__ for pair in resonance_pairs],
        "warnings": warnings,
        "summary": {
            "total_pairs": len(resonance_pairs),
            "high_confidence_pairs": high_confidence,
            "medium_confidence_pairs": medium_confidence,
            "semantic_resonance_pairs": semantic_resonance,
            "avg_resonance_score": round(
                sum(p.resonance_score for p in resonance_pairs) / len(resonance_pairs), 2
            ) if resonance_pairs else 0,
            "max_resonance_bonus": round(max_bonus, 2),
        },
    }


def _calculate_resonance_score(
    industry_item: dict,
    concept_item: dict,
    overlap_count: int,
    semantic_score: float,
    top_industry_names: set,
    top_concept_names: set,
) -> tuple[float, dict]:
    """计算共振分，返回 (score, breakdown)"""
    # 1. 行业强度分 (0-100)
    industry_strength = _calculate_industry_strength(industry_item)

    # 2. 概念强度分 (0-100)
    concept_strength = _calculate_concept_strength(concept_item)

    # 3. 重叠分 (0-100)
    overlap_score = _calculate_overlap_score(overlap_count)

    # 4. 标签对齐分 (0-100)
    label_alignment = _calculate_label_alignment(industry_item, concept_item)

    # 5. 风险调整分 (0-100)
    risk_adjustment = _calculate_risk_adjustment(industry_item, concept_item)

    # Phase 44: 加权计算（新公式）
    resonance_score = (
        industry_strength * 0.25 +
        concept_strength * 0.20 +
        overlap_score * 0.20 +
        semantic_score * 0.20 +
        label_alignment * 0.10 +
        risk_adjustment * 0.05
    )

    # 构建 score_breakdown
    score_breakdown = {
        "industry_strength_score": round(industry_strength, 2),
        "concept_strength_score": round(concept_strength, 2),
        "overlap_score": round(overlap_score, 2),
        "semantic_match_score": round(semantic_score, 2),
        "label_alignment_score": round(label_alignment, 2),
        "risk_adjustment_score": round(risk_adjustment, 2),
        "weights": {
            "industry": 0.25,
            "concept": 0.20,
            "overlap": 0.20,
            "semantic": 0.20,
            "label": 0.10,
            "risk": 0.05,
        },
    }

    return min(100.0, max(0.0, resonance_score)), score_breakdown


def _calculate_industry_strength(industry_item: dict) -> float:
    """计算行业强度分"""
    ranking_score = industry_item.get("ranking_score", 0)
    opportunity_score = industry_item.get("opportunity_score", 0)

    # ranking_score 是 0-1 时放大到 0-100
    if ranking_score <= 1:
        ranking_score *= 100

    # industry_strength_score = min(100, ranking_score * 0.7 + opportunity_score * 30)
    strength = min(100, ranking_score * 0.7 + opportunity_score * 30)
    return strength


def _calculate_concept_strength(concept_item: dict) -> float:
    """计算概念强度分"""
    composite_score = float(concept_item.get("concept_final_rank_score", 0) or 0)
    trend_score = float(concept_item.get("trend_continuation_score", 0) or 0)
    burst_score = float(concept_item.get("short_term_burst_score", 0) or 0)

    # concept_strength_score = min(100, composite_score * 0.5 + trend_score * 0.3 + burst_score * 0.2)
    strength = min(100, composite_score * 0.5 + trend_score * 0.3 + burst_score * 0.2)
    return strength


def _calculate_overlap_score(overlap_count: int) -> float:
    """计算重叠分"""
    if overlap_count >= 10:
        return 100.0
    elif overlap_count >= 5:
        return 75.0
    elif overlap_count >= 2:
        return 50.0
    elif overlap_count >= 1:
        return 25.0
    else:
        return 0.0


def _calculate_label_alignment(industry_item: dict, concept_item: dict) -> float:
    """计算标签对齐分"""
    industry_label = industry_item.get("consensus_label", "")
    concept_label = concept_item.get("agent_consensus_label", "")

    # 判断是否 trend_confirmed
    industry_trend = "trend" in industry_label.lower() and "confirm" in industry_label.lower()
    concept_trend = "trend" in concept_label.lower() and "confirm" in concept_label.lower()

    # 判断是否 strength_limited
    industry_limited = "limited" in industry_label.lower()
    concept_limited = "limited" in concept_label.lower()

    # 判断是否 weak/avoid
    industry_weak = "weak" in industry_label.lower() or "avoid" in industry_label.lower()
    concept_weak = "weak" in concept_label.lower() or "avoid" in concept_label.lower()

    if industry_trend and concept_trend:
        return 100.0
    elif (industry_trend and concept_limited) or (concept_trend and industry_limited):
        return 70.0
    elif industry_weak or concept_weak:
        return 20.0
    else:
        return 50.0


def _calculate_risk_adjustment(industry_item: dict, concept_item: dict) -> float:
    """计算风险调整分"""
    industry_label = industry_item.get("consensus_label", "")
    concept_label = concept_item.get("agent_consensus_label", "")

    # 判断是否 conflicted/weak/avoid/risk_high/risk_extreme
    industry_risk = any(kw in industry_label.lower() for kw in ["conflict", "weak", "avoid", "risk_high", "risk_extreme"])
    concept_risk = any(kw in concept_label.lower() for kw in ["conflict", "weak", "avoid", "risk_high", "risk_extreme"])

    if industry_risk or concept_risk:
        if "risk_high" in industry_label.lower() or "risk_extreme" in industry_label.lower():
            return 0.0
        elif "conflict" in industry_label.lower():
            return 40.0
        else:
            return 20.0
    else:
        return 100.0


def _determine_resonance_type(
    industry_item: dict,
    concept_item: dict,
    overlap_count: int,
    resonance_score: float,
) -> str:
    """确定共振类型"""
    industry_label = industry_item.get("consensus_label", "")
    concept_label = concept_item.get("agent_consensus_label", "")

    industry_trend = "trend" in industry_label.lower() and "confirm" in industry_label.lower()
    concept_trend = "trend" in concept_label.lower() and "confirm" in concept_label.lower()

    concept_burst = float(concept_item.get("short_term_burst_score", 0) or 0) >= 55
    concept_trend_score = float(concept_item.get("trend_continuation_score", 0) or 0) >= 55

    industry_weak = "weak" in industry_label.lower() or "avoid" in industry_label.lower()
    concept_weak = "weak" in concept_label.lower() or "avoid" in concept_label.lower()
    industry_conflict = "conflict" in industry_label.lower()
    concept_conflict = "conflict" in concept_label.lower()

    # weak_or_conflicted
    if industry_weak or concept_weak or industry_conflict or concept_conflict:
        return "weak_or_conflicted"

    # industry_trend_plus_concept_burst
    if industry_trend and concept_burst and resonance_score >= 70:
        return "industry_trend_plus_concept_burst"

    # industry_trend_plus_concept_trend
    if industry_trend and concept_trend_score and resonance_score >= 65:
        return "industry_trend_plus_concept_trend"

    # concept_only_hot
    if not industry_trend and (concept_burst or concept_trend_score) and overlap_count > 0:
        return "concept_only_hot"

    # industry_only_trend
    if industry_trend and not concept_burst and not concept_trend_score:
        return "industry_only_trend"

    # Phase 44: semantic_resonance
    # 如果有语义匹配且共振分较高，标记为 semantic_resonance
    if resonance_score >= 60 and overlap_count == 0:
        return "semantic_resonance"

    return "neutral"


def _determine_confidence(
    resonance_score: float,
    overlap_count: int,
    semantic_score: float,
    risk_adjustment: float,
) -> str:
    """Phase 45: 确定置信度（校准后）"""
    # high:
    #   resonance_score >= 65 (Phase 45: 从 72 降低到 65)
    #   且 semantic_match_score >= 70 或 overlap_score >= 50
    #   且 risk_adjustment_score >= 60
    overlap_score = _calculate_overlap_score(overlap_count)
    if (resonance_score >= 65 and
        (semantic_score >= 70 or overlap_score >= 50) and
        risk_adjustment >= 60):
        return "high"

    # medium:
    #   resonance_score >= 55 (Phase 45: 从 58 降低到 55)
    if resonance_score >= 55:
        return "medium"

    # low:
    return "low"


def _generate_reason(
    industry_item: dict,
    concept_item: dict,
    overlap_count: int,
    resonance_type: str,
    semantic_score: float = 0,
) -> str:
    """生成说明"""
    industry_name = industry_item.get("sector_name", "")
    concept_name = concept_item.get("sector_name", "")
    industry_label = industry_item.get("consensus_label", "")
    concept_label = concept_item.get("agent_consensus_label", "")

    if resonance_type == "industry_trend_plus_concept_burst":
        return f"行业趋势确认，概念短线增强，成分股重叠 {overlap_count} 只"
    elif resonance_type == "industry_trend_plus_concept_trend":
        return f"行业趋势确认，概念趋势增强，成分股重叠 {overlap_count} 只"
    elif resonance_type == "concept_only_hot":
        return f"概念板块活跃，行业趋势一般，成分股重叠 {overlap_count} 只"
    elif resonance_type == "industry_only_trend":
        return f"行业趋势确认，概念板块一般，成分股重叠 {overlap_count} 只"
    elif resonance_type == "semantic_resonance":
        return f"语义映射匹配 (score={semantic_score:.0f})，行业 {industry_name} 与概念 {concept_name} 相关"
    elif resonance_type == "weak_or_conflicted":
        return f"行业或概念存在风险信号"
    else:
        return f"行业 {industry_name} 与概念 {concept_name} 共振，成分股重叠 {overlap_count} 只"
