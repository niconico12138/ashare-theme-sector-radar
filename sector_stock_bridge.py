#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块-个股桥接层（Sector-Stock Bridge）

读取 Theme Sector Radar 板块评分报告，查询板块成分股，
计算三维度板块关联度（成分股权重 × 涨幅排名 × 资金流对齐）。

输出结构化数据供 unified_pipeline.py 使用。

关联度公式:
  relevance_score = weight_score * 0.2 + rank_score * 0.4 + flow_alignment * 0.4

数据源:
  - 板块评分: theme-sector-radar reports/sector_scores/
  - 成分股: AkShare stock_board_industry_cons_em / stock_board_concept_cons_em
  - 实时行情: 腾讯 API qt.gtimg.cn
  - 资金流: 东方财富（降级: 新浪 / 中性值）
"""

import json
import logging
import os
import re
import sys
import time

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 代理环境变量清理（避免 Clash Verge 干扰）
# ============================================================

_PROXY_KEYS = [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
]


def _clear_proxy_env():
    """清理代理环境变量，确保直连"""
    for k in _PROXY_KEYS:
        if k in os.environ:
            del os.environ[k]


# 清理一次即可
_clear_proxy_env()

logger = logging.getLogger(__name__)


# ============================================================
# 常量
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
SCORES_DIR = PROJECT_ROOT / "reports" / "sector_scores"
CACHE_DIR = PROJECT_ROOT / "data_cache" / "sector_stocks"

# Phase 22: stable data directories
STABLE_RESEARCH_DIR = PROJECT_ROOT / "reports" / "full90" / "sector_research"
STABLE_CONCEPT_DIR = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"

# 关联度权重
W_WEIGHT = 0.2
W_RANK = 0.4
W_FLOW = 0.4

# 资金流对齐系数
FLOW_BOTH_INFLOW = 1.2
FLOW_BOTH_OUTFLOW = 0.8
FLOW_INDIVIDUAL逆势 = 0.5
FLOW_INDIVIDUAL背离 = 0.3

DEFAULT_MIN_RELEVANCE = 0.6
DEFAULT_TREND_TOP_N = 5
DEFAULT_BURST_TOP_N = 5

# ============================================================
# 板块成分股内置映射（东方财富被封锁时的降级方案）
# ============================================================

SECTOR_STOCK_MAPPING = {
    "证券": [
        ("600030", "中信证券"), ("601211", "国泰君安"), ("600999", "招商证券"),
        ("601688", "华泰证券"), ("600036", "兴业证券"), ("601066", "中信建投"),
        ("600837", "海通证券"), ("000776", "广发证券"), ("601881", "中国银河"),
        ("000166", "申万宏源"), ("601377", "兴业证券"), ("600958", "东方证券"),
        ("002736", "国信证券"), ("601198", "东兴证券"), ("601878", "浙商证券"),
    ],
    "保险": [
        ("601318", "中国平安"), ("601628", "中国人寿"), ("601601", "中国太保"),
        ("2318", "中国平安H"), ("601336", "新华保险"), ("000627", "天茂集团"),
        ("600919", "江苏金租"),
    ],
    "化学制药": [
        ("600276", "恒瑞医药"), ("000538", "云南白药"), ("002001", "新和成"),
        ("600196", "复星医药"), ("000963", "华东医药"), ("002004", "华邦健康"),
        ("600867", "通化东宝"), ("000963", "华东医药"), ("002422", "科伦药业"),
        ("300003", "乐普医疗"), ("600079", "人福医药"), ("002001", "新和成"),
    ],
    "医疗服务": [
        ("300347", "泰格医药"), ("300759", "康龙化成"), ("603259", "药明康德"),
        ("300015", "爱尔眼科"), ("300760", "迈瑞医疗"), ("000516", "国际医学"),
        ("300003", "乐普医疗"), ("300122", "智飞生物"), ("002044", "美年健康"),
    ],
    "养殖业": [
        ("002714", "牧原股份"), ("300498", "温氏股份"), ("000876", "新希望"),
        ("002311", "海大集团"), ("603609", "禾丰牧业"), ("002157", "正邦科技"),
        ("002567", "唐人神"),
    ],
    "教育": [
        ("002607", "中公教育"), ("300010", "豆神教育"), ("300338", "开元教育"),
        ("002638", "勤上股份"), ("300192", "科德教育"),
    ],
    "农产品加工": [
        ("002311", "海大集团"), ("002505", "金字火腿"), ("002582", "好想你"),
        ("600598", "北大荒"), ("000061", "农产品"), ("600127", "金健米业"),
    ],
    "多元金融": [
        ("600053", "九鼎投资"), ("000563", "陕国投A"), ("600830", "香溢融通"),
        ("000416", "民生控股"), ("600318", "新力金融"),
    ],
    "物流": [
        ("002352", "顺丰控股"), ("603128", "华贸物流"), ("600009", "上海机场"),
        ("002468", "申通快递"), ("002120", "韵达股份"), ("603056", "德邦股份"),
    ],
    "生物制品": [
        ("600196", "复星医药"), ("002007", "华兰生物"), ("300122", "智飞生物"),
        ("300601", "康泰生物"), ("300347", "泰格医药"), ("300759", "康龙化成"),
        ("600739", "辽宁成大"),
    ],
    # ---- 补充高频 Top 板块 ----
    "电子化学品": [
        ("603078", "江化微"), ("002915", "德维新材"), ("300236", "上海新阳"),
        ("688268", "华特气体"), ("300346", "南大光电"), ("002409", "雅克科技"),
        ("300243", "瑞丰光电"),
    ],
    "半导体": [
        ("688981", "中芯国际"), ("002371", "北方华创"), ("603501", "韦尔股份"),
        ("688012", "中微公司"), ("688036", "传音控股"), ("002049", "紫光国微"),
        ("688008", "澜起科技"), ("300782", "卓胜微"),
    ],
    "小金属": [
        ("002460", "赣锋锂业"), ("300750", "宁德时代"), ("002466", "天齐锂业"),
        ("600489", "中金黄金"), ("000762", "西藏矿业"), ("002155", "湖南黄金"),
        ("600259", "广晟有色"),
    ],
    "光学光电子": [
        ("000725", "京东方A"), ("000100", "TCL科技"), ("002450", "欧菲光"),
        ("300450", "先导智能"), ("600703", "三安光电"), ("300136", "信维通信"),
        ("002241", "歌尔股份"),
    ],
    "厨卫电器": [
        ("002508", "老板电器"), ("002032", "苏泊尔"), ("002543", "万和电气"),
        ("603868", "飞科电器"), ("002614", "奥佳华"),
    ],
    "中药": [
        ("600436", "片仔癀"), ("000538", "云南白药"), ("002349", "精华制药"),
        ("600085", "同仁堂"), ("000423", "东阿阿胶"), ("600332", "白云山"),
        ("002422", "科伦药业"),
    ],
    "能源金属": [
        ("002460", "赣锋锂业"), ("002466", "天齐锂业"), ("300750", "宁德时代"),
        ("688567", "孚能科技"), ("002812", "恩捷股份"),
    ],
    "贵金属": [
        ("600489", "中金黄金"), ("600547", "山东黄金"), ("002155", "湖南黄金"),
        ("600988", "赤峰黄金"), ("601069", "西部黄金"), ("000975", "山金国际"),
        ("000506", "招金黄金"),
    ],
    # ---- 新增高频板块（2026-07-03 扩展） ----
    "印染": [
        ("600987", "航民股份"), ("600448", "华纺股份"), ("002083", "孚日股份"),
        ("002440", "闰土股份"), ("603980", "吉华集团"), ("002099", "海翔药业"),
        ("002394", "联发股份"), ("002493", "荣盛石化"),
    ],
    "水产饲料": [
        ("600438", "通威股份"), ("002311", "海大集团"), ("001313", "粤海饲料"),
        ("002567", "唐人神"), ("603609", "禾丰牧业"), ("002385", "大北农"),
        ("300498", "温氏股份"), ("002157", "正邦科技"),
    ],
    "黄金": [
        ("600547", "山东黄金"), ("600489", "中金黄金"), ("600988", "赤峰黄金"),
        ("002155", "湖南黄金"), ("601069", "西部黄金"), ("000975", "山金国际"),
        ("002237", "恒邦股份"), ("600531", "豫光金铅"),
    ],
    "辅料": [
        ("002003", "伟星股份"), ("002098", "浔兴股份"), ("002191", "劲嘉股份"),
        ("603687", "大胜达"), ("002886", "沃特股份"), ("002945", "华林证券"),
    ],
    "其他数字媒体": [
        ("603466", "风语筑"), ("300079", "数码视讯"), ("002261", "拓维信息"),
        ("300113", "顺网科技"), ("300792", "壹网壹创"), ("300295", "三六五网"),
        ("300459", "汤姆猫"),
    ],
    "家居用品": [
        ("603816", "顾家家居"), ("603008", "喜临门"), ("002572", "索菲亚"),
        ("603898", "好莱客"), ("002790", "瑞尔特"), ("002853", "皮阿诺"),
    ],
    "电机": [
        ("002249", "大洋电机"), ("600580", "卧龙电驱"), ("002176", "江特电机"),
        ("002576", "通达动力"), ("300222", "科大智能"), ("300124", "汇川技术"),
    ],
    "其他社会服务": [
        ("002033", "宋城演艺"), ("600138", "中青旅"), ("000888", "峨眉山A"),
        ("600054", "黄山旅游"), ("002186", "全聚德"), ("000802", "北京文化"),
        ("000428", "华天酒店"),
    ],
    "游戏": [
        ("002555", "三七互娱"), ("002624", "完美世界"), ("300418", "昆仑万维"),
        ("002517", "恺英网络"), ("002558", "巨人网络"), ("300031", "宝通科技"),
        ("300113", "顺网科技"),
    ],
    "白酒": [
        ("600519", "贵州茅台"), ("000858", "五粮液"), ("000568", "泸州老窖"),
        ("002304", "洋河股份"), ("600809", "山西汾酒"), ("603589", "口子窖"),
        ("000799", "酒鬼酒"), ("600779", "水井坊"),
    ],
    "医疗器械": [
        ("300760", "迈瑞医疗"), ("002223", "鱼跃医疗"), ("300003", "乐普医疗"),
        ("603658", "安图生物"), ("300595", "欧普康视"), ("002432", "九安医疗"),
        ("300244", "迪安诊断"), ("688180", "君实生物"),
    ],
    "工业金属": [
        ("601899", "紫金矿业"), ("600362", "江西铜业"), ("603993", "洛阳钼业"),
        ("000630", "铜陵有色"), ("000878", "云南铜业"), ("600219", "南山铝业"),
        ("601600", "中国铝业"), ("000807", "云铝股份"),
    ],
    "机场航运": [
        ("600009", "上海机场"), ("600115", "中国东航"), ("600029", "南方航空"),
        ("601111", "中国国航"), ("600897", "厦门空港"),
    ],
    "非金属材料": [
        ("002080", "中材科技"), ("600585", "海螺水泥"), ("000786", "北新建材"),
        ("300019", "硅宝科技"), ("603688", "石英股份"),
    ],
}


# ============================================================
# 报告读取
# ============================================================

def find_latest_report(as_of_date: Optional[str] = None) -> Tuple[Optional[str], Optional[Path]]:
    """
    查找最新的 sector_scores.json 报告。

    Args:
        as_of_date: 指定日期，None 则自动查找最新

    Returns:
        (as_of_date, report_path) 或 (None, None)
    """
    if as_of_date:
        report_path = SCORES_DIR / as_of_date / "sector_scores.json"
        if report_path.exists():
            return as_of_date, report_path
        # 尝试 fallback 到最新可用日期
        print(f"  ⚠️ 指定日期 {as_of_date} 无报告，尝试 fallback...")

    # 自动查找最新
    if not SCORES_DIR.exists():
        return None, None

    date_dirs = sorted(
        [d for d in SCORES_DIR.iterdir() if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", d.name)],
        reverse=True,
    )
    for d in date_dirs:
        report_path = d / "sector_scores.json"
        if report_path.exists():
            return d.name, report_path

    return None, None


def load_sector_scores(report_path: Path) -> Dict[str, Any]:
    """加载板块评分报告，返回原始 JSON 数据"""
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_top_sectors(
    data: Dict[str, Any],
    trend_top_n: int = DEFAULT_TREND_TOP_N,
    burst_top_n: int = DEFAULT_BURST_TOP_N,
) -> Tuple[List[Dict], List[Dict]]:
    """
    从板块评分报告中提取趋势 Top N 和短线 Top N 板块。

    Returns:
        (trend_sectors, burst_sectors) 每个元素包含 sector_name + 评分
    """
    scores = data.get("scores", [])

    # 趋势 Top N
    trend_sorted = sorted(scores, key=lambda x: x.get("trend_continuation_score", 0), reverse=True)
    trend_sectors = []
    for s in trend_sorted[:trend_top_n]:
        trend_sectors.append({
            "sector_name": s["sector_name"],
            "sector_type": s.get("sector_type", "industry"),
            "trend_score": s.get("trend_continuation_score", 0),
            "burst_score": s.get("short_term_burst_score", 0),
            "trend_level": s.get("trend_level", ""),
            "trend_level_cn": s.get("trend_level_cn", ""),
        })

    # 短线 Top N
    burst_sorted = sorted(scores, key=lambda x: x.get("short_term_burst_score", 0), reverse=True)
    burst_sectors = []
    for s in burst_sorted[:burst_top_n]:
        burst_sectors.append({
            "sector_name": s["sector_name"],
            "sector_type": s.get("sector_type", "industry"),
            "trend_score": s.get("trend_continuation_score", 0),
            "burst_score": s.get("short_term_burst_score", 0),
            "burst_level": s.get("burst_level", ""),
            "burst_level_cn": s.get("burst_level_cn", ""),
        })

    return trend_sectors, burst_sectors


# ============================================================
# Phase 22: stable sector input loaders
# ============================================================

def load_stable_sector_inputs(as_of_date: str) -> Dict[str, Any]:
    """Load sector inputs from stable production outputs (full90/full_concept).

    Returns a dict with keys:
      - industries: list[dict] (from sector_research.json)
      - concepts: list[dict] (from concept_unified_rank.csv)
      - source: "stable_full90" / "stable_concept" / "mixed" / "legacy_sector_scores"
      - available: bool

    Each industry dict: sector_name, sector_type, ranking_score, opportunity_score,
                        trend_score, burst_score, evidence_score, confidence_score, agent_label

    Each concept dict: sector_name, sector_type, composite_score, trend_score,
                       burst_score, rank, agent_label
    """
    result: Dict[str, Any] = {
        "industries": [],
        "concepts": [],
        "source": "legacy_sector_scores",
        "available": False,
    }

    # --- Load industry from sector_research.json ---
    industry_path = STABLE_RESEARCH_DIR / as_of_date / "sector_research.json"
    if industry_path.exists():
        try:
            data = json.loads(industry_path.read_text(encoding="utf-8"))
            for item in data.get("research_results", []):
                if item.get("sector_type") != "industry":
                    continue
                result["industries"].append({
                    "sector_name": item.get("sector_name", ""),
                    "sector_type": "industry",
                    "ranking_score": item.get("ranking_score", 0),
                    "opportunity_score": item.get("opportunity_score", 0),
                    "evidence_score": item.get("evidence_score", 0),
                    "confidence_score": item.get("confidence_score", 0),
                    "agent_label": item.get("consensus_label", ""),
                })
        except Exception:
            pass

    # --- Load concepts from concept_unified_rank.csv ---
    concept_path = STABLE_CONCEPT_DIR / as_of_date / "concept_unified_rank.csv"
    if concept_path.exists():
        try:
            import csv
            with open(concept_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result["concepts"].append({
                        "sector_name": row.get("sector_name", ""),
                        "sector_type": "concept",
                        "composite_score": float(row.get("concept_final_rank_score", 0) or 0),
                        "trend_score": float(row.get("trend_continuation_score", 0) or 0),
                        "burst_score": float(row.get("short_term_burst_score", 0) or 0),
                        "rank": int(row.get("rank", 0) or 0),
                        "agent_label": row.get("agent_consensus_label", ""),
                    })
        except Exception:
            pass

    # --- Determine source ---
    n_ind = len(result["industries"])
    n_con = len(result["concepts"])
    if n_ind > 0 and n_con > 0:
        result["source"] = "mixed"
        result["available"] = True
    elif n_ind > 0:
        result["source"] = "stable_full90"
        result["available"] = True
    elif n_con > 0:
        result["source"] = "stable_concept"
        result["available"] = True
    # else: remains legacy

    return result


def extract_top_sectors_from_stable(
    stable: Dict[str, Any],
    trend_top_n: int = DEFAULT_TREND_TOP_N,
    burst_top_n: int = DEFAULT_BURST_TOP_N,
) -> Tuple[List[Dict], List[Dict]]:
    """Extract trend/burst top from stable sector inputs.

    Returns (trend_sectors, burst_sectors) matching extract_top_sectors output format.
    """
    all_sectors = stable["industries"] + stable["concepts"]

    # --- Trend pool: sort by ranking_score > opportunity_score > trend_score ---
    trend_sorted = sorted(all_sectors, key=lambda x: (
        x.get("ranking_score", 0) or x.get("composite_score", 0),
        x.get("opportunity_score", 0),
        x.get("trend_score", 0),
    ), reverse=True)

    trend_sectors = []
    for s in trend_sorted[:trend_top_n]:
        trend_sectors.append({
            "sector_name": s["sector_name"],
            "sector_type": s.get("sector_type", "industry"),
            "trend_score": s.get("trend_score", 0) or s.get("ranking_score", 0),
            "burst_score": s.get("burst_score", 0),
            "trend_level": s.get("agent_label", ""),
            "trend_level_cn": "",
        })

    # --- Burst pool: sort by burst_score > composite_score ---
    burst_sorted = sorted(all_sectors, key=lambda x: (
        x.get("burst_score", 0),
        x.get("composite_score", 0) or x.get("opportunity_score", 0),
    ), reverse=True)

    burst_sectors = []
    for s in burst_sorted[:burst_top_n]:
        burst_sectors.append({
            "sector_name": s["sector_name"],
            "sector_type": s.get("sector_type", "industry"),
            "trend_score": s.get("trend_score", 0) or s.get("ranking_score", 0),
            "burst_score": s.get("burst_score", 0),
            "burst_level": s.get("agent_label", ""),
            "burst_level_cn": "",
        })

    return trend_sectors, burst_sectors

    # 趋势 Top N
    trend_sorted = sorted(scores, key=lambda x: x.get("trend_continuation_score", 0), reverse=True)
    trend_sectors = []
    for s in trend_sorted[:trend_top_n]:
        trend_sectors.append({
            "sector_name": s["sector_name"],
            "sector_type": s.get("sector_type", "industry"),
            "trend_score": s.get("trend_continuation_score", 0),
            "burst_score": s.get("short_term_burst_score", 0),
            "trend_level": s.get("trend_level", ""),
            "trend_level_cn": s.get("trend_level_cn", ""),
        })

    # 短线 Top N
    burst_sorted = sorted(scores, key=lambda x: x.get("short_term_burst_score", 0), reverse=True)
    burst_sectors = []
    for s in burst_sorted[:burst_top_n]:
        burst_sectors.append({
            "sector_name": s["sector_name"],
            "sector_type": s.get("sector_type", "industry"),
            "trend_score": s.get("trend_continuation_score", 0),
            "burst_score": s.get("short_term_burst_score", 0),
            "burst_level": s.get("burst_level", ""),
            "burst_level_cn": s.get("burst_level_cn", ""),
        })

    return trend_sectors, burst_sectors


def find_cross_sectors(trend_sectors: List[Dict], burst_sectors: List[Dict]) -> List[str]:
    """找出同时出现在趋势和短线 Top 列表中的板块"""
    trend_names = {s["sector_name"] for s in trend_sectors}
    burst_names = {s["sector_name"] for s in burst_sectors}
    return sorted(trend_names & burst_names)


# ============================================================
# 缓存管理
# ============================================================

def _cache_key(sector_name: str, sector_type: str, date_str: str) -> str:
    return f"{date_str}_{sector_type}_{sector_name}"


def _load_cache(key: str) -> Optional[Dict]:
    """从缓存加载板块成分股数据"""
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_cache(key: str, data: Dict):
    """保存板块成分股数据到缓存"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{key}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


