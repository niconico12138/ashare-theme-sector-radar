"""
映射质量分析

分析 catalyst event 到板块的映射质量。
"""

import json
import os
from typing import Any, Dict, List


class MappingQualityAnalyzer:
    """
    映射质量分析

    分析 catalyst event 到板块的映射质量。
    """

    def analyze(
        self,
        events: List[Dict[str, Any]],
        date_range: str = "",
    ) -> Dict[str, Any]:
        """
        分析映射质量

        Args:
            events: 事件列表
            date_range: 日期范围

        Returns:
            映射质量分析结果
        """
        if not events:
            return {
                "date_range": date_range,
                "event_count": 0,
                "mapped_count": 0,
                "unmapped_count": 0,
                "mapping_rate": 0.0,
                "status_counts": {},
                "top_unmapped": [],
                "warnings": [],
            }

        # 统计映射状态
        status_counts = {}
        mapped_count = 0
        unmapped_count = 0
        unmapped_symbols = {}

        for event in events:
            status = event.get("mapping_status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

            # 判断是否 unmapped
            industries = event.get("related_industries", [])
            concepts = event.get("related_concepts", [])
            is_unmapped = len(industries) == 0 and len(concepts) == 0

            if is_unmapped:
                unmapped_count += 1
                # 统计 unmapped symbols
                for sym in event.get("related_symbols", []):
                    if sym not in unmapped_symbols:
                        unmapped_symbols[sym] = {
                            "symbol": sym,
                            "name": "",
                            "count": 0,
                            "reason": status,
                        }
                    unmapped_symbols[sym]["count"] += 1
                    name = event.get("related_symbol_names", [])
                    if name:
                        unmapped_symbols[sym]["name"] = name[0]
            else:
                mapped_count += 1

        # 计算映射率
        mapping_rate = mapped_count / len(events) if events else 0

        # Top unmapped
        top_unmapped = sorted(
            unmapped_symbols.values(),
            key=lambda x: -x["count"]
        )[:10]

        return {
            "date_range": date_range,
            "event_count": len(events),
            "mapped_count": mapped_count,
            "unmapped_count": unmapped_count,
            "mapping_rate": round(mapping_rate, 2),
            "status_counts": status_counts,
            "top_unmapped": top_unmapped,
            "warnings": [],
        }


def save_mapping_quality_report(output_dir: str, report_data: Dict[str, Any]):
    """保存映射质量报告"""
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "catalyst_mapping_quality.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON report saved: {json_path}")

    md_report = generate_mapping_quality_md(report_data)
    md_path = os.path.join(output_dir, "catalyst_mapping_quality.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown report saved: {md_path}")


def generate_mapping_quality_md(report_data: Dict[str, Any]) -> str:
    """生成映射质量 Markdown 报告"""
    lines = []

    lines.append("# 催化事件映射质量报告")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于数据质量验证，不作为操作依据。")
    lines.append("")

    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **日期范围**: {report_data.get('date_range', '')}")
    lines.append(f"- **事件总数**: {report_data.get('event_count', 0)}")
    lines.append(f"- **已映射**: {report_data.get('mapped_count', 0)}")
    lines.append(f"- **未映射**: {report_data.get('unmapped_count', 0)}")
    lines.append(f"- **映射率**: {report_data.get('mapping_rate', 0):.0%}")
    lines.append("")

    # 映射状态分布
    status_counts = report_data.get("status_counts", {})
    if status_counts:
        lines.append("## 映射状态分布")
        lines.append("")
        lines.append("| 状态 | 数量 |")
        lines.append("|------|------|")
        for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {status} | {count} |")
        lines.append("")

    # Top unmapped
    top_unmapped = report_data.get("top_unmapped", [])
    if top_unmapped:
        lines.append("## Top 未映射")
        lines.append("")
        lines.append("| Symbol | 名称 | 出现次数 | 原因 |")
        lines.append("|--------|------|----------|------|")
        for item in top_unmapped:
            lines.append(
                f"| {item.get('symbol', '')} | "
                f"{item.get('name', '')} | "
                f"{item.get('count', 0)} | "
                f"{item.get('reason', '')} |"
            )
        lines.append("")

    # 改进建议
    lines.append("## 改进建议")
    lines.append("")
    mapping_rate = report_data.get("mapping_rate", 0)
    if mapping_rate < 0.5:
        lines.append("- 映射率较低，建议扩展成分股数据源")
        lines.append("- 增加更多 alias 映射规则")
        lines.append("- 考虑接入 AkShare 成分股接口")
    elif mapping_rate < 0.8:
        lines.append("- 映射率中等，可继续优化 alias 映射")
    else:
        lines.append("- 映射率较高，当前映射质量可接受")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于数据质量验证，不作为操作依据。*")

    return "\n".join(lines)
