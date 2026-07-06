"""
外部催化数据源研究

研究并验证可用于板块/概念催化事件识别的外部数据源。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class CatalystDataSourceResearch:
    """
    外部催化数据源研究

    枚举候选数据源，对可访问接口做小样本探测。
    """

    def __init__(self):
        """初始化"""
        self.results = []

    def run_research(
        self,
        as_of_date: str = "2026-06-29",
        sector_type: str = "industry",
    ) -> Dict[str, Any]:
        """
        运行数据源研究

        Args:
            as_of_date: 基准日期
            sector_type: 板块类型

        Returns:
            研究结果
        """
        sources = []

        # 1. AkShare 新闻接口
        sources.append(self._research_akshare_news(as_of_date))

        # 2. AkShare 公告接口
        sources.append(self._research_akshare_notice(as_of_date))

        # 3. AkShare 概念/行业信息接口
        sources.append(self._research_akshare_board_info(as_of_date))

        # 4. 巨潮资讯公告
        sources.append(self._research_cninfo(as_of_date))

        # 5. 公开政策/宏观事件源
        sources.append(self._research_macro_events(as_of_date))

        # 汇总
        available_count = sum(1 for s in sources if s.get("status") == "available")
        partial_count = sum(1 for s in sources if s.get("status") == "partial")
        unavailable_count = sum(1 for s in sources if s.get("status") == "unavailable")

        result = {
            "report_type": "catalyst_data_source_research",
            "as_of_date": as_of_date,
            "sector_type": sector_type,
            "total_sources": len(sources),
            "available_count": available_count,
            "partial_count": partial_count,
            "unavailable_count": unavailable_count,
            "sources": sources,
            "recommendations": self._generate_recommendations(sources),
            "disclaimer": "仅用于数据源研究，不作为操作依据。",
        }

        return result

    def _research_akshare_news(self, as_of_date: str) -> Dict[str, Any]:
        """研究 AkShare 新闻接口"""
        source = {
            "name": "AkShare Stock News (stock_news_em)",
            "category": "news",
            "status": "unavailable",
            "fields": [],
            "sample_count": 0,
            "history_coverage": "unknown",
            "stability": "unknown",
            "notes": [],
        }

        try:
            import akshare as ak
            # 尝试获取新闻数据
            # stock_news_em 需要 symbol 参数，这里用一个示例股票测试
            df = ak.stock_news_em(symbol="000001")
            if df is not None and len(df) > 0:
                source["status"] = "available"
                source["fields"] = list(df.columns)
                source["sample_count"] = min(len(df), 10)
                source["history_coverage"] = "recent only"
                source["stability"] = "moderate"
                source["notes"].append(f"获取到 {len(df)} 条新闻")
                source["notes"].append("需要按股票代码查询，非板块级")
        except Exception as e:
            source["status"] = "unavailable"
            source["notes"].append(f"访问失败: {str(e)[:100]}")

        return source

    def _research_akshare_notice(self, as_of_date: str) -> Dict[str, Any]:
        """研究 AkShare 公告接口"""
        source = {
            "name": "AkShare Stock Notice (stock_notice_report)",
            "category": "notice",
            "status": "unavailable",
            "fields": [],
            "sample_count": 0,
            "history_coverage": "unknown",
            "stability": "unknown",
            "notes": [],
        }

        try:
            import akshare as ak
            # 尝试获取公告数据
            df = ak.stock_notice_report(symbol="000001", date="20260629")
            if df is not None and len(df) > 0:
                source["status"] = "available"
                source["fields"] = list(df.columns)
                source["sample_count"] = min(len(df), 10)
                source["history_coverage"] = "recent only"
                source["stability"] = "moderate"
                source["notes"].append(f"获取到 {len(df)} 条公告")
        except Exception as e:
            source["status"] = "unavailable"
            source["notes"].append(f"访问失败: {str(e)[:100]}")

        return source

    def _research_akshare_board_info(self, as_of_date: str) -> Dict[str, Any]:
        """研究 AkShare 概念/行业信息接口"""
        source = {
            "name": "AkShare Board Info (stock_board_concept_info_ths)",
            "category": "board_info",
            "status": "unavailable",
            "fields": [],
            "sample_count": 0,
            "history_coverage": "unknown",
            "stability": "unknown",
            "notes": [],
        }

        try:
            import akshare as ak
            # 尝试获取概念板块信息
            df = ak.stock_board_concept_info_ths()
            if df is not None and len(df) > 0:
                source["status"] = "partial"
                source["fields"] = list(df.columns)
                source["sample_count"] = min(len(df), 10)
                source["history_coverage"] = "current snapshot only"
                source["stability"] = "moderate"
                source["notes"].append(f"获取到 {len(df)} 个概念板块信息")
                source["notes"].append("仅当前快照，无历史事件数据")
        except Exception as e:
            source["status"] = "unavailable"
            source["notes"].append(f"访问失败: {str(e)[:100]}")

        return source

    def _research_cninfo(self, as_of_date: str) -> Dict[str, Any]:
        """研究巨潮资讯公告"""
        source = {
            "name": "CNINFO Announcements",
            "category": "announcement",
            "status": "unavailable",
            "fields": [],
            "sample_count": 0,
            "history_coverage": "unknown",
            "stability": "unknown",
            "notes": [],
        }

        try:
            import akshare as ak
            # 尝试获取巨潮资讯公告
            # stock_individual_notice_report 需要 symbol
            df = ak.stock_individual_notice_report(symbol="000001")
            if df is not None and len(df) > 0:
                source["status"] = "partial"
                source["fields"] = list(df.columns)
                source["sample_count"] = min(len(df), 10)
                source["history_coverage"] = "recent only"
                source["stability"] = "moderate"
                source["notes"].append(f"获取到 {len(df)} 条公告")
                source["notes"].append("需要按股票代码查询")
        except Exception as e:
            source["status"] = "unavailable"
            source["notes"].append(f"访问失败: {str(e)[:100]}")

        return source

    def _research_macro_events(self, as_of_date: str) -> Dict[str, Any]:
        """研究公开政策/宏观事件源"""
        source = {
            "name": "Macro Economic News (news_economic_baidu)",
            "category": "macro_news",
            "status": "unavailable",
            "fields": [],
            "sample_count": 0,
            "history_coverage": "unknown",
            "stability": "unknown",
            "notes": [],
        }

        try:
            import akshare as ak
            # 尝试获取宏观经济新闻
            df = ak.news_economic_baidu()
            if df is not None and len(df) > 0:
                source["status"] = "partial"
                source["fields"] = list(df.columns)
                source["sample_count"] = min(len(df), 10)
                source["history_coverage"] = "recent only"
                source["stability"] = "low"
                source["notes"].append(f"获取到 {len(df)} 条宏观新闻")
                source["notes"].append("非结构化，需要 NLP 处理")
        except Exception as e:
            source["status"] = "unavailable"
            source["notes"].append(f"访问失败: {str(e)[:100]}")

        return source

    def _generate_recommendations(self, sources: List[Dict]) -> List[str]:
        """生成建议"""
        recommendations = []

        available = [s for s in sources if s["status"] == "available"]
        partial = [s for s in sources if s["status"] == "partial"]

        if available:
            recommendations.append(
                f"可用数据源: {', '.join(s['name'] for s in available)}"
            )

        if partial:
            recommendations.append(
                f"部分可用数据源: {', '.join(s['name'] for s in partial)}"
            )

        recommendations.append("建议: 先接入可用数据源，逐步扩展到部分可用数据源")
        recommendations.append("注意: 所有外部数据需经过缓存层，避免网络依赖")

        return recommendations


def save_catalyst_research(output_dir: str, report_data: Dict[str, Any]):
    """保存研究结果"""
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "catalyst_data_source_research.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON report saved: {json_path}")

    # 生成 Markdown
    md_report = generate_catalyst_research_report(report_data)
    md_path = os.path.join(output_dir, "catalyst_data_source_research.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown report saved: {md_path}")


def generate_catalyst_research_report(report_data: Dict[str, Any]) -> str:
    """生成研究结果 Markdown 报告"""
    lines = []

    lines.append("# 外部催化数据源研究报告")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于数据源研究，不作为操作依据。")
    lines.append("")

    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **基准日期**: {report_data.get('as_of_date', '')}")
    lines.append(f"- **候选数据源**: {report_data.get('total_sources', 0)}")
    lines.append(f"- **可用**: {report_data.get('available_count', 0)}")
    lines.append(f"- **部分可用**: {report_data.get('partial_count', 0)}")
    lines.append(f"- **不可用**: {report_data.get('unavailable_count', 0)}")
    lines.append("")

    lines.append("## 数据源详情")
    lines.append("")
    for source in report_data.get("sources", []):
        lines.append(f"### {source.get('name', '')}")
        lines.append("")
        lines.append(f"- **类别**: {source.get('category', '')}")
        lines.append(f"- **状态**: {source.get('status', '')}")
        lines.append(f"- **样本数**: {source.get('sample_count', 0)}")
        lines.append(f"- **历史覆盖**: {source.get('history_coverage', '')}")
        lines.append(f"- **稳定性**: {source.get('stability', '')}")
        if source.get("fields"):
            lines.append(f"- **字段**: {', '.join(source['fields'][:5])}")
        if source.get("notes"):
            for note in source["notes"]:
                lines.append(f"  - {note}")
        lines.append("")

    lines.append("## 建议")
    lines.append("")
    for rec in report_data.get("recommendations", []):
        lines.append(f"- {rec}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于数据源研究，不作为操作依据。*")

    return "\n".join(lines)
