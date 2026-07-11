"""
Selection Quality 模块

给每日候选股增加 selection_quality 层，将候选股分为不同 bucket，
并生成精简观察池 eligible_watchlist。
所有输出仍为 watch_only，不包含交易建议。
"""

from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# Sector Support Adjustment Policy (第二十七阶段)
# ============================================================

SECTOR_SUPPORT_ADJUSTMENT_POLICY = {
    "trend_follow": "enable_adjustment",
    "short_burst": "disable_adjustment",
    "blocked": "disable_adjustment",
    "divergence_review": "display_only",
    "v2_recovery": "display_only",
    "consensus_confirmed": "display_only",
    "unknown": "display_only",
}


def _infer_opportunity_type(candidate: dict) -> str:
    """推断 opportunity_type。"""
    # 优先从 candidate 直接读取
    opportunity_type = candidate.get("opportunity_type")
    if opportunity_type:
        return opportunity_type

    # 从 selection_bucket 推断
    selection_bucket = candidate.get("selection_bucket", "")
    if selection_bucket == "v2_opportunity":
        return "v2_recovery"
    elif selection_bucket == "divergence_review":
        return "divergence_review"
    elif selection_bucket == "blocked":
        return "blocked"
    elif selection_bucket == "core_watch":
        return "trend_follow"

    # 从 source_pool 推断
    source_pool = candidate.get("source_pool", "")
    if source_pool == "v2_potential":
        return "v2_recovery"
    elif source_pool == "burst_top":
        return "short_burst"
    elif source_pool == "trend_top":
        return "trend_follow"

    # 从 signal_type 推断
    signal_type = candidate.get("signal_type", "")
    if signal_type == "low_final_high_v2":
        return "v2_recovery"
    elif signal_type == "high_final_low_v2":
        return "divergence_review"

    return "unknown"


def _calculate_sector_support_delta(
    sector_support_score: float | None,
    policy: str,
) -> tuple[float, bool, str]:
    """计算 sector_support adjustment delta。

    Returns:
        (delta, applied, reason)
    """
    if policy == "enable_adjustment":
        if sector_support_score is None:
            return 0.0, False, "sector_support_score missing"

        sector_support_val = _safe_float(sector_support_score)
        if sector_support_val >= 75:
            return 5.0, True, "trend_follow sector_support strong"
        elif sector_support_val >= 65:
            return 3.0, True, "trend_follow sector_support moderate"
        elif sector_support_val < 40:
            return -5.0, True, "trend_follow sector_support very_weak"
        elif sector_support_val < 50:
            return -3.0, True, "trend_follow sector_support weak"
        else:
            return 0.0, False, "trend_follow sector_support neutral"

    elif policy == "disable_adjustment":
        return 0.0, False, f"disabled for {policy}"

    elif policy == "display_only":
        return 0.0, False, f"display_only for {policy}"

    else:
        return 0.0, False, "policy unknown"


