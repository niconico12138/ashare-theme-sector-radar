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

import hashlib
import json
import logging
import math
import os
import re
import stat
import sys
import time
import io

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from theme_sector_radar.reporting.sector_score_contract import (
    validate_sector_score_payload,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    loads_strict_json,
)
from theme_sector_radar.scoring.stock_sector_linkage import (
    build_constituent_linkage_input_contract,
    effective_legacy_linkage_policy_contract,
    legacy_linkage_policy_contract,
)

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
REPORT_ROOT_ENV = "THEME_SECTOR_RADAR_REPORT_ROOT"
SCORE_PAYLOAD_STDIN_ENV = "THEME_SECTOR_RADAR_SCORE_PAYLOAD_STDIN"
SCORE_PAYLOAD_AS_OF_ENV = "THEME_SECTOR_RADAR_SCORE_PAYLOAD_AS_OF"
_REPORT_ROOT_OVERRIDE = (
    os.environ.get(REPORT_ROOT_ENV) if REPORT_ROOT_ENV in os.environ else None
)
REPORT_ROOT = (
    Path(_REPORT_ROOT_OVERRIDE).expanduser().resolve()
    if _REPORT_ROOT_OVERRIDE is not None and _REPORT_ROOT_OVERRIDE.strip()
    else (
        PROJECT_ROOT / "reports"
        if _REPORT_ROOT_OVERRIDE is None
        else PROJECT_ROOT / ".invalid_explicit_report_root"
    )
)
SCORES_DIR = REPORT_ROOT / "sector_scores"
CACHE_DIR = (
    REPORT_ROOT / ".cache" / "sector_stocks"
    if _REPORT_ROOT_OVERRIDE is not None
    else PROJECT_ROOT / "data_cache" / "sector_stocks"
)

# Phase 22: stable data directories
STABLE_RESEARCH_DIR = REPORT_ROOT / "full90" / "sector_research"
STABLE_CONCEPT_DIR = REPORT_ROOT / "full_concept" / "unified_rank"
DIRECTION_SHADOW_DIR = REPORT_ROOT / "paper_shadow"

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
# 新浪财经板块代码映射（东方财富被封锁时的降级方案）
# ============================================================

_SINA_SECTOR_MAP = {
    "半导体": "new_dzqj", "电子化学品": "new_dzqj", "光学光电子": "new_dzqj",
    "电子": "new_dzqj", "元件": "new_dzqj", "消费电子": "new_dzqj",
    "游戏": "new_cmyl", "传媒": "new_cmyl", "影视院线": "new_cmyl",
    "文化传媒": "new_cmyl",
    "人工智能": "new_dzxx", "计算机": "new_dzxx", "通信": "new_dzxx",
    "通信设备": "new_dzxx", "软件开发": "new_dzxx",
    "证券": "new_jrhy", "银行": "new_jrhy", "保险": "new_jrhy",
    "房地产": "new_fdc", "钢铁": "new_gthy", "有色金属": "new_ysjs",
    "煤炭": "new_mthy", "石油石化": "new_syhy",
    "电力设备": "new_dlhy", "电力": "new_dlhy",
    "机械设备": "new_jxhy", "工程机械": "new_jxhy", "自动化设备": "new_jxhy",
    "专用设备": "new_jxhy", "通用设备": "new_jxhy",
    "食品饮料": "new_sphy", "白酒": "new_ljhy", "酿酒行业": "new_ljhy",
    "医药生物": "new_swzz", "中药": "new_swzz", "医疗器械": "new_ylqx",
    "化学制药": "new_swzz", "生物制品": "new_swzz", "医疗服务": "new_ylqx",
    "美容护理": "new_ylqx", "护理": "new_ylqx",
    "汽车制造": "new_qczz", "汽车服务及其他": "new_qczz",
    "汽车整车": "new_qczz", "汽车零部件": "new_qczz",
    "纺织服饰": "new_fzhy", "家用电器": "new_jdhy", "黑色家电": "new_jdhy",
    "白色家电": "new_jdhy", "小家电": "new_jdhy",
    "塑料制品": "new_slzp", "包装印刷": "new_ysbz", "造纸行业": "new_zzhy",
    "造纸": "new_zzhy",
    "建筑建材": "new_jzjc", "环保行业": "new_hbhy", "环境治理": "new_hbhy",
    "化工行业": "new_hghy", "化肥": "new_nyhf",
    "交通运输": "new_jtys", "机场航运": "new_jtys", "物流": "new_jtys",
    "航空运输": "new_jtys", "航运港口": "new_jtys",
    "农林牧渔": "new_nlmy", "养殖业": "new_nlmy",
    "商业百货": "new_sybh", "互联网电商": "new_sybh",
    "煤炭行业": "new_mthy", "光伏设备": "new_fdsb", "光伏": "new_fdsb",
    "电池": "new_fdsb", "其他电源设备": "new_fdsb",
    "金属新材料": "new_ysjs", "能源金属": "new_ysjs", "小金属": "new_ysjs",
    "纺织机械": "new_fzjx", "燃气": "new_gsgq", "供水供气": "new_gsgq",
    "多元金融": "new_jrhy", "公路铁路运输": "new_glql",
    "船舶制造": "new_cbzz", "飞机制造": "new_fjzz", "摩托车": "new_mtc",
    "仪器仪表": "new_yqyb", "家具行业": "new_jjhy", "家居用品": "new_jjhy",
    "开发区": "new_kfq", "次新股": "new_stock", "综合行业": "new_zhhy",
    "陶瓷行业": "new_tchy", "玻璃行业": "new_blhy",
}


