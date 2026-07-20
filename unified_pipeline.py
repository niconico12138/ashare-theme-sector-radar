#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联合选股管线（Unified Pipeline）

串联板块雷达 + 板块-个股桥接 + 个股量化打分，
输出趋势板块 Top10 个股和短线板块 Top10 个股。

架构:
  Step 1: Theme Sector Radar 板块评分（已有报告 / 新生成）
  Step 2: sector_stock_bridge 板块→成分股+关联度
  Step 3: 个股量化评分（降级: 关联度+涨幅+成交额；预留Qlib接口）
  Step 4: 综合排序 + 输出 JSON/Markdown

CLI:
  python unified_pipeline.py --as-of 2026-07-01 --trend-top-n 5 --burst-top-n 5
"""

import copy
import hashlib
import json
import logging
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from typing import Any, Dict, List, Optional, Tuple

from theme_sector_radar.data.bars_data_router import AutoBarsClient

# ============================================================
# 代理环境变量清理
# ============================================================

for _k in list(os.environ.keys()):
    if _k.upper().endswith("_PROXY") or _k.upper().endswith("_PROXY_"):
        del os.environ[_k]

logger = logging.getLogger(__name__)

# ============================================================
# HTTP 客户端（懒加载）
# ============================================================

_http_client = None


def _get_http_client():
    """懒加载 MarketDataHttpClient 单例。"""
    global _http_client
    if _http_client is None:
        try:
            from theme_sector_radar.data.market_data_http_client import (
                MarketDataHttpClient,
            )

            _http_client = MarketDataHttpClient()
        except ImportError:
            return None
    return _http_client


def _http_client_is_healthy(http_client) -> bool:
    """Return False quickly when market_data_service is unavailable.

    Without this gate, callers can spend minutes retrying every per-stock
    endpoint after /health would already have shown the local API is down.
    """
    if http_client is None:
        return False
    checker = getattr(http_client, "health_check", None) or getattr(http_client, "health", None)
    if not callable(checker):
        return True
    try:
        checker()
        return True
    except Exception as exc:
        logger.warning("market_data_service health check failed; using local fallback: %s", exc)
        return False


def _get_sector_burst_score(sector: Dict[str, Any]) -> float:
    """Return the short-term sector score across legacy and current field names."""
    value = sector.get("burst_score")
    if value is None:
        value = sector.get("short_term_burst_score", 0)
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _build_direction_linkage_summary(
    candidates: List[Dict[str, Any]],
    selection: Dict[str, Any],
    history: Dict[str, Any],
    confirmation_sectors: List[Any],
) -> Dict[str, Any]:
    """Build a compact, read-only audit summary for the shadow branch."""
    sector_groups = {"core": set(), "supplemental": set()}
    status_counts: Dict[str, int] = {}
    for candidate in candidates:
        tier = str(candidate.get("candidate_tier") or "")
        sector_name = str(candidate.get("sector_name") or "").strip()
        if tier in sector_groups and sector_name:
            sector_groups[tier].add(sector_name)
        linkage = candidate.get("linkage_v2_shadow") or {}
        status = str(linkage.get("status") or "missing")
        status_counts[status] = status_counts.get(status, 0) + 1

    confirmation_names = set()
    for sector in confirmation_sectors:
        if isinstance(sector, dict):
            name = str(sector.get("sector_name") or sector.get("name") or "").strip()
        else:
            name = str(sector or "").strip()
        if name:
            confirmation_names.add(name)

    groups = {
        "core": sorted(sector_groups["core"]),
        "supplemental": sorted(sector_groups["supplemental"]),
        "confirmation_required": sorted(confirmation_names),
    }
    return {
        "sector_groups": groups,
        "sector_group_counts": {key: len(value) for key, value in groups.items()},
        "candidate_count": len(candidates),
        "linkage_v2_status_counts": dict(sorted(status_counts.items())),
        "selected_count": int(selection.get("selected_count") or 0),
        "history_sector_count": int(history.get("sector_count") or 0),
    }


# ============================================================
# 项目路径
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from sector_stock_bridge import (
    find_latest_report,
    load_sector_scores,
    extract_top_sectors,
    find_cross_sectors,
    run_bridge,
    validate_explicit_score_report,
    DEFAULT_MIN_RELEVANCE,
    DEFAULT_TREND_TOP_N,
    DEFAULT_BURST_TOP_N,
)
from theme_sector_radar.history.sector_trend_history import (
    load_sector_trend_history,
)
from theme_sector_radar.models import SectorType
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256
from theme_sector_radar.scoring.stock_sector_linkage import (
    build_formal_candidate_selection,
    calculate_stock_sector_linkage_v2_shadow,
    relative_strength_score_from_returns,
    returns_by_date_from_bars,
    select_direction_linkage_v2_shadow_stocks,
)

DEFAULT_SECTOR_CLUSTER_MAP_PATH = PROJECT_ROOT / "config" / "path_a_sector_clusters.json"


def _activate_formal_candidate_chain(
    *,
    candidate_chain: str,
    direction_source: Dict[str, Any],
    linkage_selection: Dict[str, Any],
    legacy_candidates: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Resolve the active paper candidate chain without mutating score fields."""
    if candidate_chain == "legacy":
        selected = []
        seen_codes = set()
        for source in legacy_candidates or []:
            if source.get("sector_type") not in {None, "industry"}:
                raise ValueError("formal candidate row must use industry sector_type")
            source = copy.deepcopy(source)
            source.setdefault("sector_type", "industry")
            code = str(source.get("code") or "").strip()
            if not code or code in seen_codes:
                continue
            selected.append(source)
            seen_codes.add(code)
        return {
            "schema_version": "formal_candidate_selection.v1",
            "mode": "paper_shadow_research_only",
            "candidate_chain": "legacy",
            "status": "legacy_active_for_paper_research",
            "fallback_used": False,
            "direction_source": {},
            "linkage_source": {},
            "selected_count": len(selected),
            "selected": selected,
            "error": None,
            "disclaimer": "No broker connection and no live order instruction.",
        }
    if candidate_chain != "direction_linkage_v2":
        raise ValueError(
            "candidate_chain must be one of: legacy, direction_linkage_v2"
        )
    return build_formal_candidate_selection(
        direction_source=direction_source,
        linkage_selection=linkage_selection,
    )