def classify_stock_candidate(candidate: dict, source_pool: str) -> dict:
    """对单个候选股进行分类。

    Args:
        candidate: 候选股字典
        source_pool: 来源池 (trend_top/burst_top/v2_potential/divergence_review)

    Returns:
        分类结果字典
    """
    code = candidate.get("code", "")
    name = candidate.get("name", "")
    signal_type = candidate.get("signal_type", "unknown")
    data_quality = candidate.get("data_quality", "ok")
    risk_flags = candidate.get("risk_flags", [])

    # 读取 final_score - 保持原始值，不转为 0
    final_score_raw = candidate.get("final_score")
    final_score = _safe_float(final_score_raw) if final_score_raw is not None else None

    # 读取 v2_score - 优先使用 v2_score，fallback 到 factor_composite_shadow_score_v2
    v2_score_raw = candidate.get("v2_score")
    if v2_score_raw is None:
        v2_score_raw = candidate.get("factor_composite_shadow_score_v2")
    v2_score = _safe_float(v2_score_raw) if v2_score_raw is not None else None

    # 用于计算的分数（中性值）
    final_score_for_calc = final_score if final_score is not None else 50.0
    v2_score_for_calc = v2_score if v2_score is not None else 50.0

    # 检查 hard blockers
    hard_blockers = []

    if not code:
        hard_blockers.append("missing_code")
    if not name:
        hard_blockers.append("missing_name")
    if data_quality == "missing":
        hard_blockers.append("data_missing")
    # 只有 final_score 和 v2_score 同时缺失时才触发 scores_missing
    if final_score is None and v2_score is None:
        hard_blockers.append("scores_missing")

    # 检查 severe risk flags
    severe_flags = {"severe", "data_missing", "suspended", "st", "liquidity_missing"}
    for flag in risk_flags:
        if flag in severe_flags:
            hard_blockers.append(f"risk_{flag}")

    # 分类
    selection_bucket = "blocked"
    selection_score = 0.0

    if hard_blockers:
        selection_bucket = "blocked"
        selection_score = 0.0
    elif source_pool == "v2_potential" and signal_type == "low_final_high_v2":
        selection_bucket = "v2_opportunity"
        selection_score = v2_score_for_calc * 0.7 + final_score_for_calc * 0.3
    elif source_pool == "divergence_review" and signal_type == "high_final_low_v2":
        selection_bucket = "divergence_review"
        selection_score = final_score_for_calc * 0.5 + v2_score_for_calc * 0.5
    elif source_pool in ("trend_top", "burst_top") and final_score is not None and final_score >= 55:
        selection_bucket = "core_watch"
        selection_score = final_score_for_calc * 0.7 + v2_score_for_calc * 0.3
    else:
        selection_bucket = "blocked"
        selection_score = 0.0

    # 限制分数范围
    selection_score = max(0.0, min(100.0, selection_score))

    # 软警告
    soft_warnings = []
    if data_quality == "partial":
        soft_warnings.append("partial_data")
    if final_score is not None and final_score < 55 and selection_bucket == "core_watch":
        soft_warnings.append("low_final_score")

    # 新增软警告 (第二十一阶段-B)
    liquidity_score = candidate.get("liquidity_score")
    if liquidity_score is not None and _safe_float(liquidity_score) < 40:
        soft_warnings.append("liquidity_weak")

    chasing_risk_score = candidate.get("chasing_risk_score")
    if chasing_risk_score is not None and _safe_float(chasing_risk_score) >= 80:
        soft_warnings.append("chasing_risk_high")

    drawdown_depth = candidate.get("drawdown_depth_20")
    if drawdown_depth is not None and _safe_float(drawdown_depth) > 35:
        soft_warnings.append("drawdown_deep")

    # 质量确认 (第二十四阶段: sector_support_score)
    quality_confirmations = []
    sector_support_score = candidate.get("sector_support_score")
    if sector_support_score is not None:
        sector_support_val = _safe_float(sector_support_score)
        if sector_support_val >= 65:
            quality_confirmations.append("sector_support_confirmed")
        elif sector_support_val < 50:
            soft_warnings.append("sector_support_weak")
            if sector_support_val < 40:
                soft_warnings.append("sector_support_very_weak")

    # selection_score_adjusted (第二十七阶段: 按 opportunity_type 启用)
    opportunity_type = _infer_opportunity_type(candidate)
    adjustment_policy = SECTOR_SUPPORT_ADJUSTMENT_POLICY.get(opportunity_type, "display_only")

    sector_support_score = candidate.get("sector_support_score")
    # 如果 factor_snapshot 存在且不为 None，尝试从中读取
    factor_snapshot = candidate.get("factor_snapshot")
    if factor_snapshot is not None and sector_support_score is None:
        sector_support_score = factor_snapshot.get("sector_support_score")

    adjustment_delta, adjustment_applied, adjustment_reason = _calculate_sector_support_delta(
        sector_support_score, adjustment_policy
    )

    selection_score_adjusted = selection_score + adjustment_delta if adjustment_applied else selection_score
    selection_score_adjusted = max(0.0, min(100.0, selection_score_adjusted))

    # 确定 quality_level
    if hard_blockers:
        quality_level = "blocked"
    elif soft_warnings:
        quality_level = "warn"
    else:
        quality_level = "ok"

    # ============================================================
    # bars_factor_policy (第三十二阶段)
    # ============================================================
    bars_factor_policy = {}

    # breakout_distance_20
    breakout_distance = candidate.get("breakout_distance_20")
    if factor_snapshot is not None and breakout_distance is None:
        breakout_distance = factor_snapshot.get("breakout_distance_20")
    if breakout_distance is not None:
        breakout_val = _safe_float(breakout_distance)
        if breakout_val <= 5:
            bars_factor_policy["breakout_distance_20"] = {
                "policy": "trigger_candidate",
                "applied": False,
                "reason": "near breakout structure",
            }
            if "breakout_structure_candidate" not in quality_confirmations:
                quality_confirmations.append("breakout_structure_candidate")
        else:
            bars_factor_policy["breakout_distance_20"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "breakout structure not near",
            }
    else:
        bars_factor_policy["breakout_distance_20"] = {
            "policy": "missing",
            "applied": False,
            "reason": "breakout_distance_20 missing",
        }

    # drawdown_depth_20
    drawdown_depth = candidate.get("drawdown_depth_20")
    if factor_snapshot is not None and drawdown_depth is None:
        drawdown_depth = factor_snapshot.get("drawdown_depth_20")
    if drawdown_depth is not None:
        drawdown_val = _safe_float(drawdown_depth)
        if drawdown_val > 35:
            bars_factor_policy["drawdown_depth_20"] = {
                "policy": "soft_warning",
                "applied": True,
                "reason": "deep drawdown risk",
            }
            if "drawdown_deep" not in soft_warnings:
                soft_warnings.append("drawdown_deep")
        else:
            bars_factor_policy["drawdown_depth_20"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "drawdown depth acceptable",
            }
    else:
        bars_factor_policy["drawdown_depth_20"] = {
            "policy": "missing",
            "applied": False,
            "reason": "drawdown_depth_20 missing",
        }

    # liquidity_score
    liquidity_score = candidate.get("liquidity_score")
    if factor_snapshot is not None and liquidity_score is None:
        liquidity_score = factor_snapshot.get("liquidity_score")
    if liquidity_score is not None:
        liquidity_val = _safe_float(liquidity_score)
        if liquidity_val < 40:
            bars_factor_policy["liquidity_score"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "liquidity weak",
            }
            if "liquidity_weak" not in soft_warnings:
                soft_warnings.append("liquidity_weak")
        else:
            bars_factor_policy["liquidity_score"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "liquidity acceptable",
            }
    else:
        bars_factor_policy["liquidity_score"] = {
            "policy": "missing",
            "applied": False,
            "reason": "liquidity_score missing",
        }

    # chasing_risk_score
    chasing_risk = candidate.get("chasing_risk_score")
    if factor_snapshot is not None and chasing_risk is None:
        chasing_risk = factor_snapshot.get("chasing_risk_score")
    if chasing_risk is not None:
        chasing_val = _safe_float(chasing_risk)
        if chasing_val >= 75:
            bars_factor_policy["chasing_risk_score"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "overheat risk high",
            }
            if "overheat_risk_high" not in soft_warnings:
                soft_warnings.append("overheat_risk_high")
        else:
            bars_factor_policy["chasing_risk_score"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "chasing risk acceptable",
            }
    else:
        bars_factor_policy["chasing_risk_score"] = {
            "policy": "missing",
            "applied": False,
            "reason": "chasing_risk_score missing",
        }

    return {
        "code": code,
        "name": name,
        "source_pool": source_pool,
        "selection_bucket": selection_bucket,
        "selection_score": round(selection_score, 2),
        "selection_score_adjusted": round(selection_score_adjusted, 2),
        "sector_support_adjustment_policy": adjustment_policy,
        "sector_support_adjustment_applied": adjustment_applied,
        "sector_support_adjustment_delta": round(adjustment_delta, 2),
        "sector_support_adjustment_reason": adjustment_reason,
        "bars_factor_policy": bars_factor_policy,
        "quality_level": quality_level,
        "hard_blockers": hard_blockers,
        "soft_warnings": soft_warnings,
        "quality_confirmations": quality_confirmations,
        "risk_flags": risk_flags,
        "action_state": "watch_only",
    }