# ============================================================
# 板块成分股查询
# ============================================================

def fetch_sector_constituents(sector_name: str, sector_type: str = "industry", as_of: str | None = None) -> Dict[str, Any]:
    """查询板块成分股列表。

    Fallback strategy (Phase 3 — simplified):
      1. HTTP API → trust whatever market_data_service returns (200)
      2. HTTP unavailable → local SECTOR_STOCK_MAPPING as emergency

    Args:
        sector_name: 板块名称（如 "证券"）
        sector_type: "industry" 或 "concept"
        as_of: 日期过滤 (YYYY-MM-DD)，用于 concept 本地快照

    Returns:
        {
            "status": "ok" | "degraded" | "failed",
            "sector_name": str,
            "sector_type": str,
            "stocks": [{"code": str, "name": str, "weight": float}, ...],
            "error": str | None,
            "fallback_used": bool,
            "source": "http_em" | "http_mapping" | "http_local_industry" | "http_local_concept_members" | "local_emergency_mapping" | "unavailable",
        }
    """
    # 检查缓存（当天有效）
    today = datetime.now().strftime("%Y-%m-%d")
    cache_key = _cache_key(sector_name, sector_type, today)
    cached = _load_cache(cache_key)
    if cached:
        return cached

    result = {
        "status": "ok",
        "sector_name": sector_name,
        "sector_type": sector_type,
        "stocks": [],
        "error": None,
        "fallback_used": False,
        "source": "unavailable",
    }

    # ----------------------------------------------------------------
    # Attempt 1: HTTP API (market_data_service)
    # ----------------------------------------------------------------
    http_client = _get_http_client()
    http_ok = False

    if http_client is not None:
        try:
            raw_constituents = http_client.get_board_constituents(
                sector_name, board_type=sector_type, as_of=as_of
            )
            if raw_constituents:
                stocks = []
                total_market_cap = sum(
                    float(c.get("market_cap", 0) or 0) for c in raw_constituents
                )
                for c in raw_constituents:
                    code = str(c.get("code", "")).strip()
                    name = str(c.get("name", "")).strip()
                    mv = float(c.get("market_cap", 0) or 0)
                    weight = (mv / total_market_cap) if total_market_cap > 0 else 0.0
                    stocks.append({"code": code, "name": name, "weight": weight})

                # If weights are all zero, set equal weights
                if stocks and all(s["weight"] == 0 for s in stocks):
                    equal_w = 1.0 / len(stocks)
                    for s in stocks:
                        s["weight"] = round(equal_w, 4)

                # ---- Determine source from individual stock.source fields ----
                stock_sources = {c.get("source", "em") for c in raw_constituents}
                if "local_concept_members" in stock_sources:
                    result["source"] = "http_local_concept_members"
                elif "local_industry_members" in stock_sources:
                    result["source"] = "http_local_industry"
                elif "mapping" in stock_sources:
                    result["source"] = "http_mapping"
                else:
                    result["source"] = "http_em"

                result["stocks"] = stocks
                result["error"] = None
                http_ok = True
                _save_cache(cache_key, result)
                return result
            else:
                # HTTP 200 but empty list — trust it
                result["source"] = "http_em"
                result["stocks"] = []
                result["error"] = None
                http_ok = True
                _save_cache(cache_key, result)
                return result

        except (ConnectionError, TimeoutError) as e:
            logger.info(
                "HTTP constituents unavailable for %s (%s), trying local fallback",
                sector_name, e,
            )
        except (ValueError, RuntimeError) as e:
            logger.warning(
                "HTTP constituents error for %s: %s, trying local fallback",
                sector_name, e,
            )
        except Exception:
            logger.warning(
                "HTTP constituents unexpected error for %s", sector_name, exc_info=True
            )

    # ----------------------------------------------------------------
    # Attempt 2: local SECTOR_STOCK_MAPPING (emergency fallback)
    #   Only reached when HTTP API is unreachable (connection refused,
    #   timeout, 5xx).  DO NOT use when HTTP returned 200 with mapping
    #   data — market_data_service already did its own fallback.
    # ----------------------------------------------------------------
    if not http_ok and sector_name in SECTOR_STOCK_MAPPING:
        mapping = SECTOR_STOCK_MAPPING[sector_name]
        equal_w = 1.0 / len(mapping) if mapping else 0
        result["stocks"] = [
            {"code": code, "name": name, "weight": round(equal_w, 4)}
            for code, name in mapping
        ]
        result["status"] = "degraded"
        result["fallback_used"] = True
        result["source"] = "local_emergency_mapping"
        result["error"] = (
            f"HTTP API 不可用，使用本地 emergency 映射（{len(mapping)}只）"
        )
        _save_cache(cache_key, result)
        return result

    # No data from any source
    if not http_ok:
        result["status"] = "degraded"
        result["error"] = "HTTP API 不可用且无本地映射"
        result["source"] = "unavailable"

    _save_cache(cache_key, result)
    return result