def load_sector_cluster_map(path: str | Path) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """Load a strict, SHA-bound sector-to-cluster research contract."""
    source_path = Path(path).expanduser().resolve()
    document, source_sha256 = load_strict_json_with_sha256(source_path)
    if document.get("schema_version") != "path_a_sector_cluster_map.v1":
        raise ValueError("unsupported sector cluster map schema_version")
    if document.get("mode") != "paper_shadow_research_only":
        raise ValueError("sector cluster map must be paper_shadow_research_only")
    clusters = document.get("clusters")
    if not isinstance(clusters, dict) or not clusters:
        raise ValueError("sector cluster map clusters must be a non-empty object")
    mapping: Dict[str, str] = {}
    for raw_cluster, raw_sectors in clusters.items():
        cluster = str(raw_cluster or "").strip()
        if not cluster or not isinstance(raw_sectors, list) or not raw_sectors:
            raise ValueError("each sector cluster must have a name and sectors")
        for raw_sector in raw_sectors:
            sector = str(raw_sector or "").strip()
            if not sector:
                raise ValueError("sector cluster members must be non-empty")
            if sector in mapping:
                raise ValueError(f"sector appears in multiple clusters: {sector}")
            mapping[sector] = cluster
    canonical_mapping = json.dumps(
        mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return mapping, {
        "schema_version": document["schema_version"],
        "mode": document["mode"],
        "status": "ok",
        "path": str(source_path),
        "sha256": source_sha256,
        "mapping_sha256": hashlib.sha256(canonical_mapping).hexdigest(),
        "cluster_count": len(clusters),
        "mapped_sector_count": len(mapping),
        "mapping": dict(sorted(mapping.items())),
        "disclaimer": "No broker connection and no live order instruction.",
    }

# ============================================================
# 量化评分（增强方案 + 降级方案）
# ============================================================


def _compute_enhanced_quant_score(stock: Dict, bars: List[Dict]) -> Tuple[float, Dict[str, float]]:
    """增强量化评分 v2：当 HTTP API 返回足够 K 线数据时使用。

    v2 因子体系（满分 104 → 归一化到 100）：

    一、动量质量（30分）
      - 1日涨幅分（8）：单日涨幅，+5%满分
      - 5日动量质量（8）：5日收益/5日波动率（Sharpe-like）
      - MA排列分（8）：MA5>MA10>MA20=满分
      - 涨幅持续性（6）：近5日上涨天数占比

    二、估值合理（12分）
      - PE相对分（8）：PE vs 行业中位数
      - PB评分（4）：PB适中

    三、流动性（22分）
      - 市值适中分（8）：行业内相对市值
      - 量能趋势（8）：5日均量/20日均量，>1.2=满分
      - 日均成交额（6）：≥5亿=6

    四、风险控制（14分）
      - 20日最大回撤（8）：≤2%=满分
      - 20日波动率（6）：越低越好

    五、资金面（14分）
      - 主力净流入（8）：金额标准化
      - 资金流持续性（6）：近期流入天数

    六、板块匹配（12分）
      - 板块趋势分（8）：sector_trend_score/100
      - 板块轮动分（4）：sector_burst_score/100

    Returns:
        (归一化分数 0~100, 因子明细字典)
    """
    breakdown = {}
    raw_score = 0.0
    raw_max = 104.0  # 总分上限
    n = len(bars)

    # ============================================================
    # 一、动量质量（30分）
    # ============================================================

    # 1.1 1日涨幅分（8分）
    change = stock.get("change_pct", 0) or 0
    if change > 0:
        s1d = min(change / 5.0, 1.0) * 8
    elif change < -3:
        s1d = 0
    else:
        s1d = max(0, (change + 3) / 3) * 4  # -3%~0% 给 0~4 分
    raw_score += s1d
    breakdown["1d_momentum"] = round(s1d, 2)

    # 1.2 5日动量质量（8分）— Sharpe-like: 5d_ret / 5d_volatility
    s5d_quality = 0.0
    if n >= 5:
        closes_5 = [b.get("close", 0) for b in bars[-6:]]
        rets_5 = []
        for i in range(1, len(closes_5)):
            if closes_5[i - 1] > 0:
                rets_5.append((closes_5[i] - closes_5[i - 1]) / closes_5[i - 1])
        if rets_5:
            mean_ret = sum(rets_5) / len(rets_5)
            if len(rets_5) > 1:
                var = sum((r - mean_ret) ** 2 for r in rets_5) / len(rets_5)
                std = var ** 0.5
            else:
                std = abs(mean_ret) if mean_ret != 0 else 0.001
            if std > 0:
                sharpe = mean_ret / std
                # sharpe > 1.5 → 满分, 0~1.5 线性
                s5d_quality = min(max(sharpe, 0) / 1.5, 1.0) * 8
    raw_score += s5d_quality
    breakdown["5d_momentum_quality"] = round(s5d_quality, 2)

    # 1.3 MA排列分（8分）
    ma_score = 0.0
    if n >= 20:
        closes = [b.get("close", 0) for b in bars]
        ma5 = sum(closes[-5:]) / 5
        ma10 = sum(closes[-10:]) / 10
        ma20 = sum(closes[-20:]) / 20
        if ma5 > ma10 > ma20 and ma20 > 0:
            ma_score = 8  # 完美多头排列
        elif ma5 > ma10 and ma10 > 0:
            ma_score = 5  # 短期多头
        elif ma5 > ma20 and ma20 > 0:
            ma_score = 3  # 弱多头
    elif n >= 10:
        closes = [b.get("close", 0) for b in bars]
        ma5 = sum(closes[-5:]) / 5
        ma10 = sum(closes[-10:]) / 10
        if ma5 > ma10 and ma10 > 0:
            ma_score = 4  # 降级：只看短期
    raw_score += ma_score
    breakdown["ma_alignment"] = round(ma_score, 2)

    # 1.4 涨幅持续性（6分）
    continuity = 0.0
    if n >= 5:
        recent_5 = bars[-5:]
        up_days = sum(1 for b in recent_5 if (b.get("close", 0) or 0) > (b.get("open", 0) or 0))
        continuity = (up_days / 5) * 6
    raw_score += continuity
    breakdown["continuity"] = round(continuity, 2)

    # ============================================================
    # 二、估值合理（12分）
    # ============================================================

    # 2.1 PE相对分（8分）
    pe_score = 0.0
    pe = stock.get("pe", 0) or 0
    sector_pe_median = stock.get("_sector_pe_median")
    if pe > 0:
        if sector_pe_median and sector_pe_median > 0:
            # 行业内相对估值：越接近中位数越好
            pe_ratio = pe / sector_pe_median
            if 0.5 <= pe_ratio <= 1.5:
                pe_score = 8  # 合理区间
            elif 0.3 <= pe_ratio <= 2.0:
                pe_score = 5  # 可接受
            elif pe_ratio < 3.0:
                pe_score = 2  # 偏离较大
        else:
            # 无行业中位数，用绝对值降级
            if pe <= 30:
                pe_score = 6
            elif pe <= 50:
                pe_score = 4
            elif pe <= 100:
                pe_score = 2
    raw_score += pe_score
    breakdown["pe_score"] = round(pe_score, 2)

    # 2.2 PB评分（4分）
    pb_score = 0.0
    pb = stock.get("pb", 0) or 0
    if pb > 0:
        if 0.5 <= pb <= 5:
            pb_score = 4
        elif 0.3 <= pb <= 10:
            pb_score = 2
    raw_score += pb_score
    breakdown["pb_score"] = round(pb_score, 2)

    # ============================================================
    # 三、流动性（22分）
    # ============================================================

    # 3.1 市值适中分（8分）
    mv_score = 0.0
    mv = stock.get("total_mv", 0) or 0
    sector_mv_median = stock.get("_sector_mv_median")
    if mv > 0:
        if sector_mv_median and sector_mv_median > 0:
            # 行业内相对市值
            mv_ratio = mv / sector_mv_median
            if 0.3 <= mv_ratio <= 3.0:
                mv_score = 8  # 行业内适中
            elif 0.1 <= mv_ratio <= 10.0:
                mv_score = 5
            else:
                mv_score = 2
        else:
            # 无行业中位数，用绝对值
            if 50 <= mv <= 500:
                mv_score = 8
            elif 20 <= mv < 50 or 500 < mv <= 1000:
                mv_score = 6
            elif 10 <= mv < 20 or 1000 < mv <= 2000:
                mv_score = 4
            elif mv > 2000:
                mv_score = 3
            else:
                mv_score = 2
    raw_score += mv_score
    breakdown["market_cap"] = round(mv_score, 2)

    # 3.2 量能趋势（8分）— 5日均量/20日均量
    vol_trend = 0.0
    if n >= 20:
        vol_5 = [b.get("volume", 0) or 0 for b in bars[-5:]]
        vol_20 = [b.get("volume", 0) or 0 for b in bars[-20:]]
        avg_5 = sum(vol_5) / len(vol_5) if vol_5 else 0
        avg_20 = sum(vol_20) / len(vol_20) if vol_20 else 0
        if avg_20 > 0:
            vol_ratio = avg_5 / avg_20
            if vol_ratio >= 1.2:
                vol_trend = 8  # 明显放量
            elif vol_ratio >= 1.0:
                vol_trend = 6  # 温和放量
            elif vol_ratio >= 0.8:
                vol_trend = 3  # 轻微缩量
            # < 0.8: 0
    elif n >= 5:
        # 降级：只有5天数据，给基础分
        vol_trend = 2
    raw_score += vol_trend
    breakdown["volume_trend"] = round(vol_trend, 2)

    # 3.3 日均成交额（6分）
    amount_score = 0.0
    if n >= 5:
        recent_5_amounts = [b.get("amount", 0) or 0 for b in bars[-5:]]
        avg_amount = sum(recent_5_amounts) / len(recent_5_amounts)
        if avg_amount >= 5e8:
            amount_score = 6
        elif avg_amount >= 2e8:
            amount_score = 4
        elif avg_amount >= 1e8:
            amount_score = 3
        elif avg_amount >= 5e7:
            amount_score = 2
        elif avg_amount > 0:
            amount_score = 1
    raw_score += amount_score
    breakdown["avg_amount"] = round(amount_score, 2)

    # ============================================================
    # 四、风险控制（14分）
    # ============================================================

    # 4.1 20日最大回撤（8分）
    drawdown_score = 0.0
    if n >= 3:
        peak = bars[0].get("close", 0) or 0
        max_dd_pct = 0.0
        for b in bars:
            close_v = b.get("close", 0) or 0
            if close_v > peak:
                peak = close_v
            if peak > 0:
                dd = (peak - close_v) / peak * 100
                if dd > max_dd_pct:
                    max_dd_pct = dd
        if max_dd_pct <= 2:
            drawdown_score = 8
        elif max_dd_pct <= 5:
            drawdown_score = 6
        elif max_dd_pct <= 10:
            drawdown_score = 4
        elif max_dd_pct <= 15:
            drawdown_score = 2
    raw_score += drawdown_score
    breakdown["drawdown"] = round(drawdown_score, 2)

    # 4.2 20日波动率（6分）— 日收益率标准差
    vol_score = 0.0
    if n >= 10:
        closes = [b.get("close", 0) or 0 for b in bars]
        rets = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
        if rets and len(rets) > 1:
            mean_r = sum(rets) / len(rets)
            var_r = sum((r - mean_r) ** 2 for r in rets) / len(rets)
            daily_vol = var_r ** 0.5
            annual_vol = daily_vol * (252 ** 0.5)
            # 年化波动率 < 20% → 满分, < 30% → 4, < 50% → 2
            if annual_vol <= 0.20:
                vol_score = 6
            elif annual_vol <= 0.30:
                vol_score = 4
            elif annual_vol <= 0.50:
                vol_score = 2
    raw_score += vol_score
    breakdown["volatility"] = round(vol_score, 2)

    # ============================================================
    # 五、资金面（14分）
    # ============================================================

    # 5.1 主力净流入（8分）
    ff_score = 0.0
    ff = stock.get("_fund_flow")
    if ff and isinstance(ff, dict) and ff.get("available") is not False:
        main_inflow = ff.get("main_net_inflow")
        if main_inflow is not None and isinstance(main_inflow, (int, float)):
            yi = float(main_inflow) / 1e8  # 转为亿
            if yi > 0:
                ff_score = min(yi / 2.0, 8.0)  # 2亿=满分
            elif yi < -1:
                ff_score = 0  # 大幅流出
            else:
                ff_score = 2  # 小幅流出不扣太多
    raw_score += ff_score
    breakdown["fund_flow"] = round(ff_score, 2)

    # 5.2 资金流持续性（6分）— 需要多日数据，单日降级
    ff_persist = 0.0
    if ff and isinstance(ff, dict):
        # 如果有 recent_days 数据
        recent_days = ff.get("recent_inflow_days")
        if recent_days is not None and isinstance(recent_days, (int, float)):
            ff_persist = min(recent_days / 3.0, 1.0) * 6
        else:
            # 单日降级：有正流入给3分
            main_inflow = ff.get("main_net_inflow")
            if main_inflow is not None and isinstance(main_inflow, (int, float)) and main_inflow > 0:
                ff_persist = 3
    raw_score += ff_persist
    breakdown["fund_flow_persistence"] = round(ff_persist, 2)

    # ============================================================
    # 六、板块匹配（12分）
    # ============================================================

    # 6.1 板块趋势分（8分）
    sector_trend = stock.get("sector_trend_score", 0) or 0
    if sector_trend > 0:
        s_trend = min(sector_trend / 100.0, 1.0) * 8
    else:
        s_trend = 0
    raw_score += s_trend
    breakdown["sector_trend"] = round(s_trend, 2)

    # 6.2 板块轮动分（4分）
    sector_burst = stock.get("sector_burst_score", 0) or 0
    if sector_burst > 0:
        s_burst = min(sector_burst / 100.0, 1.0) * 4
    else:
        s_burst = 0
    raw_score += s_burst
    breakdown["sector_burst"] = round(s_burst, 2)

    # ============================================================
    # 归一化到 0~100
    # ============================================================
    normalized = round(min(raw_score / raw_max * 100, 100.0), 2)
    breakdown["raw_total"] = round(raw_score, 2)
    breakdown["raw_max"] = raw_max
    breakdown["normalized"] = normalized

    return normalized, breakdown


def _compute_fallback_quant_score(stock: Dict) -> Tuple[float, Dict[str, float]]:
    """
    降级量化评分 v2：当 K 线数据不可用时使用。

    基于可用的实时行情数据（无 K 线）：
    - 涨幅分（0~15）：单日涨幅
    - 市值适中分（0~15）：市值区间
    - PE 估值分（0~12）：PE 绝对值
    - PB 估值分（0~8）：PB 绝对值
    - 板块趋势分（0~8）：板块趋势评分
    - 板块短线分（0~4）：板块短线评分
    - 资金流分（0~8）：主力净流入

    Returns:
        (归一化分数 0~100, 因子明细字典)
    """
    breakdown = {}
    raw_score = 0.0
    raw_max = 70.0  # 降级模式总分上限

    # 1. 涨幅分（15分）
    change = stock.get("change_pct", 0) or 0
    if change > 0:
        s_change = min(change / 5.0, 1.0) * 15
    elif change < -3:
        s_change = 0
    else:
        s_change = max(0, (change + 3) / 3) * 5
    raw_score += s_change
    breakdown["change_score"] = round(s_change, 2)

    # 2. 市值适中分（15分）
    mv = stock.get("total_mv", 0) or 0
    mv_score = 0.0
    if mv > 0:
        if 50 <= mv <= 500:
            mv_score = 15
        elif 20 <= mv < 50 or 500 < mv <= 1000:
            mv_score = 10
        elif 10 <= mv < 20 or 1000 < mv <= 2000:
            mv_score = 7
        elif mv > 2000:
            mv_score = 5
        else:
            mv_score = 3
    raw_score += mv_score
    breakdown["market_cap"] = round(mv_score, 2)

    # 3. PE 估值分（12分）
    pe = stock.get("pe", 0) or 0
    pe_score = 0.0
    if pe > 0:
        if pe <= 20:
            pe_score = 12
        elif pe <= 30:
            pe_score = 10
        elif pe <= 50:
            pe_score = 7
        elif pe <= 100:
            pe_score = 4
        elif pe <= 200:
            pe_score = 2
    raw_score += pe_score
    breakdown["pe_score"] = round(pe_score, 2)

    # 4. PB 估值分（8分）
    pb = stock.get("pb", 0) or 0
    pb_score = 0.0
    if pb > 0:
        if 0.5 <= pb <= 3:
            pb_score = 8
        elif 0.3 <= pb <= 5:
            pb_score = 5
        elif 0.1 <= pb <= 10:
            pb_score = 2
    raw_score += pb_score
    breakdown["pb_score"] = round(pb_score, 2)

    # 5. 板块趋势分（8分）
    sector_trend = stock.get("sector_trend_score", 0) or 0
    s_trend = min(sector_trend / 100.0, 1.0) * 8 if sector_trend > 0 else 0
    raw_score += s_trend
    breakdown["sector_trend"] = round(s_trend, 2)

    # 6. 板块短线分（4分）
    sector_burst = stock.get("sector_burst_score", 0) or 0
    s_burst = min(sector_burst / 100.0, 1.0) * 4 if sector_burst > 0 else 0
    raw_score += s_burst
    breakdown["sector_burst"] = round(s_burst, 2)

    # 7. 资金流分（8分）
    ff = stock.get("_fund_flow")
    ff_score = 0.0
    if ff and isinstance(ff, dict) and ff.get("available") is not False:
        main_inflow = ff.get("main_net_inflow")
        if main_inflow is not None and isinstance(main_inflow, (int, float)):
            yi = float(main_inflow) / 1e8
            if yi > 0:
                ff_score = min(yi / 2.0, 8.0)
    raw_score += ff_score
    breakdown["fund_flow"] = round(ff_score, 2)

    # 归一化
    normalized = round(min(raw_score / raw_max * 100, 100.0), 2)
    breakdown["raw_total"] = round(raw_score, 2)
    breakdown["raw_max"] = raw_max
    breakdown["normalized"] = normalized

    return normalized, breakdown


def _try_qlib_quant_score(codes: List[str]) -> Optional[Dict[str, float]]:
    """
    尝试使用 Qlib 进行量化打分。

    预留接口：当前返回 None（降级到 fallback）。
    后续可接入 ai-hedge-fund smart_screener Phase1 的 Qlib 打分逻辑。

    Returns:
        {code: score} 或 None
    """
    # TODO: Phase 2 - 接入 Qlib Alpha158 + LightGBM
    # 参考: E:\\Workspace\\ai-stock-projects\\ai-hedge-fund\\smart_screener.py phase1_qlib_scan()
    return None


# These definitions are used only by the quality-adjusted shadow audit.  The
# formal scorer and its weights remain unchanged.
_QUANT_SHADOW_ENHANCED_SPECS = (
    ("momentum_quality", "1d_momentum", 8.0, "1d_momentum"),
    ("momentum_quality", "5d_momentum_quality", 8.0, "5d_momentum_quality"),
    ("momentum_quality", "ma_alignment", 8.0, "ma_alignment"),
    ("momentum_quality", "continuity", 6.0, "continuity"),
    ("valuation", "pe_score", 8.0, "pe_relative"),
    ("valuation", "pb_score", 4.0, "pb_score"),
    ("liquidity", "market_cap", 8.0, "market_cap"),
    ("liquidity", "volume_trend", 8.0, "volume_trend"),
    ("liquidity", "avg_amount", 6.0, "avg_amount"),
    ("risk_control", "drawdown", 8.0, "drawdown"),
    ("risk_control", "volatility", 6.0, "volatility"),
    ("fund_flow", "fund_flow", 8.0, "fund_flow"),
    ("fund_flow", "fund_flow_persistence", 6.0, "fund_flow_persistence"),
    ("sector_fit", "sector_trend", 8.0, "sector_trend"),
    ("sector_fit", "sector_burst", 4.0, "sector_burst"),
)

_QUANT_SHADOW_FALLBACK_SPECS = (
    ("momentum_quality", "change_score", 15.0, "1d_momentum"),
    ("valuation", "pe_score", 12.0, "pe_relative"),
    ("valuation", "pb_score", 8.0, "pb_score"),
    ("liquidity", "market_cap", 15.0, "market_cap"),
    ("fund_flow", "fund_flow", 8.0, "fund_flow"),
    ("sector_fit", "sector_trend", 8.0, "sector_trend"),
    ("sector_fit", "sector_burst", 4.0, "sector_burst"),
)


def _shadow_factor_status(
    stock: Dict[str, Any], canonical_name: str, qbd: Dict[str, Any], qkey: str
) -> str:
    """Return available/degraded/missing without changing formal scoring."""
    available = set(stock.get("available_factors") or [])
    degraded = set(stock.get("degraded_factors") or [])
    missing = set(stock.get("missing_factors") or [])

    # The validator historically exposed fund flow and sector match as broad
    # fields.  Keep their sub-factors independent in this shadow audit.
    if canonical_name == "fund_flow_persistence":
        recent_days = (stock.get("_fund_flow") or {}).get("recent_inflow_days")
        if isinstance(recent_days, (int, float)):
            return "available"
        if "fund_flow_persistence" in degraded or "fund_flow" in available:
            return "degraded"
        return "missing"
    if canonical_name in {"sector_trend", "sector_burst"}:
        source_key = f"{canonical_name}_score"
        if isinstance(stock.get(source_key), (int, float)):
            return "available"
        if canonical_name in available:
            return "available"
        if canonical_name in degraded:
            return "degraded"
        if canonical_name in missing:
            return "missing"
        if "sector_match" in degraded:
            return "degraded"
        if "sector_match" in missing:
            return "missing"
        return "missing"
    if canonical_name in available:
        return "available"
    if canonical_name in degraded:
        return "degraded"
    if canonical_name in missing:
        return "missing"

    # Keep the helper useful in unit tests and for old reports that predate
    # the validator fields.  Presence of a validated numeric input is enough
    # for a conservative inferred status; no formal score is recalculated.
    if canonical_name == "1d_momentum":
        return "available" if isinstance(stock.get("change_pct"), (int, float)) else "missing"
    if canonical_name == "pe_relative":
        return "available" if (stock.get("pe") or 0) > 0 else "missing"
    if canonical_name == "pb_score":
        return "available" if (stock.get("pb") or 0) > 0 else "missing"
    if canonical_name == "market_cap":
        return "available" if (stock.get("total_mv") or 0) > 0 else "missing"
    if canonical_name == "fund_flow":
        flow = stock.get("_fund_flow")
        return (
            "available"
            if isinstance(flow, dict)
            and flow.get("available") is not False
            and isinstance(flow.get("main_net_inflow"), (int, float))
            else "missing"
        )
    if canonical_name == "sector_match":
        return "available" if any(
            isinstance(stock.get(key), (int, float))
            for key in ("sector_trend_score", "sector_burst_score")
        ) else "missing"
    return "available" if isinstance(qbd.get(qkey), (int, float)) else "missing"


_QUANT_SHADOW_REDUNDANCY_MIN_SAMPLES = 20


def _shadow_pearson(values_a: List[float], values_b: List[float]) -> Optional[float]:
    if len(values_a) != len(values_b) or len(values_a) < _QUANT_SHADOW_REDUNDANCY_MIN_SAMPLES:
        return None
    mean_a = sum(values_a) / len(values_a)
    mean_b = sum(values_b) / len(values_b)
    centered_a = [value - mean_a for value in values_a]
    centered_b = [value - mean_b for value in values_b]
    denom_a = sum(value * value for value in centered_a) ** 0.5
    denom_b = sum(value * value for value in centered_b) ** 0.5
    if denom_a == 0 or denom_b == 0:
        return 0.0
    return round(
        sum(a * b for a, b in zip(centered_a, centered_b)) / (denom_a * denom_b),
        6,
    )


def diagnose_quant_factor_group_redundancy(stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Expose observational group correlation; never changes weights."""
    group_values: Dict[str, Dict[str, float]] = {}
    for stock in stocks:
        code = str(stock.get("code") or "")
        groups = stock.get("quant_score_shadow_factor_groups") or {}
        for group, details in groups.items():
            if details.get("status") != "available":
                continue
            value = details.get("normalized_score")
            if isinstance(value, (int, float)):
                group_values.setdefault(group, {})[code] = float(value)

    group_names = sorted(group_values)
    pairs: List[Dict[str, Any]] = []
    high_pairs: List[Dict[str, Any]] = []
    for index, left in enumerate(group_names):
        for right in group_names[index + 1:]:
            common = sorted(set(group_values[left]) & set(group_values[right]))
            corr = _shadow_pearson(
                [group_values[left][code] for code in common],
                [group_values[right][code] for code in common],
            )
            if corr is None:
                status = "insufficient_evidence"
            elif abs(corr) >= 0.8:
                status = "high"
            elif abs(corr) >= 0.6:
                status = "moderate"
            else:
                status = "low"
            item = {
                "left": left,
                "right": right,
                "sample_count": len(common),
                "correlation": corr,
                "status": status,
            }
            pairs.append(item)
            if status == "high":
                high_pairs.append(item)

    valid_pair_count = sum(
        1 for item in pairs if item["status"] != "insufficient_evidence"
    )

    return {
        "schema_version": "quant_score_shadow_redundancy.v1",
        "status": "ok" if valid_pair_count else "insufficient_evidence",
        "sample_count": len(stocks),
        "minimum_sample_count": _QUANT_SHADOW_REDUNDANCY_MIN_SAMPLES,
        "valid_pair_count": valid_pair_count,
        "groups": group_names,
        "pairwise_correlations": pairs,
        "high_redundancy_pairs": high_pairs,
        "weights_changed": False,
        "disclaimer": "Observational shadow diagnostic only; no formal weights changed.",
    }


def annotate_quant_score_shadow(
    stocks: List[Dict[str, Any]],
    *,
    cross_sectional_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Attach quality-adjusted shadow scores without touching formal scores."""
    context = dict(cross_sectional_context or {})
    context.setdefault("universe_id", "compute_quant_scores_input")
    context.setdefault("as_of_date", None)
    context.setdefault("candidate_chain", "not_provided")
    for stock in stocks:
        qbd = stock.get("quant_breakdown") or {}
        for key, value in list(qbd.items()):
            if (
                not isinstance(value, bool)
                and isinstance(value, (int, float))
                and not math.isfinite(float(value))
            ):
                qbd[key] = None
        enhanced = float(qbd.get("raw_max") or 0) >= 100 or "1d_momentum" in qbd
        specs = _QUANT_SHADOW_ENHANCED_SPECS if enhanced else _QUANT_SHADOW_FALLBACK_SPECS
        group_state: Dict[str, Dict[str, Any]] = {}
        shadow_raw_total = 0.0
        shadow_available_max = 0.0
        full_max = 0.0
        for group, qkey, factor_max, canonical_name in specs:
            full_max += factor_max
            status = _shadow_factor_status(stock, canonical_name, qbd, qkey)
            details = group_state.setdefault(
                group,
                {"raw_score": 0.0, "available_max": 0.0, "full_max": 0.0,
                 "available_factors": [], "degraded_factors": [], "missing_factors": []},
            )
            details["full_max"] += factor_max
            raw_value = qbd.get(qkey)
            finite_value = (
                not isinstance(raw_value, bool)
                and isinstance(raw_value, (int, float))
                and math.isfinite(float(raw_value))
            )
            if status == "available" and not finite_value:
                status = "missing"
            value = float(raw_value) if finite_value else 0.0
            if status == "available":
                details["raw_score"] += value
                details["available_max"] += factor_max
                details["available_factors"].append(qkey)
                shadow_raw_total += value
                shadow_available_max += factor_max
            elif status == "degraded":
                details["degraded_factors"].append(qkey)
            else:
                details["missing_factors"].append(qkey)

        available_groups = []
        degraded_groups = []
        missing_groups = []
        for group, details in group_state.items():
            if details["available_factors"]:
                available_groups.append(group)
                if details["degraded_factors"] or details["missing_factors"]:
                    details["status"] = "partial"
                    degraded_groups.append(group)
                else:
                    details["status"] = "available"
            elif details["degraded_factors"]:
                details["status"] = "degraded"
                degraded_groups.append(group)
            else:
                details["status"] = "missing"
                missing_groups.append(group)
            details["normalized_score"] = round(
                details["raw_score"] / details["available_max"] * 100, 4
            ) if details["available_max"] else None

        adjusted = (
            round(shadow_raw_total / shadow_available_max * 100, 2)
            if shadow_available_max
            else None
        )
        confidence = round(shadow_available_max / full_max * 100, 2) if full_max else 0.0
        stock["quant_score_shadow_quality_adjusted"] = adjusted
        stock["quant_score_shadow_available_factor_groups"] = sorted(available_groups)
        stock["quant_score_shadow_missing_factor_groups"] = sorted(missing_groups)
        stock["quant_score_shadow_degraded_factor_groups"] = sorted(set(degraded_groups))
        stock["quant_score_shadow_confidence"] = confidence
        stock["quant_score_shadow_factor_groups"] = group_state
        stock["quant_score_shadow_cross_sectional_universe"] = context["universe_id"]
        stock["quant_score_shadow_cross_sectional_as_of"] = context["as_of_date"]
        stock["quant_score_shadow_cross_sectional_candidate_chain"] = context[
            "candidate_chain"
        ]

    usable = [
        stock for stock in stocks
        if isinstance(stock.get("quant_score_shadow_quality_adjusted"), (int, float))
    ]
    for stock in stocks:
        score = stock.get("quant_score_shadow_quality_adjusted")
        if not usable or not isinstance(score, (int, float)):
            percentile = None
        else:
            values = [item["quant_score_shadow_quality_adjusted"] for item in usable]
            less = sum(value < score for value in values)
            equal = sum(value == score for value in values)
            percentile = round((less + equal / 2) / len(values) * 100, 2)
        stock["quant_score_shadow_cross_sectional_percentile"] = percentile

    redundancy = diagnose_quant_factor_group_redundancy(stocks)
    confidence_values = [
        float(stock["quant_score_shadow_confidence"])
        for stock in stocks
        if isinstance(stock.get("quant_score_shadow_confidence"), (int, float))
    ]
    group_status_counts: Dict[str, Dict[str, int]] = {}
    for stock in stocks:
        for group, details in (stock.get("quant_score_shadow_factor_groups") or {}).items():
            status_counts = group_status_counts.setdefault(group, {})
            status = str(details.get("status") or "missing")
            status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema_version": "quant_score_shadow_quality_adjusted.v1",
        "mode": "paper_shadow_research_only",
        "status": "ok" if usable else "unavailable",
        "scored_stock_count": len(stocks),
        "usable_shadow_score_count": len(usable),
        "missing_shadow_score_count": len(stocks) - len(usable),
        "average_confidence": round(sum(confidence_values) / len(confidence_values), 2)
        if confidence_values else 0.0,
        "factor_group_status_counts": group_status_counts,
        "recalibration": "available_factor_max_only",
        "score_interpretation": "conditional_on_available_factors",
        "cross_sectional_context": context,
        "weights_changed": False,
        "redundancy_diagnostics": redundancy,
        "disclaimer": "No broker connection and no live order instruction.",
    }


def _bars_for_linkage_returns(
    bars: List[Dict], *, bars_source: str
) -> List[Dict]:
    """Adapt compact provider dates without weakening strict linkage parsing."""
    normalized = []
    for bar in bars:
        if not isinstance(bar, dict):
            normalized.append(bar)
            continue
        copied = dict(bar)
        raw_date = str(copied.get("date") or "")
        if len(raw_date) == 8 and raw_date.isdigit():
            try:
                copied["date"] = datetime.strptime(
                    raw_date, "%Y%m%d"
                ).date().isoformat()
            except ValueError:
                pass
        normalized.append(copied)
    return normalized


def compute_quant_scores(
    stocks: List[Dict],
    as_of_date: Optional[str] = None,
    http_enabled: Optional[bool] = None,
    sector_returns_by_name: Optional[Dict[str, Dict[str, float]]] = None,
    bars_client_override: Any = None,
) -> List[Dict]:
    """为个股列表计算量化评分。

    Priority chain:
    1. Try HTTP API K-line bars → enhanced scorer (5d/10d/drawdown/turnover)
    2. Try Qlib (reserved)
    3. Fall back to basic multi-factor scorer

    Parameters
    ----------
    stocks : list[dict]
        Stock dicts each with at least ``code``, ``change_pct``, ``total_mv``,
        ``pe``.
    as_of_date : str | None
        Analysis date (``YYYY-MM-DD``).  If provided, bars are fetched for
        the 20 trading days ending on this date.
    """
    codes = [s["code"] for s in stocks]

    # HTTP remains the only fund-flow source. A bars override is used by the
    # direction-only shadow path when local StockDB is fresher or HTTP is down.
    http_client = _get_http_client() if http_enabled is not False else None
    if http_enabled is None and not _http_client_is_healthy(http_client):
        http_client = None
    bars_client = (
        bars_client_override if bars_client_override is not None else http_client
    )
    bars_cache: Dict[str, List[Dict]] = {}

    if bars_client is not None and as_of_date:
        # Build date range: ~20 trading days before as_of_date
        end_date = as_of_date.replace("-", "")
        try:
            from datetime import datetime as dt, timedelta

            start_dt = dt.strptime(as_of_date, "%Y-%m-%d") - timedelta(days=35)
            start_date = start_dt.strftime("%Y%m%d")
        except ValueError:
            start_date = end_date  # fallback: same-day

        seen_bar_codes = set()
        for s in stocks:
            code = s["code"]
            if code in seen_bar_codes:
                continue
            seen_bar_codes.add(code)
            try:
                bars = bars_client.get_stock_bars(
                    code, start=start_date, end=end_date, frequency="1d"
                )
                if bars and len(bars) >= 5:
                    bars_cache[code] = bars
            except (ConnectionError, TimeoutError, ValueError, RuntimeError):
                pass
            except Exception:
                pass

    bars_selection = getattr(bars_client, "selection", {})
    if not isinstance(bars_selection, dict):
        bars_selection = {}
    bars_source = bars_selection.get("source")
    if not bars_source:
        bars_source = "http" if bars_client is http_client and bars_client else "override"
    latest_date_key = (
        "sdk_latest_daily_date"
        if bars_source == "stockdb-sdk"
        else "http_latest_daily_date"
    )
    requested_codes = {stock["code"] for stock in stocks}
    usable_relation_count = sum(
        1 for stock in stocks if stock["code"] in bars_cache
    )
    compute_quant_scores._last_bars_audit = {
        "source": bars_source if bars_client is not None else "unavailable",
        "reason": bars_selection.get("reason", "direct_client"),
        "latest_daily_date": bars_selection.get(latest_date_key),
        "requested_stock_count": len(requested_codes),
        "usable_stock_count": len(bars_cache),
        "requested_relation_count": len(stocks),
        "usable_relation_count": usable_relation_count,
        "coverage_ratio": (
            round(len(bars_cache) / len(requested_codes), 6)
            if requested_codes
            else 0.0
        ),
        "minimum_bars": 5,
    }

    # ---- Fund flow: batch → single → neutral (Phase 16) ----
    fund_flow_source = "fund_flow_neutral"
    if http_client is not None:
        codes_batch = [s["code"] for s in stocks]
        try:
            batch_result = http_client.get_stock_fund_flow_batch(codes_batch)
            if batch_result and batch_result.get("items"):
                fund_flow_source = "fund_flow_ths_batch"
                items = batch_result["items"]
                for s in stocks:
                    code = s["code"].zfill(6)
                    if code in items:
                        s["_fund_flow"] = items[code]
            elif batch_result is None:
                # Batch failed → fall through to single
                fund_flow_source = "fund_flow_ths_single"
                for s in stocks:
                    code = s["code"]
                    try:
                        ff = http_client.get_stock_fund_flow(code)
                        if ff and ff.get("available") is not False:
                            s["_fund_flow"] = ff
                    except Exception:
                        pass
        except Exception:
            fund_flow_source = "fund_flow_ths_single"
            for s in stocks:
                code = s["code"]
                try:
                    ff = http_client.get_stock_fund_flow(code)
                    if ff and ff.get("available") is not False:
                        s["_fund_flow"] = ff
                except Exception:
                    pass

    # ---- Score each stock ----
    # Track fund flow source in quant sources
    fund_flow_count = sum(1 for s in stocks if s.get("_fund_flow") is not None)

    # v2: 数据核查统计
    quality_reports = {}

    if bars_cache:
        # At least some stocks have HTTP bar data → use enhanced scorer where possible
        enhanced_quant_source = {
            "http": "http_enhanced_v2",
            "stockdb-sdk": "stockdb_sdk_enhanced_v2",
        }.get(bars_source, "override_enhanced_v2")
        for s in stocks:
            code = s["code"]
            if code in bars_cache:
                score, breakdown = _compute_enhanced_quant_score(s, bars_cache[code])
                s["quant_score"] = score
                s["quant_breakdown"] = breakdown
                s["quant_source"] = enhanced_quant_source
            else:
                score, breakdown = _compute_fallback_quant_score(s)
                s["quant_score"] = score
                s["quant_breakdown"] = breakdown
                s["quant_source"] = "fallback_v2"
    else:
        # ---- Attempt 2: Qlib ----
        qlib_scores = _try_qlib_quant_score(codes)

        if qlib_scores:
            for s in stocks:
                s["quant_score"] = qlib_scores.get(s["code"], 50.0)
                s["quant_breakdown"] = {"source": "qlib"}
                s["quant_source"] = "qlib"
        else:
            for s in stocks:
                score, breakdown = _compute_fallback_quant_score(s)
                s["quant_score"] = score
                s["quant_breakdown"] = breakdown
                s["quant_source"] = "fallback_v2"

    # ---- 数据核查（v2 新增）----
    try:
        from theme_sector_radar.quant_data_validator import (
            compute_data_quality_for_stocks,
            print_data_quality_summary,
        )
        quality_reports = compute_data_quality_for_stocks(stocks, bars_cache, as_of_date)
        for s in stocks:
            code = s["code"]
            if code in quality_reports:
                qr = quality_reports[code]
                s["data_quality_score"] = qr.quality_score
                s["factor_coverage"] = qr.factor_coverage
                s["available_factors"] = qr.available_factors
                s["missing_factors"] = qr.missing_factors
                s["degraded_factors"] = qr.degraded_factors
        print_data_quality_summary(quality_reports)
    except ImportError:
        pass  # 数据核查模块不可用时跳过

    # Independent quality-adjusted shadow audit. It is intentionally after
    # formal scoring and validation, and never feeds formal sorting.
    quant_shadow_audit = annotate_quant_score_shadow(
        stocks,
        cross_sectional_context={
            "as_of_date": as_of_date,
            "universe_id": "compute_quant_scores_input",
            "candidate_chain": "not_provided",
        },
    )
    compute_quant_scores._last_quant_shadow_audit = quant_shadow_audit

    # ---- Stock-to-sector linkage V2 (paper/shadow only) ----
    sector_returns_by_name = sector_returns_by_name or {}
    trusted_constituent_sources = {
        "http_em",
        "http_local_industry",
        "http_local_concept_members",
    }
    for stock in stocks:
        try:
            stock_bars = bars_cache.get(stock["code"], [])
            stock_returns = (
                returns_by_date_from_bars(
                    _bars_for_linkage_returns(
                        stock_bars, bars_source=bars_source
                    ),
                    as_of_date=as_of_date,
                )
                if stock_bars and as_of_date
                else None
            )
            sector_returns = sector_returns_by_name.get(
                stock.get("sector_name", "")
            )
            relative_strength = relative_strength_score_from_returns(
                stock_returns, sector_returns
            )
            weight_score = (
                stock.get("weight_normalized")
                if stock.get("weight_signal_available")
                else None
            )
            flow_score = stock.get("linkage_flow_alignment_score")
            quality_parts = [
                1.0 if stock.get("quote_available") else 0.0,
                1.0 if stock_bars else 0.0,
                (
                    1.0
                    if stock.get("constituent_source")
                    in trusted_constituent_sources
                    else 0.5
                ),
            ]
            quality_score = sum(quality_parts) / len(quality_parts)
            stock["linkage_v2_shadow"] = (
                calculate_stock_sector_linkage_v2_shadow(
                    stock_returns=stock_returns,
                    sector_returns=sector_returns,
                    relative_strength_score=relative_strength,
                    constituent_weight_score=weight_score,
                    fund_flow_alignment_score=flow_score,
                    data_quality_score=quality_score,
                )
            )
        except ValueError as exc:
            stock["linkage_v2_shadow"] = {
                "schema_version": "stock_sector_linkage_v2_shadow.v1",
                "mode": "paper_shadow_research_only",
                "status": "unavailable",
                "score": None,
                "reason": str(exc),
                "disclaimer": "No broker connection and no live order instruction.",
            }
        except (TypeError, OverflowError):
            stock["linkage_v2_shadow"] = {
                "schema_version": "stock_sector_linkage_v2_shadow.v1",
                "mode": "paper_shadow_research_only",
                "status": "calculation_failed",
                "score": None,
                "disclaimer": "No broker connection and no live order instruction.",
            }

    # Track fund flow source (appended as suffix)
    if fund_flow_count > 0:
        ff_label = fund_flow_source.replace("fund_flow_ths_", "ff_").replace("fund_flow_", "ff_")
        for s in stocks:
            current = s.get("quant_source", "fallback")
            if s.get("_fund_flow") is not None:
                s["quant_source"] = f"{current}+{ff_label}"

    compute_quant_scores._last_fund_flow_source = fund_flow_source
    return stocks


# ============================================================
# 综合排序
# ============================================================

WEIGHT_QUANT = 0.5
WEIGHT_RELEVANCE = 0.3
WEIGHT_SECTOR_MOMENTUM = 0.2


def compute_final_scores(stocks: List[Dict]) -> List[Dict]:
    """
    计算最终综合分 v2。

    v2 公式：
    final_score = quant_score * 0.5 + relevance_score * 30 + sector_momentum * 20

    其中 sector_momentum = (sector_trend_score + sector_burst_score) / 200

    假设 quant_score 已归一化到 0~100，relevance_score 已归一化到 0~1。
    """
    for s in stocks:
        quant = s.get("quant_score", 50.0) / 100.0  # 归一化到 0~1
        relevance = s.get("relevance_score", 0.5)
        sector_trend = s.get("sector_trend_score", 0) or 0
        sector_burst = s.get("sector_burst_score", 0) or 0
        sector_momentum = (sector_trend + sector_burst) / 200.0  # 归一化到 0~1

        final = (WEIGHT_QUANT * quant + WEIGHT_RELEVANCE * relevance +
                 WEIGHT_SECTOR_MOMENTUM * sector_momentum)
        s["final_score"] = round(final * 100, 2)  # 输出 0~100
        s["sector_momentum_component"] = round(sector_momentum * 100 * WEIGHT_SECTOR_MOMENTUM, 2)

    stocks.sort(key=lambda x: x["final_score"], reverse=True)
    return stocks


# ============================================================
# 评分拆解（Phase 20）
# ============================================================


def build_score_breakdown(stock: Dict) -> Dict[str, Any]:
    """Build a human-readable score breakdown for a single stock.

    v2: 展示新因子体系的完整拆解。

    Returns a dict safe for JSON serialisation.  Missing fields
    fall back to ``0`` rather than crashing.
    """
    quant_score = stock.get("quant_score") or 0.0
    relevance_score = stock.get("relevance_score") or 0.0
    final_score = stock.get("final_score") or 0.0
    qsrc = stock.get("quant_source", "")
    qbd = stock.get("quant_breakdown", {})

    # v2 公式组件
    quant_component = round(quant_score * WEIGHT_QUANT, 2)
    relevance_component = round(relevance_score * WEIGHT_RELEVANCE * 100, 2)
    sector_momentum_component = stock.get("sector_momentum_component", 0.0)

    # 数据质量
    data_quality_score = stock.get("data_quality_score", 0.0)
    factor_coverage = stock.get("factor_coverage", 0.0)

    result = {
        "final_score": final_score,
        "quant_score_component": quant_component,
        "relevance_score_component": relevance_component,
        "sector_momentum_component": sector_momentum_component,
        "penalty": 0.0,
        "data_quality_score": data_quality_score,
        "factor_coverage": factor_coverage,
        "formula": "final = quant*0.5 + relevance*30 + sector_momentum*20",
    }

    # v2: 增强模式因子明细
    if qbd and "raw_total" in qbd:
        result["quant_breakdown"] = {
            "raw_total": qbd.get("raw_total", 0),
            "raw_max": qbd.get("raw_max", 0),
            "normalized": qbd.get("normalized", 0),
            "factors": {
                "动量质量": {
                    "1d_momentum": qbd.get("1d_momentum", 0),
                    "5d_momentum_quality": qbd.get("5d_momentum_quality", 0),
                    "ma_alignment": qbd.get("ma_alignment", 0),
                    "continuity": qbd.get("continuity", 0),
                },
                "估值合理": {
                    "pe_score": qbd.get("pe_score", 0),
                    "pb_score": qbd.get("pb_score", 0),
                },
                "流动性": {
                    "market_cap": qbd.get("market_cap", 0),
                    "volume_trend": qbd.get("volume_trend", 0),
                    "avg_amount": qbd.get("avg_amount", 0),
                },
                "风险控制": {
                    "drawdown": qbd.get("drawdown", 0),
                    "volatility": qbd.get("volatility", 0),
                },
                "资金面": {
                    "fund_flow": qbd.get("fund_flow", 0),
                    "fund_flow_persistence": qbd.get("fund_flow_persistence", 0),
                },
                "板块匹配": {
                    "sector_trend": qbd.get("sector_trend", 0),
                    "sector_burst": qbd.get("sector_burst", 0),
                },
            },
        }

    return result


def _annotate_score_breakdown(stocks: List[Dict]) -> List[Dict]:
    """Attach ``score_breakdown`` to every stock in-place."""
    for s in stocks:
        s["score_breakdown"] = build_score_breakdown(s)
    return stocks


# ============================================================
# 运行健康门禁（Phase 6）
# ============================================================


_COVERAGE_THRESHOLD = 0.8  # 红线：覆盖率低于此值为 warn


def _ratio(numerator: int, denominator: int) -> float:
    """Safe ratio, avoids division by zero."""
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def build_data_quality_summary(
    data_source: Dict[str, Any],
    run_health: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a unified data-quality panel from scattered source stats.

    Parameters
    ----------
    data_source : dict
        From ``result["data_source"]``.
    run_health : dict | None
        From ``result["run_health"]``.

    Returns
    -------
    dict  with keys: ``status``, ``summary``, ``coverage``, ``warnings``.
    """
    warnings: list[str] = []
    csrc = data_source.get("constituent_sources", {})
    qsrc = data_source.get("quant_score_sources", {})
    sis = data_source.get("stock_info_sources", {})
    ff_src = data_source.get("fund_flow_source", "fund_flow_neutral")

    # ---- constituents ----
    total_c = sum(csrc.values()) or 1
    real_c = csrc.get("http_em", 0) + csrc.get("http_local_industry", 0)
    cr = _ratio(real_c, total_c)
    c_status = "pass" if cr >= _COVERAGE_THRESHOLD else "warn"
    c_main = "http_em" if csrc.get("http_em", 0) > 0 else (
        "http_local_industry" if csrc.get("http_local_industry", 0) > 0 else "http_mapping"
    )
    if cr < _COVERAGE_THRESHOLD:
        warnings.append(f"成分股真实源覆盖率 {cr:.0%} < {_COVERAGE_THRESHOLD:.0%}")

    # ---- quant scores ----
    total_q = sum(qsrc.values()) or 1
    enhanced_q = sum(v for k, v in qsrc.items() if "enhanced" in k)
    qr = _ratio(enhanced_q, total_q)
    q_status = "pass" if qr >= _COVERAGE_THRESHOLD else "warn"
    if qr < _COVERAGE_THRESHOLD:
        warnings.append(f"量化评分 http_enhanced 覆盖率 {qr:.0%} < {_COVERAGE_THRESHOLD:.0%}")

    # ---- fund flow ----
    # ff_batch/ff_single are counts inferred from stock_info or quant tracking
    ff_total = sum(v for k, v in qsrc.items() if "ff_" in k) + sum(
        v for k, v in qsrc.items() if "enhanced" in k and "ff_" not in k
    )
    ff_avail = sum(v for k, v in qsrc.items() if "ff_batch" in k or "ff_single" in k)
    if ff_total == 0:
        ff_total = 1
    fr = _ratio(ff_avail, ff_total)
    ff_status = "pass" if fr >= _COVERAGE_THRESHOLD else "warn" if fr > 0 else "warn"
    if fr == 0:
        warnings.append("资金流数据全部 neutral (无可用源)")

    # ---- stock info ----
    si_ok = sis.get("ok", 0)
    si_filtered = sis.get("filtered_st", 0) + sis.get("filtered_invalid", 0)
    si_unknown = sis.get("unknown", 0)
    si_known = si_ok + si_filtered
    si_total = si_known + si_unknown or 1
    sir = _ratio(si_known, si_total)
    si_status = "pass" if sir >= _COVERAGE_THRESHOLD else "warn"
    if sir < _COVERAGE_THRESHOLD:
        warnings.append(f"股票基础信息已知率 {sir:.0%} < {_COVERAGE_THRESHOLD:.0%}")

    # ---- overall status ----
    overall = run_health.get("status", "unknown") if run_health else "unknown"

    return {
        "status": overall,
        "summary": {
            "constituents": {"status": c_status, "coverage": round(cr, 4), "main_source": c_main},
            "quant_scores": {"status": q_status, "coverage": round(qr, 4)},
            "fund_flow": {"status": ff_status, "coverage": round(fr, 4), "source": ff_src},
            "stock_info": {"status": si_status, "coverage": round(sir, 4)},
        },
        "coverage": {
            "constituents_real_ratio": round(cr, 4),
            "fund_flow_available_ratio": round(fr, 4),
            "stock_info_known_ratio": round(sir, 4),
            "quant_http_ratio": round(qr, 4),
        },
        "warnings": warnings,
    }


def evaluate_run_health(data_source: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate whether run output is healthy enough for daily use.

    Parameters
    ----------
    data_source : dict
        The ``data_source`` dict from the unified pipeline result,
        with keys: ``constituent_sources``, ``quant_score_sources``,
        ``has_unavailable_sectors``, ``has_emergency_fallback``.

    Returns
    -------
    dict
        {
            "status": "pass" | "warn" | "fail",
            "reasons": [...],
            "metrics": {
                "total_constituent_sectors": int,
                "unavailable_sectors": int,
                "emergency_fallback_sectors": int,
                "http_enhanced_stocks": int,
                "fallback_quant_stocks": int,
            }
        }
    """
    reasons: list[str] = []
    csrc = data_source.get("constituent_sources", {})
    qsrc = data_source.get("quant_score_sources", {})

    # ---- constituent metrics ----
    unavailable = csrc.get("unavailable", 0)
    emergency = csrc.get("local_emergency_mapping", 0)
    total_constituent = sum(csrc.values())
    total_constituent = max(total_constituent, 1)  # avoid div by zero

    # ---- quant metrics ----
    enhanced = qsrc.get("http_enhanced", 0)
    fallback = qsrc.get("fallback", 0)
    total_quant = enhanced + fallback
    total_quant = max(total_quant, 1)

    metrics = {
        "total_constituent_sectors": total_constituent,
        "unavailable_sectors": unavailable,
        "emergency_fallback_sectors": emergency,
        "http_enhanced_stocks": enhanced,
        "fallback_quant_stocks": fallback,
        "candidate_chain": data_source.get("candidate_chain"),
        "formal_candidate_status": data_source.get("formal_candidate_status"),
    }

    # ---- FAIL rules ----
    if (
        data_source.get("candidate_chain") == "direction_linkage_v2"
        and data_source.get("formal_candidate_status")
        != "active_for_paper_research"
    ):
        reasons.append("方向分主路径未形成经过验证的候选池")

    if total_constituent > 0 and unavailable / total_constituent >= 0.3:
        reasons.append(
            f"unavailable 板块占比 {unavailable}/{total_constituent} >= 30%"
        )

    if total_constituent > 0 and emergency / total_constituent >= 0.5:
        reasons.append(
            f"emergency fallback 板块占比 {emergency}/{total_constituent} >= 50%"
        )

    if total_quant > 0 and fallback / total_quant >= 0.5:
        reasons.append(
            f"fallback 量化评分占比 {fallback}/{total_quant} >= 50%"
        )

    if reasons:
        return {"status": "fail", "reasons": reasons, "metrics": metrics}

    # ---- WARN rules ----
    if unavailable > 0:
        reasons.append(
            f"存在 {unavailable} 个 unavailable 板块 (< 30%)"
        )
    if emergency > 0:
        reasons.append(
            f"存在 {emergency} 个 emergency fallback 板块 (< 50%)"
        )
    if fallback > 0:
        reasons.append(
            f"存在 {fallback} 只个股使用 fallback 量化评分 (< 50%)"
        )
    # Phase 17: stock info unknown ratio
    stock_info = data_source.get("stock_info_sources", {})
    stock_ok = stock_info.get("ok", 0)
    stock_unknown = stock_info.get("unknown", 0)
    stock_total = stock_ok + stock_unknown
    if stock_total > 0 and stock_unknown / stock_total >= 0.5:
        reasons.append(
            f"股票基础信息缺失比例 {stock_unknown}/{stock_total} >= 50%"
        )

    # ---- http_mapping vs http_local_industry/http_local_concept ----
    http_em = csrc.get("http_em", 0)
    http_stale = csrc.get("http_stale", 0)
    http_local = csrc.get("http_local_industry", 0)
    http_local_concept = csrc.get("http_local_concept_members", 0)
    http_map = csrc.get("http_mapping", 0)

    # Real sources = em + stale + local_industry + local_concept
    real_sources = http_em + http_stale + http_local + http_local_concept
    mapping_ratio = http_map / total_constituent if total_constituent > 0 else 0

    if mapping_ratio >= 0.5 and http_map > 0:
        reasons.append(
            f"离线映射占比 {http_map}/{total_constituent} >= 50%，实际数据源不足"
        )
    elif http_em == 0 and http_stale == 0 and http_local == 0 and http_local_concept == 0 and total_constituent > 0 and unavailable == 0:
        # All mapping with ZERO real sources → old-style warn
        reasons.append("全部成分股来源于离线映射 (http_mapping)，EM 可能不可用")
    elif (http_local > 0 or http_local_concept > 0) and http_em == 0 and http_stale == 0:
        # Has local_industry or local_concept but no live EM — just note it, not necessarily warn
        if http_map > 0 and mapping_ratio < 0.5:
            # Minor mapping alongside local sources — acceptable, not a warn
            pass
        elif http_map == 0:
            # Pure local sources — good, no warn needed
            pass

    if reasons:
        return {"status": "warn", "reasons": reasons, "metrics": metrics}

    # ---- PASS ----
    return {
        "status": "pass",
        "reasons": ["所有数据源正常"],
        "metrics": metrics,
    }


# ============================================================
# Markdown 格式化
# ============================================================


_HEALTH_ICON = {"pass": "✅", "warn": "⚠️", "fail": "❌"}


# ============================================================
# 输出
# ============================================================


def _format_stock_table(stocks: List[Dict], top_n: int = 10) -> str:
    """格式化个股表格 (Phase 20: with breakdown)"""
    lines = []
    lines.append(f"{'排名':>3} {'代码':<8} {'名称':<10} {'综合':>6} {'量化':>6} {'关联':>6} {'资金':>4} {'板块':<8}")
    lines.append(f"{'─'*80}")
    for i, s in enumerate(stocks[:top_n], 1):
        bd = s.get("score_breakdown", {})
        ff_flag = "✓" if bd.get("has_fund_flow") else "—"
        lines.append(
            f"{i:3d} {s['code']:<8} {s.get('name',''):<10} "
            f"{s.get('final_score',0):>6.1f} {s.get('quant_score',0):>6.1f} "
            f"{s.get('relevance_score',0):>6.3f} {ff_flag:>4} "
            f"{s.get('sector_name',''):<8}"
        )
    lines.append(f"  * 资金列: ✓ = 含THS资金流因子, — = 无资金流数据")
    return "\n".join(lines)


def generate_markdown_report(
    as_of_date: str,
    trend_stocks: List[Dict],
    burst_stocks: List[Dict],
    bridge_result: Dict[str, Any],
    top_n: int = 10,
    run_health: Optional[Dict[str, Any]] = None,
    data_quality: Optional[Dict[str, Any]] = None,
    candidate_chain: str = "direction_linkage_v2",
    active_candidates: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """生成 Markdown 报告"""
    score_as_of_date = str(bridge_result.get("as_of_date") or as_of_date)
    lines = []
    lines.append(f"# 板块雷达 × 个股选股 联合报告")
    lines.append(f"")
    lines.append(f"**分析日期**: {as_of_date}")
    lines.append(f"**板块评分日期**: {score_as_of_date}")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    legacy_sector_paths_enabled = bool(
        bridge_result.get(
            "legacy_sector_paths_enabled", candidate_chain == "legacy"
        )
    )
    lines.append(f"**候选主路径**: {candidate_chain}")
    lines.append(
        "**趋势/短线路径**: "
        + ("启用（legacy 研究模式）" if legacy_sector_paths_enabled else "关闭")
    )
    lines.append(f"")

    # 健康门禁状态（Phase 6）
    if run_health:
        icon = _HEALTH_ICON.get(run_health.get("status", ""), "")
        lines.append(f"**{icon} 数据健康门禁**: {run_health['status'].upper()}")
        for reason in run_health.get("reasons", []):
            lines.append(f"  - {reason}")
        lines.append(f"")

    lines.append(f"> **免责声明**: 本报告仅用于板块研究和选股参考，不作为操作依据。")
    lines.append(f"")

    # Phase 19: 数据质量面板
    if data_quality:
        dq = data_quality
        lines.append(f"## 数据质量面板")
        lines.append(f"")
        lines.append(f"| 模块 | 状态 | 覆盖率 | 主要来源 |")
        lines.append(f"|------|------|--------|----------|")
        for mod_key, label, note in [
            ("constituents", "成分股", "真实行业成分股"),
            ("quant_scores", "K线/量化", "StockDB"),
            ("fund_flow", "资金流", "THS"),
            ("stock_info", "股票基础信息", "SecurityMaster"),
        ]:
            mod = dq.get("summary", {}).get(mod_key, {})
            st = mod.get("status", "?")
            icon = "✅" if st == "pass" else "⚠️"
            cov = mod.get("coverage", 0)
            main = mod.get("main_source", mod.get("source", ""))
            lines.append(f"| {icon} {label} | {st} | {cov:.1%} | {main} |")
        lines.append(f"")

    # 数据来源状态（Phase 5）
    source_summary = bridge_result.get("constituent_source_summary", {})
    quant_sources = {}
    score_source_rows = (
        (trend_stocks if trend_stocks else [])
        + (burst_stocks if burst_stocks else [])
        if legacy_sector_paths_enabled
        else list(active_candidates or [])
    )
    for s in score_source_rows:
        qs = s.get("quant_source", "fallback")
        quant_sources[qs] = quant_sources.get(qs, 0) + 1

    lines.append(f"## 数据来源状态")
    lines.append(f"")
    lines.append(f"| 来源 | 板块数 |")
    lines.append(f"|------|--------|")
    for label in ["http_em", "http_stale", "http_local_industry", "http_local_concept_members", "http_mapping", "local_emergency_mapping", "unavailable"]:
        count = source_summary.get(label, 0)
        icon = "✅" if label.startswith("http_") else "⚠️" if label == "local_emergency_mapping" else "❌" if label == "unavailable" else ""
        lines.append(f"| {icon} {label} | {count} |")
    lines.append(f"")

    has_unavailable = source_summary.get("unavailable", 0) > 0
    has_emergency = source_summary.get("local_emergency_mapping", 0) > 0
    if has_unavailable:
        lines.append(f"⚠️ **警告**: 存在 {source_summary['unavailable']} 个板块无成分股数据。")
    if has_emergency:
        lines.append(f"⚠️ **降级**: {source_summary['local_emergency_mapping']} 个板块使用本地 emergency mapping（market_data_service 不可达）。")
    if not has_unavailable and not has_emergency:
        lines.append(f"✅ 所有板块成分股数据正常获取。")
    lines.append(f"")

    lines.append(f"| 量化评分来源 | 个股数 |")
    lines.append(f"|-------------|--------|")
    for label, count in sorted(quant_sources.items()):
        icon = "✅" if "enhanced" in label else "⚠️"
        lines.append(f"| {icon} {label} | {count} |")
    lines.append(f"")

    # Phase 17: stock info filtering status
    stock_info = bridge_result.get("stock_info_sources", {})
    if stock_info:
        st_filtered = stock_info.get("filtered_st", 0)
        inv_filtered = stock_info.get("filtered_invalid", 0)
        si_unknown = stock_info.get("unknown", 0)
        si_ok = stock_info.get("ok", 0)
        if st_filtered > 0 or inv_filtered > 0 or si_unknown > 0:
            lines.append(f"| 股票基础信息过滤 | 数量 |")
            lines.append(f"|-----------------|------|")
            lines.append(f"| ✅ 检查通过 | {si_ok} |")
            if st_filtered > 0:
                lines.append(f"| ⚠️ ST 过滤 | {st_filtered} |")
            if inv_filtered > 0:
                lines.append(f"| ⚠️ 无效代码/名称 | {inv_filtered} |")
            if si_unknown > 0:
                lines.append(f"| ⚠️ API 不可达 (保留) | {si_unknown} |")
            lines.append(f"")

    # 数据来源总述
    lines.append(f"## 数据来源")
    lines.append(f"")
    # Phase 22: show sector input source
    sector_src = bridge_result.get("sector_input_source", "legacy_sector_scores")
    if sector_src.startswith("stable"):
        lines.append(f"- **板块评分来源**: {sector_src} (reports/full90 + full_concept/{score_as_of_date}/)")
    else:
        lines.append(f"- **板块评分来源**: reports/sector_scores/{score_as_of_date}/")
    lines.append(f"- **板块关联度**: 成分股权重(0.2) + 涨幅排名(0.4) + 资金流对齐(0.4)")
    # Determine quant source description
    first_stock = score_source_rows[0] if score_source_rows else None
    if first_stock:
        qs = first_stock.get("quant_source", "fallback")
        if qs == "http_enhanced":
            quant_desc = "HTTP 增强多因子（5日/10日涨幅+回撤+成交额+涨幅+估值）"
        elif qs == "qlib":
            quant_desc = "Qlib Alpha158"
        else:
            quant_desc = "降级多因子（关联度+涨幅+估值）"
    else:
        quant_desc = "降级多因子（关联度+涨幅+估值）"

    lines.append(f"- **量化评分**: {quant_desc}")
    lines.append(f"- **API 状态**: {json.dumps(bridge_result.get('api_status', {}), ensure_ascii=False)}")
    lines.append(f"")

    if not legacy_sector_paths_enabled:
        lines.append("## 方向分 + Linkage V2 主路径候选")
        lines.append("")
        if active_candidates:
            lines.append(_format_stock_table(active_candidates, top_n))
        else:
            lines.append("方向分主路径未形成可用候选，系统保持 fail-closed。")
        lines.append("")

    # 趋势板块
    trend_sectors_info = bridge_result.get("trend_sectors", [])
    lines.append(f"## 趋势板块来源")
    lines.append(f"")
    lines.append(f"| 板块 | 趋势分 | 短线分 | 资金流 | 高关联度个股 |")
    lines.append(f"|------|--------|--------|--------|-------------|")
    for sec in trend_sectors_info:
        lines.append(
            f"| {sec['sector_name']} | {sec.get('trend_score',0):.1f} | "
            f"{sec.get('burst_score',0):.1f} | {sec.get('fund_flow_direction','—')} | "
            f"{sec.get('high_relevance_count',0)}/{sec.get('total_constituents',0)} |"
        )
    lines.append(f"")

    # 趋势 Top10 个股
    lines.append(f"## 趋势板块 Top{top_n} 个股")
    lines.append(f"")
    if not legacy_sector_paths_enabled:
        lines.append("趋势板块路径已关闭，本次不参与候选池。")
    elif trend_stocks:
        lines.append(_format_stock_table(trend_stocks, top_n))
    else:
        lines.append(f"⚠️ 无符合条件的个股（关联度 >= {DEFAULT_MIN_RELEVANCE}）")
    lines.append(f"")

    # 短线板块
    burst_sectors_info = bridge_result.get("burst_sectors", [])
    lines.append(f"## 短线板块来源")
    lines.append(f"")
    lines.append(f"| 板块 | 趋势分 | 短线分 | 资金流 | 高关联度个股 |")
    lines.append(f"|------|--------|--------|--------|-------------|")
    for sec in burst_sectors_info:
        lines.append(
            f"| {sec['sector_name']} | {sec.get('trend_score',0):.1f} | "
            f"{sec.get('burst_score',0):.1f} | {sec.get('fund_flow_direction','—')} | "
            f"{sec.get('high_relevance_count',0)}/{sec.get('total_constituents',0)} |"
        )
    lines.append(f"")

    # 短线 Top10 个股
    lines.append(f"## 短线板块 Top{top_n} 个股")
    lines.append(f"")
    if not legacy_sector_paths_enabled:
        lines.append("短线板块路径已关闭，本次不参与候选池。")
    elif burst_stocks:
        lines.append(_format_stock_table(burst_stocks, top_n))
    else:
        lines.append(f"⚠️ 无符合条件的个股（关联度 >= {DEFAULT_MIN_RELEVANCE}）")
    lines.append(f"")

    # 重叠板块
    cross = bridge_result.get("cross_sectors", [])
    if cross:
        lines.append(f"## 重叠板块（同时出现在趋势和短线 Top）")
        lines.append(f"")
        lines.append(f"板块: {', '.join(cross)}")
        lines.append(f"")

    # 评分说明
    lines.append(f"## 评分公式")
    lines.append(f"")
    lines.append(f"```")
    lines.append(f"综合分 = 量化分 × 0.6 + 板块关联度 × 0.4")
    lines.append(f"板块关联度 = 成分股权重分 × 0.2 + 涨幅排名分 × 0.4 + 资金流对齐 × 0.4")
    lines.append(f"```")
    lines.append(f"")

    # 声明
    lines.append(f"---")
    lines.append(f"*本报告由 Unified Pipeline 自动生成。*")

    return "\n".join(lines)


# ============================================================
# 主流程
# ============================================================


def run_pipeline(
    as_of_date: Optional[str] = None,
    trend_top_n: int = DEFAULT_TREND_TOP_N,
    burst_top_n: int = DEFAULT_BURST_TOP_N,
    min_relevance: float = DEFAULT_MIN_RELEVANCE,
    output_dir: Optional[str] = None,
    mode: str = "quick",
    sector_history_root: Optional[str] = None,
    sector_cluster_map_path: Optional[str] = None,
    candidate_chain: str = "direction_linkage_v2",
) -> Dict[str, Any]:
    """
    运行联合选股管线。

    Args:
        as_of_date: 分析日期
        trend_top_n: 趋势板块 Top N
        burst_top_n: 短线板块 Top N
        min_relevance: 最小关联度
        output_dir: 输出目录
        mode: "quick" 或 "deep"
        candidate_chain: 默认使用 direction_linkage_v2；legacy 仅显式启用

    Returns:
        完整的管线结果
    """
    legacy_sector_paths_enabled = candidate_chain == "legacy"
    result = {
        "status": "ok",
        "as_of_date": None,
        "score_as_of_date": None,
        "mode": mode,
        "trend_top_stocks": [],
        "burst_top_stocks": [],
        "active_top_stocks": [],
        "active_candidates_all": [],
        "formal_candidate_selection": {},
        "candidate_chain": candidate_chain,
        "legacy_sector_paths_enabled": legacy_sector_paths_enabled,
        "active_sector_path": (
            "legacy_trend_burst"
            if legacy_sector_paths_enabled
            else "direction_score"
        ),
        "direction_shadow_candidates_all": [],
        "direction_linkage_v2_selection_shadow": {},
        "direction_shadow_runtime_audit": {},
        "quant_score_shadow_audit": {},
        "sector_cluster_map": {},
        "bridge_result": None,
        "warnings": [],
        "generated_at": datetime.now().isoformat(),
    }

    # Step 1: 运行桥接
    print(f"\n{'='*70}")
    print(f"🚀 板块雷达 × 个股选股 联合管线")
    print(f"   模式: {'快速' if mode == 'quick' else '深度'}")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    score_ok, validated_score_report, score_error = validate_explicit_score_report(
        as_of_date
    )
    if not score_ok:
        result["status"] = "failed"
        result["warnings"].append(score_error or "显式报告根校验失败")
        return result

    http_client = _get_http_client()
    market_data_service_reachable = _http_client_is_healthy(http_client)
    if not market_data_service_reachable:
        result["warnings"].append("api_unavailable_fast_path")

    bridge_result = run_bridge(
        as_of_date=as_of_date,
        trend_top_n=trend_top_n,
        burst_top_n=burst_top_n,
        min_relevance=min_relevance,
        include_legacy_sector_paths=legacy_sector_paths_enabled,
        _validated_score_report=validated_score_report,
    )

    if bridge_result["status"] == "failed":
        result["status"] = "failed"
        result["warnings"] = bridge_result.get("warnings", [])
        print(f"\n❌ 桥接失败: {bridge_result.get('warnings', [])}")
        return result

    # Keep the requested research date while preserving the actual score snapshot date.
    result["as_of_date"] = as_of_date or bridge_result["as_of_date"]
    result["score_as_of_date"] = bridge_result["as_of_date"]
    result["bridge_result"] = bridge_result

    # Step 2: 收集所有高关联度个股
    print(f"\n{'─'*70}")
    print(f"📊 Step 2: 个股量化评分")
    print(f"{'─'*70}")

    # Phase 17/18: stock info stats
    _stock_info_stats = {"ok": 0, "filtered_st": 0, "filtered_invalid": 0, "unknown": 0}

    def _validate_stocks(stocks: list, label: str) -> list:
        """Filter invalid/ST stocks using batch /stocks/info/batch → single → unknown.

        Phase 18: batch first with single fallback; Phase 17 rules preserved.
        """
        http_client = _get_http_client() if market_data_service_reachable else None
        filtered: list = []
        code_set = list({s.get("code", "").strip() for s in stocks
                        if s.get("code", "").strip() and len(s.get("code", "").strip()) == 6})

        # ---- Attempt 1: batch stock info ----
        batch_items: dict[str, dict] = {}
        if http_client and code_set:
            try:
                batch_result = http_client.get_stock_info_batch(code_set)
                if batch_result and batch_result.get("items"):
                    batch_items = batch_result["items"]
            except Exception:
                pass

        # ---- Validate each stock ----
        for s in stocks:
            code = s.get("code", "").strip()
            # Basic sanity checks (always run)
            if not code or len(code) != 6 or not code.isdigit():
                _stock_info_stats["filtered_invalid"] += 1
                continue
            name = s.get("name", "").strip()
            if not name:
                _stock_info_stats["filtered_invalid"] += 1
                continue

            # Try batch result first
            info = batch_items.get(code.zfill(6))
            if info is not None and batch_items:
                pass  # use batch info
            elif http_client:
                # ---- Attempt 2: single stock info ----
                try:
                    info = http_client.get_stock_info(code)
                except Exception:
                    info = None
            else:
                info = None

            if info is None:
                # API failed → keep but mark unknown
                _stock_info_stats["unknown"] += 1
                filtered.append(s)
                continue

            # Filter ST stocks
            if info.get("is_st"):
                _stock_info_stats["filtered_st"] += 1
                continue

            # Filter by listed_status if present
            status = info.get("listed_status", "")
            if status and status not in ("listed", "normal", "active", ""):
                _stock_info_stats["filtered_invalid"] += 1
                continue

            _stock_info_stats["ok"] += 1
            filtered.append(s)

        if _stock_info_stats["filtered_st"] > 0 or _stock_info_stats["filtered_invalid"] > 0:
            removed = _stock_info_stats["filtered_st"] + _stock_info_stats["filtered_invalid"]
            print(f"    [{label}] 过滤 {removed} 只 (ST={_stock_info_stats['filtered_st']}, invalid={_stock_info_stats['filtered_invalid']})")
        return filtered

    sector_returns_by_name: Dict[str, Dict[str, float]] = {}
    sector_history_warnings = []
    if sector_history_root and result.get("score_as_of_date"):
        for sector_type in (SectorType.INDUSTRY, SectorType.CONCEPT):
            histories, warnings = load_sector_trend_history(
                sector_history_root,
                sector_type=sector_type,
                as_of_date=result["score_as_of_date"],
                max_returns=20,
            )
            sector_history_warnings.extend(warnings)
            for name, history in histories.items():
                sector_returns_by_name[name] = dict(
                    zip(history["recent_dates"], history["recent_returns"])
                )
    result["linkage_v2_history"] = {
        "mode": "paper_shadow_research_only",
        "root": sector_history_root,
        "sector_count": len(sector_returns_by_name),
        "warnings": sector_history_warnings,
    }

    def _collect_and_score(sector_list: List[Dict], label: str) -> List[Dict]:
        all_stocks = []
        seen_codes = set()
        for sec in sector_list:
            for s in sec.get("stocks", []):
                code = s["code"]
                if code not in seen_codes:
                    seen_codes.add(code)
                    s["sector_name"] = sec["sector_name"]
                    s["sector_trend_score"] = sec.get("trend_score", 0)
                    s["sector_burst_score"] = _get_sector_burst_score(sec)
                    all_stocks.append(s)

        if not all_stocks:
            print(f"  ⚠️ [{label}] 无高关联度个股")
            return []

        # Phase 17: validate stocks via /stocks/{code}/info
        all_stocks = _validate_stocks(all_stocks, label)
        if not all_stocks:
            print(f"  ⚠️ [{label}] 过滤后无有效个股")
            return []

        # 量化打分
        print(f"  [{label}] {len(all_stocks)} 只个股，计算量化评分...")
        all_stocks = compute_quant_scores(
            all_stocks,
            as_of_date=bridge_result.get("as_of_date"),
            http_enabled=market_data_service_reachable,
            sector_returns_by_name=sector_returns_by_name,
        )

        # 综合排序
        all_stocks = compute_final_scores(all_stocks)
        _annotate_score_breakdown(all_stocks)  # Phase 20

        # 输出 Top N
        top_n = min(10, len(all_stocks))
        print(f"  [{label}] Top{top_n}:")
        for i, s in enumerate(all_stocks[:top_n], 1):
            print(f"    {i:2d}. {s['code']} {s.get('name',''):<8} "
                  f"综合:{s['final_score']:.1f} 量化:{s['quant_score']:.1f} "
                  f"关联:{s['relevance_score']:.3f} [{s['sector_name']}]")

        return all_stocks

    compute_quant_scores._last_fund_flow_source = "not_evaluated"
    if legacy_sector_paths_enabled:
        trend_stocks = _collect_and_score(
            bridge_result.get("trend_sectors", []), "趋势"
        )
        burst_stocks = _collect_and_score(
            bridge_result.get("burst_sectors", []), "短线"
        )
    else:
        trend_stocks = []
        burst_stocks = []

    legacy_stock_info_stats = dict(_stock_info_stats)
    legacy_fund_flow_source = getattr(
        compute_quant_scores, "_last_fund_flow_source", "fund_flow_neutral"
    )
    _stock_info_stats = {
        "ok": 0,
        "filtered_st": 0,
        "filtered_invalid": 0,
        "unknown": 0,
    }
    compute_quant_scores._last_fund_flow_source = "not_evaluated"

    cluster_map_path = sector_cluster_map_path or str(
        DEFAULT_SECTOR_CLUSTER_MAP_PATH
    )
    try:
        sector_cluster_map, sector_cluster_audit = load_sector_cluster_map(
            cluster_map_path
        )
    except (OSError, ValueError, TypeError) as exc:
        sector_cluster_map = {}
        sector_cluster_audit = {
            "schema_version": "path_a_sector_cluster_map.v1",
            "mode": "paper_shadow_research_only",
            "status": "unavailable",
            "path": str(Path(cluster_map_path).expanduser().resolve()),
            "sha256": None,
            "cluster_count": 0,
            "mapped_sector_count": 0,
            "mapping": {},
            "error": str(exc),
            "disclaimer": "No broker connection and no live order instruction.",
        }
    result["sector_cluster_map"] = sector_cluster_audit

    direction_shadow_stocks = []
    for sector in bridge_result.get("direction_shadow_sectors", []):
        for source in sector.get("shadow_prefilter_stocks", []):
            stock = dict(source)
            stock["sector_name"] = sector["sector_name"]
            stock["sector_type"] = sector.get("sector_type", "industry")
            stock["candidate_tier"] = sector.get("candidate_tier")
            stock["sector_trend_score"] = sector.get("trend_score", 0)
            stock["sector_burst_score"] = sector.get("burst_score", 0)
            stock["sector_direction_score"] = sector.get(
                "direction_score_shadow"
            )
            stock["direction_score_shadow"] = sector.get(
                "direction_score_shadow"
            )
            stock["direction_state"] = sector.get("direction_state")
            direction_shadow_stocks.append(stock)
    direction_shadow_stocks = _validate_stocks(
        direction_shadow_stocks, "direction_shadow"
    )
    direction_bars_client = None
    direction_bars_init_error = None
    if direction_shadow_stocks and sector_returns_by_name:
        try:
            direction_bars_client = AutoBarsClient(
                http_client=http_client,
                expected_min_date=bridge_result.get("as_of_date"),
            )
        except (ImportError, OSError, ConnectionError, RuntimeError, ValueError) as exc:
            direction_bars_init_error = str(exc)
    compute_quant_scores._last_bars_audit = {
        "source": "not_evaluated",
        "reason": "not_evaluated",
        "latest_daily_date": None,
        "requested_stock_count": len(
            {stock["code"] for stock in direction_shadow_stocks}
        ),
        "usable_stock_count": 0,
        "requested_relation_count": len(direction_shadow_stocks),
        "usable_relation_count": 0,
        "coverage_ratio": 0.0,
        "minimum_bars": 5,
    }
    if direction_shadow_stocks:
        direction_shadow_stocks = compute_quant_scores(
            direction_shadow_stocks,
            as_of_date=bridge_result.get("as_of_date"),
            http_enabled=market_data_service_reachable,
            sector_returns_by_name=sector_returns_by_name,
            bars_client_override=direction_bars_client,
        )
    direction_bars_audit = dict(
        getattr(compute_quant_scores, "_last_bars_audit", {})
    )
    quant_shadow_audit = dict(
        getattr(compute_quant_scores, "_last_quant_shadow_audit", {})
    )
    shadow_context = {
        "as_of_date": bridge_result.get("as_of_date"),
        "universe_id": "direction_shadow_candidates_all",
        "candidate_chain": candidate_chain,
    }
    quant_shadow_audit["cross_sectional_context"] = shadow_context
    for stock in direction_shadow_stocks:
        stock["quant_score_shadow_cross_sectional_universe"] = shadow_context[
            "universe_id"
        ]
        stock["quant_score_shadow_cross_sectional_as_of"] = shadow_context[
            "as_of_date"
        ]
        stock["quant_score_shadow_cross_sectional_candidate_chain"] = shadow_context[
            "candidate_chain"
        ]
    compute_quant_scores._last_quant_shadow_audit = quant_shadow_audit
    if (
        direction_bars_init_error
        and not direction_bars_client
        and direction_bars_audit.get("source") in {"unavailable", "not_evaluated"}
    ):
        direction_bars_audit.update(
            {
                "source": "unavailable",
                "reason": "stockdb_sdk_unavailable",
                "latest_daily_date": None,
                "error": direction_bars_init_error,
            }
        )
    direction_linkage_selection = select_direction_linkage_v2_shadow_stocks(
        direction_shadow_stocks,
        sector_cluster_map=sector_cluster_map,
    )
    result["direction_shadow_candidates_all"] = direction_shadow_stocks
    result["direction_linkage_v2_selection_shadow"] = direction_linkage_selection
    direction_source = (
        bridge_result.get("linkage_research", {}).get("direction_shadow_input", {})
    )
    formal_candidate_selection = _activate_formal_candidate_chain(
        candidate_chain=candidate_chain,
        direction_source=direction_source,
        linkage_selection=direction_linkage_selection,
        legacy_candidates=trend_stocks + burst_stocks,
    )
    result["formal_candidate_selection"] = formal_candidate_selection
    result["active_candidates_all"] = formal_candidate_selection["selected"]
    result["active_top_stocks"] = formal_candidate_selection["selected"][:10]
    if (
        candidate_chain == "direction_linkage_v2"
        and formal_candidate_selection["status"] != "active_for_paper_research"
    ):
        result["warnings"].append(
            "formal_replacement_unavailable: "
            + str(formal_candidate_selection.get("error") or "unknown")
        )
    result["direction_shadow_runtime_audit"] = {
        "mode": "paper_shadow_research_only",
        "stock_info_sources": dict(_stock_info_stats),
        "fund_flow_source": getattr(
            compute_quant_scores, "_last_fund_flow_source", "not_evaluated"
        ),
        "bars_source": direction_bars_audit.get("source", "unavailable"),
        "bars_reason": direction_bars_audit.get("reason", "not_evaluated"),
        "latest_daily_date": direction_bars_audit.get("latest_daily_date"),
        "stock_bar_coverage": {
            "requested_stock_count": direction_bars_audit.get(
                "requested_stock_count", len(direction_shadow_stocks)
            ),
            "usable_stock_count": direction_bars_audit.get(
                "usable_stock_count", 0
            ),
            "requested_relation_count": direction_bars_audit.get(
                "requested_relation_count", len(direction_shadow_stocks)
            ),
            "usable_relation_count": direction_bars_audit.get(
                "usable_relation_count", 0
            ),
            "coverage_ratio": direction_bars_audit.get("coverage_ratio", 0.0),
            "minimum_bars": direction_bars_audit.get("minimum_bars", 5),
        },
        "quant_score_shadow_audit": getattr(
            compute_quant_scores, "_last_quant_shadow_audit", {}
        ),
        "disclaimer": "No broker connection and no live order instruction.",
    }
    result["quant_score_shadow_audit"] = result["direction_shadow_runtime_audit"][
        "quant_score_shadow_audit"
    ]
    if direction_bars_audit.get("error"):
        result["direction_shadow_runtime_audit"]["bars_error"] = (
            direction_bars_audit["error"]
        )

    # Embed stock info stats into bridge result for reporting
    bridge_result["stock_info_sources"] = (
        dict(legacy_stock_info_stats)
        if legacy_sector_paths_enabled
        else dict(_stock_info_stats)
    )

    # Save complete candidate lists for export_top30_candidates.py
    result["trend_top_stocks"] = trend_stocks[:10]  # Top10 for display
    result["burst_top_stocks"] = burst_stocks[:10]  # Top10 for display
    result["trend_candidates_all"] = trend_stocks  # Complete list for candidate pool
    result["burst_candidates_all"] = burst_stocks  # Complete list for candidate pool

    # Build source summaries
    quant_sources: Dict[str, int] = {}
    scored_source_rows = (
        trend_stocks + burst_stocks
        if legacy_sector_paths_enabled
        else direction_shadow_stocks
    )
    for s in scored_source_rows:
        qs = s.get("quant_source", "fallback")
        quant_sources[qs] = quant_sources.get(qs, 0) + 1

    source_summary = bridge_result.get("constituent_source_summary", {})
    active_fund_flow_source = (
        legacy_fund_flow_source
        if legacy_sector_paths_enabled
        else result["direction_shadow_runtime_audit"].get(
            "fund_flow_source", "not_evaluated"
        )
    )
    result["data_source"] = {
        "constituent_sources": dict(source_summary),
        "quant_score_sources": quant_sources,
        "fund_flow_source": active_fund_flow_source,
        "stock_info_sources": (
            dict(legacy_stock_info_stats)
            if legacy_sector_paths_enabled
            else dict(_stock_info_stats)
        ),
        "market_data_service_reachable": market_data_service_reachable,
        "api_fast_path": "http_enabled" if market_data_service_reachable else "api_unavailable_fast_path",
        "sector_input_source": bridge_result.get("sector_input_source", "legacy_sector_scores"),
        "candidate_chain": candidate_chain,
        "legacy_sector_paths_enabled": legacy_sector_paths_enabled,
        "active_sector_path": result["active_sector_path"],
        "formal_candidate_status": formal_candidate_selection["status"],
        "has_unavailable_sectors": source_summary.get("unavailable", 0) > 0,
        "has_emergency_fallback": source_summary.get("local_emergency_mapping", 0) > 0,
    }
    result["run_health"] = evaluate_run_health(result["data_source"])
    result["data_quality"] = build_data_quality_summary(
        result["data_source"], result["run_health"]
    )

    # Step 3: 输出报告
    print(f"\n{'─'*70}")
    print(f"📁 Step 3: 生成报告")
    print(f"{'─'*70}")

    actual_date = result["as_of_date"]
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = PROJECT_ROOT / "reports" / "unified" / (actual_date or "unknown")

    out_path.mkdir(parents=True, exist_ok=True)

    # JSON 报告
    json_report = {
        "report_type": "unified_pipeline",
        "version": "0.1.0",
        "as_of_date": actual_date,
        "score_as_of_date": result["score_as_of_date"],
        "generated_at": result["generated_at"],
        "mode": mode,
        "trend_top_stocks": result["trend_top_stocks"],
        "burst_top_stocks": result["burst_top_stocks"],
        "active_top_stocks": result["active_top_stocks"],
        "active_candidates_all": result["active_candidates_all"],
        "formal_candidate_selection": result["formal_candidate_selection"],
        "candidate_chain": result["candidate_chain"],
        "legacy_sector_paths_enabled": result["legacy_sector_paths_enabled"],
        "active_sector_path": result["active_sector_path"],
        "trend_candidates_all": result["trend_candidates_all"],
        "burst_candidates_all": result["burst_candidates_all"],
        "direction_shadow_candidates_all": result[
            "direction_shadow_candidates_all"
        ],
        "direction_linkage_v2_selection_shadow": result[
            "direction_linkage_v2_selection_shadow"
        ],
        "direction_shadow_runtime_audit": result[
            "direction_shadow_runtime_audit"
        ],
        "quant_score_shadow_audit": result["quant_score_shadow_audit"],
        "bridge_summary": {
            "trend_sectors": [
                {"name": s["sector_name"], "trend_score": s["trend_score"],
                 "burst_score": _get_sector_burst_score(s), "count": s["high_relevance_count"]}
                for s in (
                    bridge_result.get("trend_sectors", [])
                    if legacy_sector_paths_enabled
                    else []
                )
            ],
            "burst_sectors": [
                {"name": s["sector_name"], "trend_score": s["trend_score"],
                 "burst_score": _get_sector_burst_score(s), "count": s["high_relevance_count"]}
                for s in (
                    bridge_result.get("burst_sectors", [])
                    if legacy_sector_paths_enabled
                    else []
                )
            ],
            "cross_sectors": (
                bridge_result.get("cross_sectors", [])
                if legacy_sector_paths_enabled
                else []
            ),
            "score_as_of_date": result["score_as_of_date"],
            "api_status": bridge_result.get("api_status", {}),
            "constituent_source_summary": bridge_result.get("constituent_source_summary", {}),
        },
        "linkage_research": {
            "mode": "paper_shadow_research_only",
            "bridge": bridge_result.get("linkage_research", {}),
            "history": result.get("linkage_v2_history", {}),
            "sector_cluster_map": result.get("sector_cluster_map", {}),
            "direction_summary": _build_direction_linkage_summary(
                result["direction_shadow_candidates_all"],
                result["direction_linkage_v2_selection_shadow"],
                result.get("linkage_v2_history", {}),
                bridge_result.get("direction_confirmation_sectors", []),
            ),
        },
        "data_source": result["data_source"],
        "run_health": result["run_health"],
        "data_quality": result["data_quality"],
        "scoring_method": {
            "quant_source": (
                scored_source_rows[0].get("quant_source", "fallback")
                if scored_source_rows
                else "unavailable"
            ),
            "weights": {"quant": WEIGHT_QUANT, "relevance": WEIGHT_RELEVANCE},
            "min_relevance": min_relevance,
            "legacy_sector_paths_enabled": legacy_sector_paths_enabled,
            "active_candidate_ranking": (
                "linkage_selection_score"
                if candidate_chain == "direction_linkage_v2"
                else "final_score"
            ),
        },
        "warnings": result["warnings"],
        "disclaimer": "本报告仅用于板块研究和选股参考，不作为操作依据。",
    }

    json_file = out_path / "unified_report.json"
    json_text = json.dumps(
        json_report,
        ensure_ascii=False,
        indent=2,
        default=str,
        allow_nan=False,
    ) + "\n"
    json_tmp_file = json_file.with_name(json_file.name + ".tmp")
    try:
        with open(json_tmp_file, "w", encoding="utf-8", newline="") as f:
            f.write(json_text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(json_tmp_file, json_file)
    except Exception:
        try:
            json_tmp_file.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    print(f"  ✅ JSON: {json_file}")

    # Markdown 报告
    md_content = generate_markdown_report(
        as_of_date=actual_date,
        trend_stocks=trend_stocks,
        burst_stocks=burst_stocks,
        bridge_result=bridge_result,
        run_health=result.get("run_health"),
        data_quality=result.get("data_quality"),
        candidate_chain=candidate_chain,
        active_candidates=result["active_candidates_all"],
    )
    md_file = out_path / "unified_report.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"  ✅ Markdown: {md_file}")

    # 摘要
    print(f"\n{'='*70}")
    print(f"✅ 联合管线完成")
    print(f"{'='*70}")
    print(f"  日期: {actual_date}")
    print(f"  模式: {mode}")
    health = result.get("run_health", {})
    icon = _HEALTH_ICON.get(health.get("status", ""), "")
    print(f"  {icon} 健康门禁: {health.get('status', 'N/A').upper()}")
    for reason in health.get("reasons", []):
        print(f"    - {reason}")
    if legacy_sector_paths_enabled:
        print(f"  趋势 Top10: {len(trend_stocks)} 只")
        print(f"  短线 Top10: {len(burst_stocks)} 只")
    else:
        print("  趋势/短线路径: 已关闭")
        print(f"  方向分主路径候选: {len(result['active_candidates_all'])} 只")
    print(f"  报告目录: {out_path}")

    return result


# ============================================================
# CLI 入口
# ============================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="板块雷达 × 个股选股 联合管线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 快速模式
  python unified_pipeline.py --as-of 2026-07-01 --mode quick

  # 指定参数
  python unified_pipeline.py --as-of 2026-07-01 --trend-top-n 5 --burst-top-n 5 --min-relevance 0.6
        """,
    )
    parser.add_argument("--as-of", type=str, default=None, help="分析日期 (YYYY-MM-DD)")
    parser.add_argument("--trend-top-n", type=int, default=DEFAULT_TREND_TOP_N, help="趋势板块 Top N")
    parser.add_argument("--burst-top-n", type=int, default=DEFAULT_BURST_TOP_N, help="短线板块 Top N")
    parser.add_argument("--min-relevance", type=float, default=DEFAULT_MIN_RELEVANCE, help="最小关联度")
    parser.add_argument("--output", type=str, default=None, help="输出目录")
    parser.add_argument("--mode", type=str, choices=["quick", "deep"], default="quick", help="运行模式")
    parser.add_argument(
        "--sector-history-root",
        type=str,
        default=None,
        help="Explicit sector history root for linkage V2 shadow",
    )
    parser.add_argument(
        "--sector-cluster-map",
        type=str,
        default=None,
        help="Strict paper/shadow sector cluster map JSON",
    )
    parser.add_argument(
        "--candidate-chain",
        choices=["legacy", "direction_linkage_v2"],
        default="direction_linkage_v2",
        help="Active paper-research candidate chain",
    )
    args = parser.parse_args()

    result = run_pipeline(
        as_of_date=args.as_of,
        trend_top_n=args.trend_top_n,
        burst_top_n=args.burst_top_n,
        min_relevance=args.min_relevance,
        output_dir=args.output,
        mode=args.mode,
        sector_history_root=args.sector_history_root,
        sector_cluster_map_path=args.sector_cluster_map,
        candidate_chain=args.candidate_chain,
    )

    sys.exit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
