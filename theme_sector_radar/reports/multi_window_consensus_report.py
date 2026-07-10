"""
多窗口趋势共识报告生成

生成多窗口趋势共识的 JSON 和 Markdown 报告。
"""

import json
import os
from typing import Any, Dict, List


def generate_multi_window_consensus_report(
    report_data: Dict[str, Any],
) -> str:
    """
    生成多窗口趋势共识 Markdown 报告

    Args:
        report_data: 报告数据字典

    Returns:
        Markdown 报告字符串
    """
    lines = []

    # 标题
    lines.append("# 多窗口趋势共识报告")
    lines.append("")

    # 免责声明
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    # 参数
    lines.append("## 参数")
    lines.append("")
    lines.append(f"- **日期**: {report_data.get('as_of_date', '')}")
    lines.append(f"- **板块类型**: {report_data.get('sector_type', '')}")
    lines.append(f"- **趋势权重方案**: {report_data.get('trend_weight_profile', '')}")

    windows = report_data.get("windows", [5, 10, 20])
    lines.append(f"- **窗口**: {', '.join(str(w) for w in windows)}")

    metadata = report_data.get("metadata", {})
    lines.append(f"- **基准**: {metadata.get('benchmark', 'none')}")
    lines.append(f"- **历史范围**: {metadata.get('history_start_date', '')} ~ {metadata.get('history_end_date', '')}")
    lines.append("")

    # 共识 Top N
    consensus = report_data.get("consensus", [])
    lines.append(f"## 共识 Top {len(consensus)}")
    lines.append("")
    lines.append("| 排名 | 板块 | 共识标签 | 共识分 | 基础分 | 动量加分 | 量价比 | 5日分 | 10日分 | 20日分 | 市场环境 | 共识强度 | 观察要点 |")
    lines.append("|------|------|----------|--------|--------|----------|--------|-------|--------|--------|----------|----------|----------|")

    for i, item in enumerate(consensus, 1):
        window_scores = item.get("window_scores", {})
        watch_points = item.get("watch_points", [])
        watch_summary = watch_points[0] if watch_points else "-"

        lines.append(
            f"| {i} | {item.get('sector_name', '')} | "
            f"{item.get('multi_window_label', '')} | "
            f"{item.get('consensus_score', 0):.1f} | "
            f"{item.get('base_consensus', 0):.1f} | "
            f"{item.get('momentum_bonus', 0):+.1f} | "
            f"{item.get('volume_confirmation_ratio', 1.0):.2f} | "
            f"{window_scores.get('5', 0):.1f} | "
            f"{window_scores.get('10', 0):.1f} | "
            f"{window_scores.get('20', 0):.1f} | "
            f"{item.get('market_regime', '-')} | "
            f"{item.get('consensus_strength', '')} | "
            f"{watch_summary[:30]}... |"
        )
    lines.append("")

    # 自适应权重说明
    lines.append("### 自适应权重说明")
    lines.append("")
    lines.append("| 市场环境 | 5日权重 | 10日权重 | 20日权重 | 判断条件 |")
    lines.append("|----------|---------|----------|----------|----------|")
    lines.append("| 趋势行情 (trending) | 0.15 | 0.30 | 0.55 | CV > 0.15，看长窗口 |")
    lines.append("| 震荡行情 (oscillating) | 0.35 | 0.35 | 0.30 | CV < 0.08，看短窗口 |")
    lines.append("| 突破行情 (breakout) | 0.40 | 0.35 | 0.25 | 0.08 ≤ CV ≤ 0.15 |")
    lines.append("")
    lines.append("> CV = 窗口分标准差 / 窗口分均值，反映三个窗口的分歧程度")
    lines.append("")

    # 量价共振说明
    lines.append("### 量价共振说明")
    lines.append("")
    lines.append("- 放量（volume_or_heat ≥ 7）+ 趋势分高（≥ 50）→ 共识分 ×1.1")
    lines.append("- 缩量（volume_or_heat ≤ 3）+ 趋势分高（≥ 50）→ 共识分 ×0.9（假突破风险）")
    lines.append("- 其他情况 → 不调整")
    lines.append("")

    # 窗口分歧
    conflicted = [item for item in consensus if item.get("window_conflicts")]
    if conflicted:
        lines.append("## 窗口分歧")
        lines.append("")
        lines.append("| 板块 | 共识标签 | 分歧说明 |")
        lines.append("|------|----------|----------|")

        for item in conflicted:
            conflicts = item.get("window_conflicts", [])
            conflict_summary = "; ".join(conflicts[:2])
            lines.append(
                f"| {item.get('sector_name', '')} | "
                f"{item.get('multi_window_label', '')} | "
                f"{conflict_summary[:50]}... |"
            )
        lines.append("")

    # 数据质量提示
    data_warnings = []
    for item in consensus:
        warnings = item.get("data_warnings", [])
        data_warnings.extend(warnings)

    if data_warnings:
        lines.append("## 数据质量提示")
        lines.append("")
        for warning in set(data_warnings):
            lines.append(f"- {warning}")
        lines.append("")

    # 声明
    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)


def save_multi_window_consensus_report(
    output_dir: str,
    report_data: Dict[str, Any],
    consensus_data: List[Dict[str, Any]],
):
    """
    保存多窗口趋势共识报告

    Args:
        output_dir: 输出目录
        report_data: 报告元数据
        consensus_data: 共识数据列表
    """
    os.makedirs(output_dir, exist_ok=True)

    # 更新 report_data
    report_data["consensus"] = consensus_data

    # 保存 JSON
    json_path = os.path.join(output_dir, "multi_window_consensus.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    # 保存 Markdown
    md_report = generate_multi_window_consensus_report(report_data)
    md_path = os.path.join(output_dir, "multi_window_consensus.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"Multi-window consensus reports saved to: {output_dir}")