# ============================================================
# 腾讯行情 API
# ============================================================

def _parse_tencent_quote(raw: str) -> Optional[Dict]:
    """
    解析腾讯行情 API 返回数据。

    格式: v_sz600030="1~中信证券~600030~21.50~21.30~..."
    字段: 0=未知 1=名称 2=代码 3=现价 4=昨收 5=今开
          6=最高 7=最低 8=买入 9=卖出 30=成交额 31=成交量
          32=外盘 33=内盘 37=涨跌幅 38=振幅 39=流通市值 40=总市值
          44=市盈率(动) 46=市净率
    """
    match = re.search(r'"(.+)"', raw)
    if not match:
        return None
    parts = match.group(1).split("~")
    if len(parts) < 47:
        return None
    try:
        price = float(parts[3]) if parts[3] else 0
        prev_close = float(parts[4]) if parts[4] else 0
        change_pct = float(parts[32]) if parts[32] else 0
        turnover = float(parts[38]) if parts[38] else 0
        total_mv = float(parts[44]) if parts[44] else 0  # 总市值（亿元）
        pe = float(parts[39]) if parts[39] else 0
        pb = float(parts[46]) if parts[46] else 0
        volume = float(parts[36]) if parts[36] else 0  # 成交量（手）

        return {
            "name": parts[1],
            "code": parts[2],
            "price": price,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "turnover_pct": turnover,
            "total_mv": total_mv,
            "pe": pe,
            "pb": pb,
            "volume": volume,
        }
    except (ValueError, IndexError):
        return None