def _fetch_sina_constituents(sector_name: str) -> List[Dict]:
    """通过新浪财经获取板块成分股（东方财富不可用时的替代方案）"""
    sina_code = _SINA_SECTOR_MAP.get(sector_name)
    if not sina_code:
        return []

    import requests
    stocks = []
    page = 1
    while page <= 10:
        url = (
            f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            f"Market_Center.getHQNodeData?page={page}&num=80&sort=symbol&asc=1"
            f"&node={sina_code}&symbol=&_s_r_a=page"
        )
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            data = json.loads(resp.text)
            if not data:
                break
            for d in data:
                code = d.get("code", "")
                name = d.get("name", "")
                mv = d.get("mktcap", 0) or 0
                if code and name and not name.startswith("*ST"):
                    stocks.append({"code": code, "name": name, "mktcap": mv})
            if len(data) < 80:
                break
            page += 1
        except Exception:
            break

    return stocks


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
    if as_of_date is not None and not _is_valid_iso_date(as_of_date):
        return None, None

    if _REPORT_ROOT_OVERRIDE is not None:
        if not _REPORT_ROOT_OVERRIDE.strip():
            return None, None
        if as_of_date is None:
            return None, None
        try:
            report_root = Path(_REPORT_ROOT_OVERRIDE).expanduser().resolve(strict=True)
            if not report_root.is_dir():
                return None, None
            expected_score_root = report_root / "sector_scores"
            score_root = expected_score_root.resolve(strict=True)
            if score_root != expected_score_root:
                return None, None
            report_path = (score_root / as_of_date / "sector_scores.json").resolve()
            report_path.relative_to(score_root)
        except (OSError, RuntimeError, ValueError):
            return None, None

        if report_path.is_file():
            return as_of_date, report_path
        return None, None

    candidates = _default_score_report_candidates(as_of_date)
    if candidates:
        return candidates[0]

    return None, None


def _default_score_report_candidates(
    as_of_date: Optional[str],
) -> List[Tuple[str, Path]]:
    """Return exact-only or descending historical candidates for default roots."""
    if as_of_date is not None and not _is_valid_iso_date(as_of_date):
        return []
    if as_of_date:
        exact_path = SCORES_DIR / as_of_date / "sector_scores.json"
        if exact_path.exists():
            return [(as_of_date, exact_path)]
        print(f"  ⚠️ 指定日期 {as_of_date} 无报告，尝试 fallback...")
    if not SCORES_DIR.exists():
        return []
    candidates = []
    for date_dir in sorted(
        (
            path
            for path in SCORES_DIR.iterdir()
            if path.is_dir()
            and _is_valid_iso_date(path.name)
            and (as_of_date is None or path.name <= as_of_date)
        ),
        reverse=True,
    ):
        report_path = date_dir / "sector_scores.json"
        if report_path.exists():
            candidates.append((date_dir.name, report_path))
    return candidates


def load_sector_scores(report_path: Path) -> Dict[str, Any]:
    """加载板块评分报告，返回原始 JSON 数据"""
    if _REPORT_ROOT_OVERRIDE is not None:
        text = _read_override_confined_text(report_path, encoding="utf-8-sig")
        if text is None:
            raise OSError(f"显式报告路径不安全或不可读: {report_path}")
        data = loads_strict_json(text, context=str(report_path))
        if not isinstance(data, dict):
            raise ValueError("sector_scores payload must be an object")
        return data
    data = loads_strict_json(
        report_path.read_text(encoding="utf-8-sig"), context=str(report_path)
    )
    if not isinstance(data, dict):
        raise ValueError("sector_scores payload must be an object")
    return data


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

def _override_confinement_root(confined_root: Optional[Path]) -> Tuple[Path, Path]:
    report_root = Path(_REPORT_ROOT_OVERRIDE).expanduser().resolve(strict=True)
    if confined_root is None:
        return report_root, report_root
    expected_root = Path(os.path.abspath(os.path.expanduser(str(confined_root))))
    expected_root.relative_to(report_root)
    return report_root, expected_root


def _resolve_override_confined_path(
    path: Path,
    *,
    confined_root: Optional[Path] = None,
) -> Optional[Path]:
    """Resolve a path only when it remains inside its explicit input subtree."""
    if _REPORT_ROOT_OVERRIDE is None:
        return path
    if not _REPORT_ROOT_OVERRIDE.strip():
        return None
    try:
        _report_root, expected_root = _override_confinement_root(confined_root)
        resolved = path.expanduser().resolve()
        resolved.relative_to(expected_root)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved


def _read_override_confined_text(
    path: Path,
    *,
    encoding: str,
    confined_root: Optional[Path] = None,
) -> Optional[str]:
    """Open first, then prove the opened file still belongs to the explicit root."""
    if _REPORT_ROOT_OVERRIDE is None:
        try:
            return path.read_text(encoding=encoding)
        except (OSError, UnicodeError):
            return None

    try:
        expected_report_root, expected_root = _override_confinement_root(
            confined_root
        )
        resolved = _resolve_override_confined_path(
            path, confined_root=confined_root
        )
        if resolved is None:
            return None
        fd = os.open(
            resolved,
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NONBLOCK", 0),
        )
    except (OSError, RuntimeError, ValueError):
        return None

    try:
        current_root = Path(_REPORT_ROOT_OVERRIDE).expanduser().resolve(strict=True)
        current_path = path.expanduser().resolve(strict=True)
        if current_root != expected_report_root or current_path != resolved:
            return None
        current_path.relative_to(expected_root)
        opened_stat = os.fstat(fd)
        if not stat.S_ISREG(opened_stat.st_mode):
            return None
        if not os.path.samestat(opened_stat, os.stat(current_path)):
            return None
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read().decode(encoding)
    except (OSError, RuntimeError, UnicodeError, ValueError):
        return None
    finally:
        os.close(fd)


