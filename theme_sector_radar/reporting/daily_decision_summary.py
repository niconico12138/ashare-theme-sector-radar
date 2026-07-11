"""
Daily Decision Summary 模块

生成机器友好的 daily decision summary JSON，用于日报展示和流程自动化。
所有模式均为 watch_only，不含交易建议。
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


def _field(row: dict, *keys, default="-"):
    """Safely get a field by trying multiple key names."""
    for k in keys:
        v = row.get(k)
        if v is not None and v != "":
            return v
    return default


def normalize_stock_item(raw: dict, source_pool: str, rank: int | None = None) -> dict:
    """规范化股票字段，确保字段映射正确。

    从多种字段名中读取数据，保持缺失值为 None（不转为 0）。
    """
    # 读取 code
    code = raw.get("code") or raw.get("stock_code") or raw.get("symbol") or ""

    # 读取 name
    name = raw.get("name") or raw.get("stock_name") or ""

    # 读取 sector_name
    sector_name = raw.get("sector_name") or raw.get("industry") or raw.get("concept_name") or raw.get("board_name") or ""

    # 读取 final_score - 保持 None，不转为 0
    final_score = raw.get("final_score") if raw.get("final_score") is not None else None
    if final_score is not None:
        final_score = _safe_float(final_score)

    # 读取 v2_score - 优先使用 v2_score，fallback 到 factor_composite_shadow_score_v2
    v2_score = raw.get("v2_score")
    if v2_score is None:
        v2_score = raw.get("factor_composite_shadow_score_v2")
    if v2_score is not None:
        v2_score = _safe_float(v2_score)

    # 保留 factor_composite_shadow_score_v2
    factor_composite_shadow_score_v2 = raw.get("factor_composite_shadow_score_v2")
    if factor_composite_shadow_score_v2 is not None:
        factor_composite_shadow_score_v2 = _safe_float(factor_composite_shadow_score_v2)

    # 读取 signal_type
    signal_type = raw.get("signal_type", "unknown")

    # 映射 signal_type
    reason = raw.get("reason", "")
    if reason == "low_final_high_v2":
        signal_type = "low_final_high_v2"
    elif reason == "high_final_low_v2":
        signal_type = "high_final_low_v2"
    elif reason == "high_v2_risk_confirmed":
        signal_type = "high_v2"

    # 读取 factor_snapshot
    factor_snapshot = raw.get("factor_snapshot")

    # 读取 risk_flags
    risk_flags = raw.get("risk_flags", [])

    # 读取 sector_support_score
    sector_support_score = raw.get("sector_support_score")
    if sector_support_score is not None:
        sector_support_score = _safe_float(sector_support_score)

    # 读取 data_quality
    data_quality = raw.get("data_quality", "ok")

    return {
        "rank": rank or raw.get("rank", 0),
        "code": code,
        "name": name,
        "sector_name": sector_name,
        "source_pool": source_pool,
        "final_score": final_score,
        "v2_score": v2_score,
        "factor_composite_shadow_score_v2": factor_composite_shadow_score_v2,
        "signal_type": signal_type,
        "risk_flags": risk_flags,
        "data_quality": data_quality,
        "factor_snapshot": factor_snapshot,
        "sector_support_score": sector_support_score,
        "action_state": "watch_only",
    }


def build_daily_decision_summary(
    as_of: str,
    unified_report: dict,
    sectors: list[dict],
    concepts: list[dict],
    v2_monitor: dict | None = None,
    top_n: int = 5,
) -> dict:
    """构建 daily decision summary。

    Args:
        as_of: 日期
        unified_report: unified pipeline report
        sectors: 行业研究数据
        concepts: 概念排名数据
        v2_monitor: V2 Shadow Monitor 数据（可选）
        top_n: 每个池最多展示的股票数量

    Returns:
        decision summary 字典
    """
    # 运行状态
    health = unified_report.get("run_health", {})
    dq = unified_report.get("data_quality", {})

    health_status = health.get("status", "unknown")
    dq_status = dq.get("status", "unknown")

    # allow_observation: run_health 或 data_quality 为 fail 时为 false
    allow_observation = health_status != "fail" and dq_status != "fail"

    blockers = []
    warnings = []

    if health_status == "fail":
        blockers.append("run_health fail")
    if dq_status == "fail":
        blockers.append("data_quality fail")

    health_reasons = health.get("reasons", [])
    if health_reasons:
        warnings.extend(health_reasons)

    dq_warns = dq.get("warnings", [])
    if dq_warns:
        warnings.extend(dq_warns)

    run_status = {
        "data_quality": dq_status,
        "run_health": health_status,
        "market_regime": "unknown",
        "allow_observation": allow_observation,
        "blockers": blockers,
        "warnings": warnings,
    }

    # 板块聚焦
    industry_items = []
    for i, s in enumerate(sectors[:top_n], 1):
        industry_items.append({
            "rank": i,
            "name": _field(s, "sector_name", "name", "industry"),
            "score": _safe_float(s.get("ranking_score")),
            "label": _field(s, "consensus_label", "agent_label", "label"),
            "risk_level": "unknown",
            "confidence": _safe_float(s.get("confidence_score")),
        })

    concept_items = []
    for i, r in enumerate(concepts[:top_n], 1):
        concept_items.append({
            "rank": i,
            "name": _field(r, "sector_name", "name", "concept"),
            "score": _safe_float(r.get("concept_final_rank_score", r.get("composite_score"))),
            "label": _field(r, "agent_consensus_label", "agent_label"),
            "trend_score": _safe_float(r.get("trend_continuation_score", r.get("trend_score"))),
            "burst_score": _safe_float(r.get("short_term_burst_score", r.get("burst_score"))),
            "confidence": _safe_float(r.get("confidence_score")),
        })

    sector_focus = {
        "industries": industry_items,
        "concepts": concept_items,
    }

    # 股票池
    trend_stocks = unified_report.get("trend_top_stocks", [])[:top_n]
    burst_stocks = unified_report.get("burst_top_stocks", [])[:top_n]

    trend_items = []
    for i, s in enumerate(trend_stocks, 1):
        item = normalize_stock_item(s, "trend_top", i)
        item["signal_type"] = "trend"
        trend_items.append(item)

    burst_items = []
    for i, s in enumerate(burst_stocks, 1):
        item = normalize_stock_item(s, "burst_top", i)
        item["signal_type"] = "burst"
        burst_items.append(item)

    # V2 潜力观察和分歧复核
    v2_potential_items = []
    divergence_review_items = []

    if v2_monitor:
        divergence_samples = v2_monitor.get("divergence_samples", [])

        for s in divergence_samples:
            # 确定 source_pool
            reason = s.get("reason", "")
            if reason == "low_final_high_v2":
                source_pool = "v2_potential"
                rank = len(v2_potential_items) + 1
            elif reason == "high_final_low_v2":
                source_pool = "divergence_review"
                rank = len(divergence_review_items) + 1
            else:
                source_pool = "v2_potential"
                rank = len(v2_potential_items) + 1

            # 使用 normalize_stock_item 规范化字段
            item = normalize_stock_item(s, source_pool, rank)

            if reason == "low_final_high_v2" and len(v2_potential_items) < top_n:
                v2_potential_items.append(item)
            elif reason == "high_final_low_v2" and len(divergence_review_items) < top_n:
                divergence_review_items.append(item)

    stock_pools = {
        "trend_top": trend_items,
        "burst_top": burst_items,
        "v2_potential": v2_potential_items,
        "divergence_review": divergence_review_items,
    }

    # 构建 eligible_watchlist 和 selection_quality
    try:
        from theme_sector_radar.reporting.selection_quality import build_eligible_watchlist
        watchlist_result = build_eligible_watchlist(stock_pools, top_n)

        # 合并到 stock_pools
        stock_pools["eligible_watchlist"] = watchlist_result["eligible_watchlist"]
        stock_pools["core_watch"] = watchlist_result["core_watch"]
        stock_pools["blocked"] = watchlist_result["blocked"]

        selection_quality = watchlist_result["selection_quality"]

        # 优化 allow_observation 逻辑
        # 只有以下情况 false：
        # - run_health == fail 且存在 hard blocker
        # - data_quality == fail 且 eligible_count == 0
        # - selection_quality.pool_quality == fail
        if (health_status == "fail" and selection_quality["hard_blockers"]) or \
           (dq_status == "fail" and selection_quality["eligible_count"] == 0) or \
           selection_quality["pool_quality"] == "fail":
            run_status["allow_observation"] = False

        # 添加 soft_warnings 到 run_status
        if selection_quality["soft_warnings"]:
            run_status["warnings"].extend(selection_quality["soft_warnings"])

        # 为每只股票补充画像和解释
        try:
            from theme_sector_radar.reporting.stock_profile import build_stock_profile
            from theme_sector_radar.reporting.stock_explanation import build_stock_explanation

            for pool_name in ["eligible_watchlist", "core_watch", "v2_opportunity", "divergence_review", "blocked"]:
                for item in stock_pools.get(pool_name, []):
                    try:
                        profile = build_stock_profile(item)
                        explanation = build_stock_explanation(item, profile)
                        item["stock_profile"] = profile
                        item.update(explanation)
                    except Exception:
                        # 画像生成失败不影响 summary
                        pass
        except Exception:
            pass

    except Exception:
        # 降级处理
        selection_quality = {
            "eligible_count": 0,
            "blocked_count": 0,
            "pool_quality": "unknown",
            "hard_blockers": [],
            "soft_warnings": [],
        }

    # 风险摘要
    risk_summary = {
        "data_quality_warnings": dq_warns,
        "run_health_reasons": health_reasons,
        "notes": [],
    }

    return {
        "schema_version": "1.0",
        "as_of": as_of,
        "decision_mode": "watch_only",
        "run_status": run_status,
        "sector_focus": sector_focus,
        "stock_pools": stock_pools,
        "selection_quality": selection_quality,
        "risk_summary": risk_summary,
    }