def fetch_tencent_quotes(codes: List[str]) -> Dict[str, Dict]:
    """
    批量获取腾讯实时行情。

    Args:
        codes: 股票代码列表（6位纯数字）

    Returns:
        {code: {name, price, change_pct, ...}, ...}
    """
    if not codes:
        return {}

    import requests

    results = {}

    # 腾讯 API 一次最多请求约 80 只
    batch_size = 60
    for i in range(0, len(codes), batch_size):
        batch = codes[i : i + batch_size]
        # 构造请求参数: v_sz600030,v_sz000001,...
        symbols = ",".join(f"{'sh' if c.startswith('6') else 'sz'}{c}" for c in batch)
        url = f"http://qt.gtimg.cn/q={symbols}"

        try:
            resp = requests.get(url, timeout=10)
            resp.encoding = "gbk"
            for line in resp.text.strip().split("\n"):
                line = line.strip()
                if not line or "=" not in line:
                    continue
                quote = _parse_tencent_quote(line)
                if quote and quote["code"]:
                    results[quote["code"]] = quote
        except Exception:
            pass  # 单批次失败不影响其他批次

        if i + batch_size < len(codes):
            time.sleep(0.2)

    return results


# ============================================================
# 资金流数据
# ============================================================

def fetch_sector_fund_flow(sector_name: str) -> Dict[str, Any]:
    """
    获取板块主力资金流向。

    Returns:
        {
            "status": "ok" | "degraded" | "failed",
            "net_flow": float | None,   # 净流入（正=流入，负=流出）
            "direction": "inflow" | "outflow" | "neutral",
            "error": str | None,
        }
    """
    result = {
        "status": "ok",
        "net_flow": None,
        "direction": "neutral",
        "error": None,
    }

    # 尝试东方财富板块资金流
    try:
        import akshare as ak
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
        if df is not None and not df.empty:
            row = df[df["名称"] == sector_name]
            if not row.empty:
                net = float(row.iloc[0].get("主力净流入-净额", 0))
                result["net_flow"] = net
                result["direction"] = "inflow" if net > 0 else "outflow" if net < 0 else "neutral"
                return result
    except Exception as e:
        result["error"] = f"东方财富板块资金流失败: {str(e)[:100]}"

    # 降级：尝试新浪财经
    try:
        import requests
        # 新浪行业资金流接口
        url = f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_bkzj_bk?page=1&num=20&sort=netamount&asc=0&fenlei=1"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                if item.get("name") == sector_name:
                    net = float(item.get("netamount", 0))
                    result["net_flow"] = net
                    result["direction"] = "inflow" if net > 0 else "outflow" if net < 0 else "neutral"
                    result["status"] = "ok"
                    result["error"] = None
                    return result
    except Exception:
        pass

    # 降级：中性值
    result["status"] = "degraded"
    result["direction"] = "neutral"
    if not result["error"]:
        result["error"] = "所有资金流 API 不可用，使用中性值"
    return result