def validate_explicit_score_report(
    as_of_date: Optional[str],
) -> Tuple[bool, Optional[Tuple[str, Path, Dict[str, Any]]], Optional[str]]:
    """Load and validate the resolved score report before any network work."""
    if os.environ.get(SCORE_PAYLOAD_STDIN_ENV) == "1":
        try:
            if (
                as_of_date is None
                or re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of_date) is None
                or datetime.strptime(as_of_date, "%Y-%m-%d").strftime("%Y-%m-%d")
                != as_of_date
            ):
                raise ValueError(f"无效分析日期: {as_of_date}")
            payload_date = os.environ.get(SCORE_PAYLOAD_AS_OF_ENV) or as_of_date
            if (
                re.fullmatch(r"\d{4}-\d{2}-\d{2}", payload_date) is None
                or datetime.strptime(payload_date, "%Y-%m-%d").strftime("%Y-%m-%d")
                != payload_date
                or payload_date > as_of_date
            ):
                raise ValueError(f"无效父进程评分日期: {payload_date}")
            if _REPORT_ROOT_OVERRIDE is None:
                score_root = Path(SCORES_DIR).expanduser().resolve()
            else:
                if not _REPORT_ROOT_OVERRIDE.strip():
                    raise OSError("显式报告根不能为空")
                report_root = Path(_REPORT_ROOT_OVERRIDE).expanduser().resolve(strict=True)
                if not report_root.is_dir():
                    raise OSError(f"显式报告根不存在: {report_root}")
                expected_score_root = report_root / "sector_scores"
                score_root = expected_score_root.resolve(strict=True)
                if score_root != expected_score_root:
                    raise OSError("显式报告根的 sector_scores 不是精确子目录")
            report_path = score_root / payload_date / "sector_scores.json"
            report_path.relative_to(score_root)
            data = loads_strict_json(
                sys.stdin.read(), context="parent-validated sector_scores stdin"
            )
            validate_sector_score_payload(data, expected_as_of=payload_date)
        except (
            OSError,
            RuntimeError,
            UnicodeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            return False, None, f"父进程传递的 sector_scores JSON 无效: {exc}"
        return True, (payload_date, report_path, data), None

    if _REPORT_ROOT_OVERRIDE is None:
        candidates = _default_score_report_candidates(as_of_date)
        if not candidates:
            return False, None, f"找不到板块评分报告 (请求日期: {as_of_date})"
        last_error: Exception | None = None
        for actual_date, report_path in candidates:
            try:
                data = load_sector_scores(report_path)
                validate_sector_score_payload(data, expected_as_of=actual_date)
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                continue
            return True, (actual_date, report_path, data), None
        return False, None, f"sector_scores JSON 无效: {last_error}"
    if not _REPORT_ROOT_OVERRIDE.strip():
        return False, None, "显式报告根不能为空"

    actual_date, report_path = find_latest_report(as_of_date)
    if actual_date is None or report_path is None:
        return False, None, f"找不到显式报告根中的板块评分报告 (请求日期: {as_of_date})"
    try:
        data = load_sector_scores(report_path)
        validate_sector_score_payload(data, expected_as_of=actual_date)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        return False, None, f"显式报告根的 sector_scores JSON 无效: {exc}"
    return True, (actual_date, report_path, data), None


def _stable_text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


def _is_valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%d") == value


def _stable_finite_number(
    value: Any,
    field: str,
    *,
    allow_text: bool = False,
) -> float:
    if value is None or value == "":
        value = 0
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    if isinstance(value, str):
        if not allow_text:
            raise ValueError(f"{field} must be a finite number")
        value = value.strip() or "0"
    elif not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def _stable_required_finite_number(
    value: Any,
    field: str,
    *,
    allow_text: bool = False,
) -> float:
    if value is None or value == "":
        raise ValueError(f"{field} must be a finite number")
    return _stable_finite_number(value, field, allow_text=allow_text)


def _stable_nonnegative_int(value: Any, field: str) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a nonnegative integer")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and re.fullmatch(r"[+]?[0-9]+", value.strip()):
        number = int(value.strip())
    else:
        raise ValueError(f"{field} must be a nonnegative integer")
    if number < 0:
        raise ValueError(f"{field} must be a nonnegative integer")
    return number


def load_stable_sector_inputs(
    as_of_date: str,
    score_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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
    industry_path = _resolve_override_confined_path(
        STABLE_RESEARCH_DIR / as_of_date / "sector_research.json",
        confined_root=STABLE_RESEARCH_DIR,
    )
    # Also load trend/burst scores and level labels from sector_scores.json for industries
    _industry_score_map = {}
    _scores_path = _resolve_override_confined_path(
        SCORES_DIR / as_of_date / "sector_scores.json",
        confined_root=SCORES_DIR,
    )
    if score_data is not None:
        _scores_data = score_data
        for _s in _scores_data.get("scores", []):
            if _s.get("sector_type") == "industry":
                _industry_score_map[_s["sector_name"]] = {
                    "trend_score": _stable_finite_number(
                        _s.get("trend_continuation_score", 0),
                        "trend_continuation_score",
                    ),
                    "burst_score": _stable_finite_number(
                        _s.get("short_term_burst_score", 0),
                        "short_term_burst_score",
                    ),
                    "trend_level": _stable_text(
                        _s.get("trend_level", ""), "trend_level", allow_empty=True
                    ),
                    "trend_level_cn": _stable_text(
                        _s.get("trend_level_cn", ""),
                        "trend_level_cn",
                        allow_empty=True,
                    ),
                    "burst_level": _stable_text(
                        _s.get("burst_level", ""), "burst_level", allow_empty=True
                    ),
                    "burst_level_cn": _stable_text(
                        _s.get("burst_level_cn", ""),
                        "burst_level_cn",
                        allow_empty=True,
                    ),
                }
    elif _scores_path is not None:
        try:
            _scores_text = _read_override_confined_text(
                _scores_path, encoding="utf-8-sig", confined_root=SCORES_DIR
            )
            if _scores_text is None:
                raise OSError("score input escaped explicit report root")
            _scores_data = loads_strict_json(
                _scores_text, context=str(_scores_path)
            )
            for _s in _scores_data.get("scores", []):
                if _s.get("sector_type") == "industry":
                    _industry_score_map[_s["sector_name"]] = {
                        "trend_score": _s.get("trend_continuation_score", 0),
                        "burst_score": _s.get("short_term_burst_score", 0),
                        "trend_level": _s.get("trend_level", ""),
                        "trend_level_cn": _s.get("trend_level_cn", ""),
                        "burst_level": _s.get("burst_level", ""),
                        "burst_level_cn": _s.get("burst_level_cn", ""),
                    }
        except Exception:
            pass

    if industry_path is not None:
        try:
            industry_text = _read_override_confined_text(
                industry_path,
                encoding="utf-8-sig",
                confined_root=STABLE_RESEARCH_DIR,
            )
            if industry_text is None:
                raise OSError("industry input escaped explicit report root")
            data = loads_strict_json(industry_text, context=str(industry_path))
            if not isinstance(data, dict) or not isinstance(
                data.get("research_results"), list
            ):
                raise ValueError("industry research_results must be a list")
            if data.get("as_of_date") != as_of_date:
                raise ValueError("industry as_of_date mismatch")
            if data.get("sector_type") != "industry":
                raise ValueError("industry top-level sector_type mismatch")
            if data.get("report_type") != "sector_research":
                raise ValueError("industry report_type mismatch")
            parsed_industries = []
            for item in data["research_results"]:
                if not isinstance(item, dict):
                    raise ValueError("industry row must be an object")
                required_fields = {
                    "sector_name",
                    "sector_type",
                    "consensus_label",
                    "ranking_score",
                    "opportunity_score",
                    "evidence_score",
                    "confidence_score",
                }
                if not required_fields.issubset(item):
                    raise ValueError("industry row missing required fields")
                _name = _stable_text(item.get("sector_name"), "sector_name")
                _sector_type = _stable_text(
                    item.get("sector_type"), "sector_type"
                )
                if _sector_type != "industry":
                    raise ValueError("industry row sector_type mismatch")
                _scores = _industry_score_map.get(_name, {})
                parsed_industries.append({
                    "sector_name": _name,
                    "sector_type": "industry",
                    "ranking_score": _stable_required_finite_number(
                        item.get("ranking_score"), "ranking_score"
                    ),
                    "opportunity_score": _stable_required_finite_number(
                        item.get("opportunity_score"), "opportunity_score"
                    ),
                    "evidence_score": _stable_required_finite_number(
                        item.get("evidence_score"), "evidence_score"
                    ),
                    "confidence_score": _stable_required_finite_number(
                        item.get("confidence_score"), "confidence_score"
                    ),
                    "trend_score": _stable_finite_number(
                        _scores.get("trend_score", 0), "trend_score"
                    ),
                    "burst_score": _stable_finite_number(
                        _scores.get("burst_score", 0), "burst_score"
                    ),
                    "trend_level": _stable_text(
                        _scores.get("trend_level", ""),
                        "trend_level",
                        allow_empty=True,
                    ),
                    "trend_level_cn": _stable_text(
                        _scores.get("trend_level_cn", ""),
                        "trend_level_cn",
                        allow_empty=True,
                    ),
                    "burst_level": _stable_text(
                        _scores.get("burst_level", ""),
                        "burst_level",
                        allow_empty=True,
                    ),
                    "burst_level_cn": _stable_text(
                        _scores.get("burst_level_cn", ""),
                        "burst_level_cn",
                        allow_empty=True,
                    ),
                    "agent_label": _stable_text(
                        item.get("consensus_label"),
                        "consensus_label",
                    ),
                })
            result["industries"] = parsed_industries
        except Exception:
            pass

    # --- Load concepts from concept_unified_rank.csv ---
    concept_path = _resolve_override_confined_path(
        STABLE_CONCEPT_DIR / as_of_date / "concept_unified_rank.csv",
        confined_root=STABLE_CONCEPT_DIR,
    )
    if concept_path is not None:
        try:
            import csv
            concept_text = _read_override_confined_text(
                concept_path,
                encoding="utf-8-sig",
                confined_root=STABLE_CONCEPT_DIR,
            )
            if concept_text is None:
                raise OSError("concept input escaped explicit report root")
            reader = csv.DictReader(io.StringIO(concept_text))
            required_columns = {
                "rank",
                "sector_name",
                "concept_final_rank_score",
                "trend_continuation_score",
                "short_term_burst_score",
                "agent_consensus_label",
            }
            if reader.fieldnames is None or not required_columns.issubset(
                reader.fieldnames
            ):
                raise ValueError("concept input missing required columns")
            parsed_concepts = []
            for row in reader:
                if not isinstance(row, dict):
                    raise ValueError("concept row must be an object")
                if row.get("rank") in (None, ""):
                    raise ValueError("rank must be a nonnegative integer")
                parsed_concepts.append({
                    "sector_name": _stable_text(
                        row.get("sector_name"), "sector_name"
                    ),
                    "sector_type": "concept",
                    "composite_score": _stable_required_finite_number(
                        row.get("concept_final_rank_score"),
                        "concept_final_rank_score",
                        allow_text=True,
                    ),
                    "trend_score": _stable_required_finite_number(
                        row.get("trend_continuation_score"),
                        "trend_continuation_score",
                        allow_text=True,
                    ),
                    "burst_score": _stable_required_finite_number(
                        row.get("short_term_burst_score"),
                        "short_term_burst_score",
                        allow_text=True,
                    ),
                    "rank": _stable_nonnegative_int(row.get("rank"), "rank"),
                    "agent_label": _stable_text(
                        row.get("agent_consensus_label"),
                        "agent_consensus_label",
                    ),
                })
            result["concepts"] = parsed_concepts
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
            "trend_score": (
                s.get("trend_score")
                if s.get("trend_score") is not None
                else s.get("ranking_score", 0)
            ),
            "burst_score": s.get("burst_score", 0),
            "trend_level": s.get("trend_level", "") or s.get("agent_label", ""),
            "trend_level_cn": s.get("trend_level_cn", ""),
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
            "trend_score": (
                s.get("trend_score")
                if s.get("trend_score") is not None
                else s.get("ranking_score", 0)
            ),
            "burst_score": s.get("burst_score", 0),
            "burst_level": s.get("burst_level", "") or s.get("agent_label", ""),
            "burst_level_cn": s.get("burst_level_cn", ""),
        })

    return trend_sectors, burst_sectors