def build_eligible_watchlist(stock_pools: dict, top_n: int = 10) -> dict:
    """构建精简观察池。

    Args:
        stock_pools: daily_decision_summary 中的 stock_pools
        top_n: 每个 bucket 最多保留的股票数量

    Returns:
        分类后的候选池和 selection_quality
    """
    # 收集所有候选股
    all_candidates: list[dict] = []

    # 按优先级处理各池
    pool_priority = {
        "v2_potential": 1,
        "core_watch": 2,
        "divergence_review": 3,
        "blocked": 4,
    }

    # 首先分类 core_watch 和 blocked
    for pool_name in ["trend_top", "burst_top"]:
        for candidate in stock_pools.get(pool_name, []):
            classified = classify_stock_candidate(candidate, pool_name)
            all_candidates.append(classified)

    # 分类 v2_potential
    for candidate in stock_pools.get("v2_potential", []):
        classified = classify_stock_candidate(candidate, "v2_potential")
        all_candidates.append(classified)

    # 分类 divergence_review
    for candidate in stock_pools.get("divergence_review", []):
        classified = classify_stock_candidate(candidate, "divergence_review")
        all_candidates.append(classified)

    # 去重：同一 code 只保留优先级最高的
    seen_codes: dict[str, dict] = {}
    for candidate in all_candidates:
        code = candidate.get("code", "")
        if not code:
            continue

        bucket = candidate.get("selection_bucket", "blocked")
        priority = pool_priority.get(bucket, 5)

        if code not in seen_codes:
            seen_codes[code] = candidate
            seen_codes[code]["_priority"] = priority
        else:
            # 如果新候选优先级更高，替换
            existing_priority = seen_codes[code].get("_priority", 5)
            if priority < existing_priority:
                # 记录来源历史
                old_source = seen_codes[code].get("source_pool", "")
                candidate["source_pool_history"] = [old_source, candidate.get("source_pool", "")]
                seen_codes[code] = candidate
                seen_codes[code]["_priority"] = priority
            else:
                # 记录来源历史
                if "source_pool_history" not in seen_codes[code]:
                    seen_codes[code]["source_pool_history"] = []
                seen_codes[code]["source_pool_history"].append(candidate.get("source_pool", ""))

    # 按 bucket 分组
    result = {
        "eligible_watchlist": [],
        "core_watch": [],
        "v2_opportunity": [],
        "divergence_review": [],
        "blocked": [],
    }

    all_hard_blockers: list[str] = []
    all_soft_warnings: list[str] = []

    for code, candidate in seen_codes.items():
        bucket = candidate.get("selection_bucket", "blocked")

        # 清理内部字段
        clean_candidate = {k: v for k, v in candidate.items() if not k.startswith("_")}

        if bucket == "core_watch":
            result["core_watch"].append(clean_candidate)
        elif bucket == "v2_opportunity":
            result["v2_opportunity"].append(clean_candidate)
        elif bucket == "divergence_review":
            result["divergence_review"].append(clean_candidate)
        elif bucket == "blocked":
            result["blocked"].append(clean_candidate)

        # 收集 blockers 和 warnings
        all_hard_blockers.extend(candidate.get("hard_blockers", []))
        all_soft_warnings.extend(candidate.get("soft_warnings", []))

    # 构建 eligible_watchlist：排除 blocked，按 selection_score 排序
    eligible = []
    for bucket in ["v2_opportunity", "core_watch", "divergence_review"]:
        for candidate in result[bucket]:
            eligible.append(candidate)

    # 按 selection_score 排序
    eligible.sort(key=lambda x: x.get("selection_score", 0), reverse=True)
    result["eligible_watchlist"] = eligible[:top_n * 2]  # 保留更多用于展示

    # 限制各池大小
    for bucket in ["core_watch", "v2_opportunity", "divergence_review", "blocked"]:
        result[bucket] = result[bucket][:top_n]

    # 计算 selection_quality
    eligible_count = len(result["eligible_watchlist"])
    blocked_count = len(result["blocked"])

    # 判断 pool_quality
    if eligible_count == 0 or len(all_hard_blockers) >= 5:
        pool_quality = "fail"
    elif blocked_count > eligible_count or all_soft_warnings:
        pool_quality = "warn"
    else:
        pool_quality = "ok"

    selection_quality = {
        "eligible_count": eligible_count,
        "blocked_count": blocked_count,
        "pool_quality": pool_quality,
        "hard_blockers": list(set(all_hard_blockers)),
        "soft_warnings": list(set(all_soft_warnings)),
    }

    return {
        "eligible_watchlist": result["eligible_watchlist"],
        "core_watch": result["core_watch"],
        "v2_opportunity": result["v2_opportunity"],
        "divergence_review": result["divergence_review"],
        "blocked": result["blocked"],
        "selection_quality": selection_quality,
    }