def fetch_individual_fund_flow(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    批量获取个股主力资金流向。

    Returns:
        {code: {"net_flow": float, "direction": str}, ...}
    """
    results = {}

    # 尝试东方财富个股资金流排行
    try:
        import akshare as ak
        df = ak.stock_individual_fund_flow_rank(indicator="今日")
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                code = str(row.get("代码", "")).strip()
                if code in codes:
                    val = row.get("主力净流入-净额") or 0
                    net = float(val)
                    results[code] = {
                        "net_flow": net,
                        "direction": "inflow" if net > 0 else "outflow" if net < 0 else "neutral",
                    }
            if results:
                return results
    except Exception:
        pass

    # 降级：新浪个股资金流
    try:
        import requests
        for code in codes[:30]:  # 限制请求数
            prefix = "sh" if code.startswith("6") else "sz"
            url = f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_qsfx_zjlrqs?page=1&num=1&sort=opendate&asc=0&datefrom=&dateto=&symbol={prefix}{code}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    net = float(data[0].get("netamount", 0))
                    results[code] = {
                        "net_flow": net,
                        "direction": "inflow" if net > 0 else "outflow" if net < 0 else "neutral",
                    }
            time.sleep(0.1)
    except Exception:
        pass

    return results


# ============================================================
# 关联度计算
# ============================================================

def _normalize_weights(stocks: List[Dict]) -> List[Dict]:
    """将成分股权重归一化到 0~1"""
    weights = [s.get("weight", 0) for s in stocks]
    max_w = max(weights) if weights else 1
    if max_w <= 0:
        return stocks
    for s in stocks:
        s["weight_normalized"] = s.get("weight", 0) / max_w
    return stocks


def _compute_rank_scores(stocks: List[Dict]) -> List[Dict]:
    """
    计算涨幅排名分。

    排名百分位归一化到 0~1：
      排名前 10% → 1.0
      排名后 10% → 0.0
    """
    n = len(stocks)
    if n == 0:
        return stocks

    # 按涨跌幅降序排名
    sorted_stocks = sorted(stocks, key=lambda x: x.get("change_pct", 0), reverse=True)
    for rank_idx, s in enumerate(sorted_stocks):
        percentile = rank_idx / max(n - 1, 1)  # 0 = 最高, 1 = 最低
        # 映射到 0~1（排名越高分越高）
        rank_score = 1.0 - percentile
        s["rank_score"] = round(rank_score, 4)
        s["rank_in_sector"] = rank_idx + 1

    return stocks


def _compute_flow_alignment(
    stock_direction: str,
    sector_direction: str,
) -> float:
    """
    计算资金流对齐系数。

    Returns:
        归一化到 0~1 的系数（系数 / 1.2）
    """
    if sector_direction == "neutral" or stock_direction == "neutral":
        # 无法判断方向时，使用中性值
        return 1.0 / FLOW_BOTH_INFLOW  # 1.0/1.2 ≈ 0.833

    if sector_direction == "inflow" and stock_direction == "inflow":
        return FLOW_BOTH_INFLOW / FLOW_BOTH_INFLOW  # 1.0
    elif sector_direction == "inflow" and stock_direction == "outflow":
        return FLOW_INDIVIDUAL背离 / FLOW_BOTH_INFLOW  # 0.25
    elif sector_direction == "outflow" and stock_direction == "inflow":
        return FLOW_INDIVIDUAL逆势 / FLOW_BOTH_INFLOW  # 0.417
    elif sector_direction == "outflow" and stock_direction == "outflow":
        return FLOW_BOTH_OUTFLOW / FLOW_BOTH_INFLOW  # 0.667
    else:
        return 1.0 / FLOW_BOTH_INFLOW


def compute_relevance_scores(
    stocks: List[Dict],
    sector_fund_flow: Dict[str, Any],
    min_relevance: float = DEFAULT_MIN_RELEVANCE,
) -> List[Dict]:
    """
    计算每只个股的板块关联度。

    Args:
        stocks: 成分股列表（需包含 weight, change_pct, individual_flow_direction）
        sector_fund_flow: 板块资金流 {"direction": "inflow"/"outflow"/"neutral"}
        min_relevance: 最小关联度阈值

    Returns:
        过滤后的高关联度个股列表
    """
    sector_direction = sector_fund_flow.get("direction", "neutral")

    # 归一化权重
    stocks = _normalize_weights(stocks)

    # 计算涨幅排名分
    stocks = _compute_rank_scores(stocks)

    # 计算每只个股的关联度
    for s in stocks:
        weight_score = s.get("weight_normalized", 0.5)
        rank_score = s.get("rank_score", 0.5)
        stock_direction = s.get("individual_flow_direction", "neutral")
        flow_alignment = _compute_flow_alignment(stock_direction, sector_direction)

        relevance = W_WEIGHT * weight_score + W_RANK * rank_score + W_FLOW * flow_alignment
        relevance = round(min(relevance, 1.0), 4)

        s["relevance_score"] = relevance
        s["relevance_breakdown"] = {
            "weight_score": round(weight_score, 4),
            "rank_score": round(rank_score, 4),
            "flow_alignment": round(flow_alignment, 4),
        }

    # 过滤高关联度
    filtered = [s for s in stocks if s["relevance_score"] >= min_relevance]
    # 按关联度降序
    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)

    return filtered


# ============================================================
# 主流程
# ============================================================

def run_bridge(
    as_of_date: Optional[str] = None,
    trend_top_n: int = DEFAULT_TREND_TOP_N,
    burst_top_n: int = DEFAULT_BURST_TOP_N,
    min_relevance: float = DEFAULT_MIN_RELEVANCE,
) -> Dict[str, Any]:
    """
    执行完整的板块-个股桥接流程。

    Args:
        as_of_date: 指定日期，None 则自动查找最新
        trend_top_n: 趋势板块 Top N
        burst_top_n: 短线板块 Top N
        min_relevance: 最小关联度阈值

    Returns:
        完整的桥接结果，包含 trend_sectors / burst_sectors / cross_sectors
    """
    output = {
        "as_of_date": None,
        "status": "ok",
        "trend_sectors": [],
        "burst_sectors": [],
        "cross_sectors": [],
        "api_status": {
            "http_constituents": "ok",
            "tencent_quotes": "ok",
            "fund_flow": "ok",
        },
        "warnings": [],
        "generated_at": datetime.now().isoformat(),
    }

    # Step 1: 读取板块评分报告 (Phase 22: stable inputs first)
    print("  [1/5] 读取板块评分报告...")
    actual_date, report_path = find_latest_report(as_of_date)
    if not report_path:
        output["status"] = "failed"
        output["warnings"].append(f"找不到板块评分报告 (请求日期: {as_of_date})")
        return output

    if actual_date != as_of_date:
        output["warnings"].append(f"指定日期 {as_of_date} 无报告，使用 {actual_date}")

    output["as_of_date"] = actual_date

    # Phase 22: try stable inputs first
    stable = load_stable_sector_inputs(actual_date)
    if stable["available"]:
        trend_sectors_meta, burst_sectors_meta = extract_top_sectors_from_stable(stable, trend_top_n, burst_top_n)
        output["sector_input_source"] = stable["source"]
        print(f"    ✅ 使用稳定产线数据: {stable['source']} "
              f"(行业{len(stable['industries'])}个, 概念{len(stable['concepts'])}个)")
    else:
        data = load_sector_scores(report_path)
        trend_sectors_meta, burst_sectors_meta = extract_top_sectors(data, trend_top_n, burst_top_n)
        output["sector_input_source"] = "legacy_sector_scores"
        print(f"    ⚠️ 使用旧评分数据 (无稳定产线数据)")

    cross_sector_names = find_cross_sectors(trend_sectors_meta, burst_sectors_meta)
    output["cross_sectors"] = cross_sector_names

    all_sectors = {s["sector_name"]: s for s in trend_sectors_meta}
    all_sectors.update({s["sector_name"]: s for s in burst_sectors_meta})

    print(f"    趋势 Top{trend_top_n}: {[s['sector_name'] for s in trend_sectors_meta]}")
    print(f"    短线 Top{burst_top_n}: {[s['sector_name'] for s in burst_sectors_meta]}")
    if cross_sector_names:
        print(f"    重叠板块: {cross_sector_names}")

    # Step 2: 查询板块成分股
    print("  [2/5] 查询板块成分股...")
    sector_stocks = {}  # {sector_name: {status, stocks, ...}}
    source_counter = {"http_em": 0, "http_stale": 0, "http_mapping": 0,
                      "http_local_industry": 0, "http_local_concept_members": 0,
                      "local_emergency_mapping": 0, "unavailable": 0}

    for name in all_sectors:
        meta = all_sectors[name]
        result = fetch_sector_constituents(name, meta.get("sector_type", "industry"), as_of=output.get("as_of_date"))
        sector_stocks[name] = result
        src = result.get("source", "unavailable")
        if src in source_counter:
            source_counter[src] += 1
        else:
            source_counter[src] = 1
        status_emoji = "✅" if result["status"] == "ok" else "⚠️" if result["status"] == "degraded" else "❌"
        print(f"    {status_emoji} {name}: {len(result['stocks'])} 只成分股 [{src}]" +
              (f" ({result['error']})" if result["error"] else ""))
        if "local_emergency" in result.get("source", ""):
            output["api_status"]["http_constituents"] = "degraded"

    output["constituent_source_summary"] = source_counter

    # Step 3: 获取行情数据
    print("  [3/5] 获取成分股行情...")
    all_codes = set()
    for name, sec_data in sector_stocks.items():
        for s in sec_data.get("stocks", []):
            all_codes.add(s["code"])

    quotes = fetch_tencent_quotes(list(all_codes))
    if not quotes:
        output["api_status"]["tencent_quotes"] = "failed"
        output["warnings"].append("腾讯行情 API 无数据")
    else:
        print(f"    ✅ 获取 {len(quotes)} 只股票行情")

    # Step 4: 获取资金流数据
    print("  [4/5] 获取资金流数据...")
    sector_flows = {}
    for name in all_sectors:
        flow = fetch_sector_fund_flow(name)
        sector_flows[name] = flow
        status_emoji = "✅" if flow["status"] == "ok" else "⚠️"
        print(f"    {status_emoji} {name}: {flow['direction']}" +
              (f" ({flow['error']})" if flow.get("error") else ""))
        if flow["status"] != "ok":
            output["api_status"]["fund_flow"] = "degraded"

    # 获取个股资金流
    individual_flows = fetch_individual_fund_flow(list(all_codes))
    if individual_flows:
        print(f"    ✅ 获取 {len(individual_flows)} 只个股资金流")
    else:
        print("    ⚠️ 个股资金流不可用，使用中性值")
        output["api_status"]["fund_flow"] = "degraded"

    # Step 5: 计算关联度
    print("  [5/5] 计算板块关联度...")

    def _build_sector_stocks(sector_meta_list: List[Dict], label: str) -> List[Dict]:
        sector_results = []
        for meta in sector_meta_list:
            name = meta["sector_name"]
            sec_data = sector_stocks.get(name, {})
            stocks_raw = sec_data.get("stocks", [])

            # 合并行情和资金流
            enriched = []
            for s in stocks_raw:
                code = s["code"]
                q = quotes.get(code, {})
                flow = individual_flows.get(code, {})

                enriched.append({
                    "code": code,
                    "name": s.get("name") or q.get("name", ""),
                    "sector_weight": s.get("weight", 0),
                    "change_pct": q.get("change_pct", 0),
                    "price": q.get("price", 0),
                    "total_mv": q.get("total_mv", 0),
                    "pe": q.get("pe", 0),
                    "pb": q.get("pb", 0),
                    "individual_fund_flow": flow.get("net_flow", 0),
                    "individual_flow_direction": flow.get("direction", "neutral"),
                })

            # 计算关联度
            flow_data = sector_flows.get(name, {"direction": "neutral"})
            filtered = compute_relevance_scores(enriched, flow_data, min_relevance)

            sector_entry = {
                "sector_name": name,
                "sector_type": meta.get("sector_type", "industry"),
                "trend_score": meta.get("trend_score", 0),
                "burst_score": meta.get("burst_score", 0),
                "fund_flow_direction": flow_data.get("direction", "neutral"),
                "total_constituents": len(stocks_raw),
                "high_relevance_count": len(filtered),
                "stocks": filtered,
            }
            sector_results.append(sector_entry)

            status_emoji = "✅" if filtered else "⚠️"
            print(f"    {status_emoji} [{label}] {name}: {len(filtered)}/{len(stocks_raw)} 只高关联度")

        return sector_results

    output["trend_sectors"] = _build_sector_stocks(trend_sectors_meta, "趋势")
    output["burst_sectors"] = _build_sector_stocks(burst_sectors_meta, "短线")

    # 汇总
    total_trend_stocks = sum(len(s["stocks"]) for s in output["trend_sectors"])
    total_burst_stocks = sum(len(s["stocks"]) for s in output["burst_sectors"])
    print(f"\n  ✅ 桥接完成: 趋势 {total_trend_stocks} 只 / 短线 {total_burst_stocks} 只高关联度个股")

    return output


# ============================================================
# CLI 入口
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="板块-个股桥接层")
    parser.add_argument("--as-of", type=str, default=None, help="分析日期")
    parser.add_argument("--trend-top-n", type=int, default=DEFAULT_TREND_TOP_N, help="趋势板块 Top N")
    parser.add_argument("--burst-top-n", type=int, default=DEFAULT_BURST_TOP_N, help="短线板块 Top N")
    parser.add_argument("--min-relevance", type=float, default=DEFAULT_MIN_RELEVANCE, help="最小关联度")
    parser.add_argument("--output", type=str, default=None, help="输出目录")
    args = parser.parse_args()

    print(f"{'='*70}")
    print(f"板块-个股桥接层 (Sector-Stock Bridge)")
    print(f"{'='*70}")

    result = run_bridge(
        as_of_date=args.as_of,
        trend_top_n=args.trend_top_n,
        burst_top_n=args.burst_top_n,
        min_relevance=args.min_relevance,
    )

    # 输出 JSON
    output_dir = Path(args.output) if args.output else PROJECT_ROOT / "reports" / "bridge" / result.get("as_of_date", "unknown")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "bridge_result.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n📁 桥接结果已保存: {output_file}")

    # 摘要
    print(f"\n{'='*70}")
    print(f"摘要")
    print(f"{'='*70}")
    print(f"  日期: {result['as_of_date']}")
    print(f"  状态: {result['status']}")
    print(f"  API 状态: {result['api_status']}")
    src_summary = result.get("constituent_source_summary", {})
    if src_summary:
        print(f"  成分股来源: {json.dumps(src_summary, ensure_ascii=False)}")
    if result["warnings"]:
        print(f"  警告: {result['warnings']}")

    for label, sectors in [("趋势", result["trend_sectors"]), ("短线", result["burst_sectors"])]:
        print(f"\n  [{label}板块]")
        for sec in sectors:
            stocks_str = ", ".join(f"{s['code']}({s['name']})" for s in sec["stocks"][:5])
            print(f"    {sec['sector_name']}: {sec['high_relevance_count']}只 → {stocks_str}")


if __name__ == "__main__":
    main()