def load_direction_candidate_shadow(
    as_of_date: str,
    *,
    candidate_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load confirmed direction candidates without affecting legacy inputs."""
    path = candidate_path or (
        DIRECTION_SHADOW_DIR
        / f"industry_direction_{as_of_date}"
        / "industry_direction_candidates.json"
    )
    result: Dict[str, Any] = {
        "status": "unavailable",
        "mode": "paper_shadow_research_only",
        "path": str(path),
        "sha256": None,
        "eligible_sectors": [],
        "confirmation_required": [],
        "error": None,
    }
    if not path.is_file():
        result["error"] = "direction candidate shadow report is missing"
        return result
    try:
        payload, sha256 = load_strict_json_with_sha256(path)
        if not isinstance(payload, dict):
            raise ValueError("direction candidate report must be an object")
        if payload.get("schema_version") != "industry_direction_candidate_selection.v1":
            raise ValueError("direction candidate schema_version mismatch")
        if payload.get("mode") != "paper_shadow_research_only":
            raise ValueError("direction candidate report must remain paper shadow")
        if payload.get("as_of_date") != as_of_date:
            raise ValueError("direction candidate as_of_date mismatch")

        eligible = []
        seen_names = set()
        for group_name in ("core_candidates", "supplemental_candidates"):
            rows = payload.get(group_name)
            if not isinstance(rows, list):
                raise ValueError(f"{group_name} must be an array")
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError(f"{group_name} row must be an object")
                name = str(row.get("sector_name") or "").strip()
                if not name or name in seen_names:
                    raise ValueError("direction candidate sector identity is invalid")
                seen_names.add(name)
                eligible.append(
                    {
                        "sector_name": name,
                        "sector_type": "industry",
                        "trend_score": _stable_required_finite_number(
                            row.get("time_series_score"), "time_series_score"
                        ),
                        "burst_score": _stable_required_finite_number(
                            row.get("rank_momentum_score"), "rank_momentum_score"
                        ),
                        "direction_score_shadow": _stable_required_finite_number(
                            row.get("direction_score_shadow"),
                            "direction_score_shadow",
                        ),
                        "direction_state": _stable_text(
                            row.get("direction_state"), "direction_state"
                        ),
                        "candidate_tier": (
                            "core" if group_name == "core_candidates" else "supplemental"
                        ),
                    }
                )
        confirmation_rows = payload.get("confirmation_required")
        if not isinstance(confirmation_rows, list):
            raise ValueError("confirmation_required must be an array")
        confirmations = []
        for row in confirmation_rows:
            if not isinstance(row, dict):
                raise ValueError("confirmation_required row must be an object")
            name = str(row.get("sector_name") or "").strip()
            if not name:
                raise ValueError("confirmation sector identity is invalid")
            confirmations.append(
                {
                    "sector_name": name,
                    "direction_score_shadow": _stable_required_finite_number(
                        row.get("direction_score_shadow"),
                        "direction_score_shadow",
                    ),
                    "direction_state": "pulse_confirmation_required",
                }
            )
        result.update(
            {
                "status": "ok",
                "sha256": sha256,
                "eligible_sectors": eligible,
                "confirmation_required": confirmations,
            }
        )
    except (OSError, UnicodeError, ValueError) as exc:
        result["error"] = str(exc)
    return result


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


_CACHE_STATUS_VALUES = {"ok", "degraded", "failed"}
_CACHE_SOURCE_VALUES = {
    "http_em",
    "http_stale",
    "http_mapping",
    "http_local_industry",
    "http_local_concept_members",
    "sina_fallback",
    "local_emergency_mapping",
    "unavailable",
}


def _valid_cache_payload(
    data: Any,
    *,
    expected_sector_name: Optional[str],
    expected_sector_type: Optional[str],
    expected_as_of_date: Optional[str],
) -> bool:
    required = {
        "status", "as_of_date", "sector_name", "sector_type", "stocks", "error",
        "fallback_used", "source",
    }
    if not isinstance(data, dict) or not required.issubset(data):
        return False
    if data["status"] not in _CACHE_STATUS_VALUES:
        return False
    if not isinstance(data["as_of_date"], str):
        return False
    try:
        cache_date = datetime.strptime(data["as_of_date"], "%Y-%m-%d")
    except ValueError:
        return False
    if cache_date.strftime("%Y-%m-%d") != data["as_of_date"]:
        return False
    if expected_as_of_date is not None and data["as_of_date"] != expected_as_of_date:
        return False
    if not isinstance(data["sector_name"], str) or not data["sector_name"].strip():
        return False
    if not isinstance(data["sector_type"], str) or not data["sector_type"].strip():
        return False
    if expected_sector_name is not None and data["sector_name"] != expected_sector_name:
        return False
    if expected_sector_type is not None and data["sector_type"] != expected_sector_type:
        return False
    if data["error"] is not None and not isinstance(data["error"], str):
        return False
    if not isinstance(data["fallback_used"], bool):
        return False
    if data["source"] not in _CACHE_SOURCE_VALUES:
        return False
    if not isinstance(data["stocks"], list):
        return False
    for stock in data["stocks"]:
        if not isinstance(stock, dict):
            return False
        if not isinstance(stock.get("code"), str) or not stock["code"].strip():
            return False
        if not isinstance(stock.get("name"), str) or not stock["name"].strip():
            return False
        weight = stock.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            return False
        try:
            finite_weight = float(weight)
        except (OverflowError, TypeError, ValueError):
            return False
        if not math.isfinite(finite_weight) or finite_weight < 0:
            return False
    return True


def _load_cache(
    key: str,
    *,
    expected_sector_name: Optional[str] = None,
    expected_sector_type: Optional[str] = None,
    expected_as_of_date: Optional[str] = None,
) -> Optional[Dict]:
    """从缓存加载板块成分股数据"""
    cache_file = _resolve_cache_file(key)
    if cache_file is not None:
        try:
            cache_text = _read_override_confined_text(
                cache_file, encoding="utf-8-sig", confined_root=CACHE_DIR
            )
            if cache_text is None:
                return None
            cache_data = loads_strict_json(cache_text, context=str(cache_file))
            if _valid_cache_payload(
                cache_data,
                expected_sector_name=expected_sector_name,
                expected_sector_type=expected_sector_type,
                expected_as_of_date=expected_as_of_date,
            ):
                return cache_data
        except Exception:
            pass
    return None


def _save_cache(key: str, data: Dict):
    """保存板块成分股数据到缓存"""
    if _REPORT_ROOT_OVERRIDE is not None:
        # Explicit roots are immutable inputs. Disabling cache writes removes the
        # create-time junction race while preserving the legacy default cache.
        return
    cache_dir = CACHE_DIR.expanduser().resolve()
    cache_file = _resolve_cache_file(key)
    if cache_dir is None or cache_file is None:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _resolve_cache_file(key: str) -> Optional[Path]:
    if not isinstance(key, str) or not key or "\x00" in key:
        return None
    if _REPORT_ROOT_OVERRIDE is not None:
        return _resolve_override_confined_path(
            CACHE_DIR / f"{key}.json", confined_root=CACHE_DIR
        )
    try:
        cache_root = CACHE_DIR.expanduser().resolve()
        cache_file = (cache_root / f"{key}.json").resolve()
        cache_file.relative_to(cache_root)
        if cache_file.parent != cache_root:
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return cache_file


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
    if as_of is not None and not _is_valid_iso_date(as_of):
        raise ValueError(f"invalid analysis date: {as_of}")

    # Bind cache identity to the requested research date, or today for legacy calls.
    cache_date = as_of or datetime.now().strftime("%Y-%m-%d")
    cache_key = _cache_key(sector_name, sector_type, cache_date)
    cached = _load_cache(
        cache_key,
        expected_sector_name=sector_name,
        expected_sector_type=sector_type,
        expected_as_of_date=cache_date,
    )
    if cached:
        return cached

    result = {
        "status": "ok",
        "as_of_date": cache_date,
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

    # Attempt 2a: Sina Finance fallback
    if not http_ok:
        sina_stocks = _fetch_sina_constituents(sector_name)
        if sina_stocks:
            total_mv = sum(s.get("mktcap", 0) for s in sina_stocks) or 1
            equal_w = 1.0 / len(sina_stocks)
            result["stocks"] = [
                {
                    "code": s["code"],
                    "name": s["name"],
                    "weight": round(s.get("mktcap", 0) / total_mv, 4) if total_mv > 0 else equal_w,
                }
                for s in sina_stocks
            ]
            result["status"] = "degraded"
            result["fallback_used"] = True
            result["source"] = "sina_fallback"
            result["error"] = f"使用新浪财经成分股（{len(sina_stocks)}只）"
            _save_cache(cache_key, result)
            return result

    # Attempt 2b: local SECTOR_STOCK_MAPPING (emergency fallback)
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

    # 降级：尝试新浪财经（含 THS→新浪名称映射）
    try:
        import requests
        url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_bkzj_bk?page=1&num=50&sort=netamount&asc=0&fenlei=0"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            data = resp.json()
            sina_flow = {item.get("name"): float(item.get("netamount", 0)) for item in data}

            # 1. 精确匹配
            if sector_name in sina_flow:
                net = sina_flow[sector_name]
                result["net_flow"] = net
                result["direction"] = "inflow" if net > 0 else "outflow" if net < 0 else "neutral"
                result["status"] = "ok"
                result["error"] = None
                return result

            # 2. THS→新浪名称映射
            _THS_TO_SINA_MAP = {
                "电子化学品": "电子器件", "电子元件": "电子器件",
                "游戏": "传媒娱乐", "影视院线": "传媒娱乐", "文化传媒": "传媒娱乐",
                "半导体": "电子信息", "互联网电商": "电子信息",
                "美容护理": "化工行业", "造纸": "造纸行业",
                "工程机械": "机械行业", "专用设备": "机械行业", "通用设备": "机械行业",
                "化学制药": "生物制药", "生物制品": "生物制药", "医疗服务": "医疗器械",
                "白酒": "酿酒行业", "证券": "金融行业", "银行": "金融行业",
                "保险": "金融行业", "房地产": "房地产",
                "汽车整车": "汽车制造", "汽车零部件": "汽车制造",
                "煤炭": "煤炭行业", "石油石化": "石油行业",
                "电力": "电力行业", "燃气": "供水供气", "环保": "环保行业",
                "建筑装饰": "建筑建材", "建筑材料": "建筑建材",
                "交通运输": "交通运输", "航空运输": "交通运输", "航运港口": "交通运输",
                "食品饮料": "食品行业", "纺织服装": "纺织行业",
                "家电": "家电行业", "白色家电": "家电行业", "小家电": "家电行业",
            }
            mapped_name = _THS_TO_SINA_MAP.get(sector_name)
            if mapped_name and mapped_name in sina_flow:
                net = sina_flow[mapped_name]
                result["net_flow"] = net
                result["direction"] = "inflow" if net > 0 else "outflow" if net < 0 else "neutral"
                result["status"] = "ok"
                result["error"] = None
                return result

            # 3. 模糊匹配
            for sina_name, net in sina_flow.items():
                if sector_name in sina_name or sina_name in sector_name:
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
    _validated_score_report: Optional[Tuple[str, Path, Dict[str, Any]]] = None,
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
        "direction_shadow_sectors": [],
        "direction_confirmation_sectors": [],
        "cross_sectors": [],
        "api_status": {
            "http_constituents": "ok",
            "tencent_quotes": "ok",
            "fund_flow": "ok",
        },
        "warnings": [],
        "generated_at": datetime.now().isoformat(),
        "linkage_research": {
            "mode": "paper_shadow_research_only",
            "legacy_policy": legacy_linkage_policy_contract(),
            "effective_policy": effective_legacy_linkage_policy_contract(
                trend_top_n=trend_top_n,
                burst_top_n=burst_top_n,
                minimum_relevance=min_relevance,
            ),
            "score_input": None,
            "sector_funnel": [],
            "constituent_audit_by_sector": {},
            "disclaimer": "No broker connection and no live order instruction.",
        },
    }

    # Step 1: 读取板块评分报告 (Phase 22: stable inputs first)
    print("  [1/5] 读取板块评分报告...")
    if _validated_score_report is None:
        valid, _validated_score_report, error = validate_explicit_score_report(
            as_of_date
        )
        if not valid or _validated_score_report is None:
            output["status"] = "failed"
            output["warnings"].append(error or "板块评分报告校验失败")
            return output
    actual_date, report_path, validated_score_data = _validated_score_report
    try:
        validate_sector_score_payload(validated_score_data, expected_as_of=actual_date)
    except ValueError as exc:
        output["status"] = "failed"
        output["warnings"].append(f"sector_scores JSON 无效: {exc}")
        return output

    if actual_date != as_of_date:
        output["warnings"].append(f"指定日期 {as_of_date} 无报告，使用 {actual_date}")

    output["as_of_date"] = actual_date
    canonical_score_input = json.dumps(
        validated_score_data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    score_input_sha256 = hashlib.sha256(canonical_score_input).hexdigest()
    output["linkage_research"]["score_input"] = {
        "as_of_date": actual_date,
        "path": str(report_path),
        "sha256": score_input_sha256,
        "sha256_basis": "canonical_validated_payload",
        "source_file_sha256": (
            hashlib.sha256(report_path.read_bytes()).hexdigest()
            if report_path.is_file()
            else None
        ),
    }

    # Phase 22: try stable inputs first
    stable = load_stable_sector_inputs(actual_date, score_data=validated_score_data)
    if stable["available"]:
        trend_sectors_meta, burst_sectors_meta = extract_top_sectors_from_stable(stable, trend_top_n, burst_top_n)
        output["sector_input_source"] = stable["source"]
        print(f"    ✅ 使用稳定产线数据: {stable['source']} "
              f"(行业{len(stable['industries'])}个, 概念{len(stable['concepts'])}个)")
    else:
        data = validated_score_data or load_sector_scores(report_path)
        trend_sectors_meta, burst_sectors_meta = extract_top_sectors(data, trend_top_n, burst_top_n)
        output["sector_input_source"] = "legacy_sector_scores"
        print(f"    ⚠️ 使用旧评分数据 (无稳定产线数据)")

    cross_sector_names = find_cross_sectors(trend_sectors_meta, burst_sectors_meta)
    output["cross_sectors"] = cross_sector_names

    direction_shadow = load_direction_candidate_shadow(actual_date)
    output["linkage_research"]["direction_shadow_input"] = {
        key: direction_shadow.get(key)
        for key in ("status", "mode", "path", "sha256", "error")
    }
    direction_sectors_meta = direction_shadow["eligible_sectors"]
    output["direction_confirmation_sectors"] = direction_shadow[
        "confirmation_required"
    ]

    legacy_sectors = {s["sector_name"]: s for s in trend_sectors_meta}
    legacy_sectors.update({s["sector_name"]: s for s in burst_sectors_meta})
    direction_only_sectors = {
        sector["sector_name"]: sector
        for sector in direction_sectors_meta
        if sector["sector_name"] not in legacy_sectors
    }
    all_sectors = {**legacy_sectors, **direction_only_sectors}

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
    direction_source_counter = dict.fromkeys(source_counter, 0)

    for name in all_sectors:
        meta = all_sectors[name]
        result = fetch_sector_constituents(name, meta.get("sector_type", "industry"), as_of=output.get("as_of_date"))
        sector_stocks[name] = result
        src = result.get("source", "unavailable")
        target_counter = (
            source_counter if name in legacy_sectors else direction_source_counter
        )
        if src in target_counter:
            target_counter[src] += 1
        else:
            target_counter[src] = 1
        status_emoji = "✅" if result["status"] == "ok" else "⚠️" if result["status"] == "degraded" else "❌"
        print(f"    {status_emoji} {name}: {len(result['stocks'])} 只成分股 [{src}]" +
              (f" ({result['error']})" if result["error"] else ""))
        if name in legacy_sectors and "local_emergency" in result.get("source", ""):
            output["api_status"]["http_constituents"] = "degraded"

    output["constituent_source_summary"] = source_counter
    output["linkage_research"]["direction_constituent_source_summary"] = (
        direction_source_counter
    )

    # Step 3: 获取行情数据
    print("  [3/5] 获取成分股行情...")
    legacy_codes = set()
    direction_codes = set()
    for name, sec_data in sector_stocks.items():
        for s in sec_data.get("stocks", []):
            if name in legacy_sectors:
                legacy_codes.add(s["code"])
            elif s["code"] not in legacy_codes:
                direction_codes.add(s["code"])

    legacy_quotes = fetch_tencent_quotes(list(legacy_codes))
    direction_quotes = (
        fetch_tencent_quotes(list(direction_codes)) if direction_codes else {}
    )
    quotes = {**legacy_quotes, **direction_quotes}
    if not legacy_quotes:
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
        if name in legacy_sectors and flow["status"] != "ok":
            output["api_status"]["fund_flow"] = "degraded"

    # 获取个股资金流
    legacy_individual_flows = fetch_individual_fund_flow(list(legacy_codes))
    direction_individual_flows = (
        fetch_individual_fund_flow(list(direction_codes)) if direction_codes else {}
    )
    individual_flows = {**legacy_individual_flows, **direction_individual_flows}
    if legacy_individual_flows:
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
                    "weight": s.get("weight", 0),
                    "sector_weight": s.get("weight", 0),
                    "change_pct": q.get("change_pct", 0),
                    "price": q.get("price", 0),
                    "total_mv": q.get("total_mv", 0),
                    "pe": q.get("pe", 0),
                    "pb": q.get("pb", 0),
                    "individual_fund_flow": flow.get("net_flow", 0),
                    "individual_flow_direction": flow.get("direction", "neutral"),
                    "individual_flow_available": code in individual_flows,
                    "quote_available": code in quotes,
                })

            # 计算关联度
            flow_data = sector_flows.get(name, {"direction": "neutral"})
            filtered = compute_relevance_scores(enriched, flow_data, min_relevance)
            informative_weights = {
                float(stock.get("weight", 0))
                for stock in enriched
                if isinstance(stock.get("weight"), (int, float))
                and not isinstance(stock.get("weight"), bool)
                and math.isfinite(float(stock.get("weight", 0)))
                and float(stock.get("weight", 0)) > 0
            }
            weight_signal_available = len(informative_weights) > 1
            sector_flow_available = (
                flow_data.get("status") == "ok"
                and flow_data.get("direction") in {"inflow", "outflow"}
            )
            for stock in enriched:
                stock["weight_signal_available"] = weight_signal_available
                stock["constituent_source"] = sec_data.get(
                    "source", "unavailable"
                )
                stock["sector_flow_status"] = flow_data.get(
                    "status", "unavailable"
                )
                stock["sector_flow_direction"] = flow_data.get(
                    "direction", "neutral"
                )
                if (
                    sector_flow_available
                    and stock["individual_flow_available"]
                    and stock["individual_flow_direction"] in {"inflow", "outflow"}
                ):
                    stock["linkage_flow_alignment_score"] = (
                        _compute_flow_alignment(
                            stock["individual_flow_direction"],
                            stock["sector_flow_direction"],
                        )
                    )
                else:
                    stock["linkage_flow_alignment_score"] = None
            if name not in output["linkage_research"]["constituent_audit_by_sector"]:
                output["linkage_research"]["constituent_audit_by_sector"][name] = (
                    build_constituent_linkage_input_contract(
                        enriched,
                        as_of_date=output["as_of_date"],
                        sector_name=name,
                        sector_type=meta.get("sector_type", "industry"),
                        constituent_source=sec_data.get("source", "unavailable"),
                        sector_flow_status=flow_data.get("status", "unavailable"),
                    )
                )

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
            if label == "direction_shadow":
                sector_entry.update(
                    {
                        "candidate_tier": meta.get("candidate_tier"),
                        "direction_score_shadow": meta.get(
                            "direction_score_shadow"
                        ),
                        "direction_state": meta.get("direction_state"),
                        "shadow_prefilter_stocks": enriched,
                    }
                )
            sector_results.append(sector_entry)
            output["linkage_research"]["sector_funnel"].append(
                {
                    "path": label,
                    "sector_name": name,
                    "sector_type": meta.get("sector_type", "industry"),
                    "constituent_source": sec_data.get("source", "unavailable"),
                    "raw_constituent_count": len(stocks_raw),
                    "legacy_relevance_pass_count": len(filtered),
                    "legacy_relevance_reject_count": len(stocks_raw) - len(filtered),
                    "minimum_relevance": min_relevance,
                }
            )

            status_emoji = "✅" if filtered else "⚠️"
            print(f"    {status_emoji} [{label}] {name}: {len(filtered)}/{len(stocks_raw)} 只高关联度")

        return sector_results

    output["trend_sectors"] = _build_sector_stocks(trend_sectors_meta, "趋势")
    output["burst_sectors"] = _build_sector_stocks(burst_sectors_meta, "短线")
    output["direction_shadow_sectors"] = _build_sector_stocks(
        direction_sectors_meta, "direction_shadow"
    )

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
