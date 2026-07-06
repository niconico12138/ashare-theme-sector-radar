"""
板块批量评分报告生成。

生成批量历史评分的汇总报告和时间序列报告。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List


TREND_LEVEL_CN = {
    "strong_watch": "重点观察",
    "watch": "观察",
    "neutral": "中性",
    "cooling": "降温",
    "avoid": "偏弱",
}

BURST_LEVEL_CN = {
    "burst_hot": "短线强势",
    "burst_watch": "短线活跃",
    "burst_neutral": "短线中性",
    "burst_fading": "短线降温",
    "burst_avoid": "短线偏弱",
}


def _trend_level_cn(score: Dict[str, Any]) -> str:
    level = score.get("trend_level") or score.get("selection_level") or ""
    return score.get("trend_level_cn") or score.get("selection_level_cn") or TREND_LEVEL_CN.get(level, level)


def _burst_level_cn(score: Dict[str, Any]) -> str:
    level = score.get("burst_level", "")
    return score.get("burst_level_cn") or BURST_LEVEL_CN.get(level, level)


def generate_batch_summary(
    start_date: str,
    end_date: str,
    sector_type: str,
    score_mode: str,
    benchmark: str,
    total_dates: int,
    completed_dates: List[str],
    skipped_dates: List[Dict[str, str]],
    failed_dates: List[Dict[str, str]],
    output_dirs: List[str],
    warnings: List[str] = None,
) -> Dict[str, Any]:
    """生成批量评分汇总。"""
    return {
        "start_date": start_date,
        "end_date": end_date,
        "sector_type": sector_type,
        "score_mode": score_mode,
        "benchmark": benchmark,
        "total_dates": total_dates,
        "completed_dates": len(completed_dates),
        "skipped_dates": skipped_dates,
        "failed_dates": failed_dates,
        "output_dirs": output_dirs,
        "warnings": warnings or [],
        "generated_at": datetime.now().isoformat(),
    }


def generate_batch_summary_markdown(
    batch_summary: Dict[str, Any],
    daily_scores: Dict[str, Dict[str, Any]],
) -> str:
    """生成批量评分汇总 Markdown 报告。"""
    lines = []

    lines.append("# 板块批量评分汇总")
    lines.append("")
    lines.append(f"**日期范围**: {batch_summary['start_date']} ~ {batch_summary['end_date']}")
    lines.append(f"**板块类型**: {batch_summary['sector_type']}")
    lines.append(f"**评分模式**: {batch_summary['score_mode']}")
    lines.append(f"**基准**: {batch_summary['benchmark']}")
    lines.append(f"**生成时间**: {batch_summary['generated_at']}")
    lines.append("")
    lines.append("> **说明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股决策依据或自动交易指令。")
    lines.append("")

    lines.append("## 批量评分概览")
    lines.append("")
    lines.append(f"- **总日期数**: {batch_summary['total_dates']}")
    lines.append(f"- **完成日期数**: {batch_summary['completed_dates']}")
    lines.append(f"- **跳过日期数**: {len(batch_summary['skipped_dates'])}")
    lines.append(f"- **失败日期数**: {len(batch_summary['failed_dates'])}")
    lines.append("")

    if batch_summary['skipped_dates']:
        lines.append("## 跳过日期")
        lines.append("")
        lines.append("| 日期 | 原因 |")
        lines.append("|------|------|")
        for item in batch_summary['skipped_dates']:
            lines.append(f"| {item['date']} | {item['reason']} |")
        lines.append("")

    if batch_summary['failed_dates']:
        lines.append("## 失败日期")
        lines.append("")
        lines.append("| 日期 | 原因 |")
        lines.append("|------|------|")
        for item in batch_summary['failed_dates']:
            lines.append(f"| {item['date']} | {item['reason']} |")
        lines.append("")

    if batch_summary.get('warnings'):
        lines.append("## 警告")
        lines.append("")
        for warning in batch_summary['warnings']:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## 每日趋势持续 Top 3")
    lines.append("")
    for date_str in sorted(daily_scores.keys()):
        scores = daily_scores[date_str].get("scores", [])
        if not scores:
            continue
        lines.append(f"### {date_str}")
        lines.append("")
        lines.append("| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | Profile |")
        lines.append("|------|------|--------|----------|--------|---------|")
        for i, score in enumerate(scores[:3], 1):
            interpretation = score.get("score_interpretation", {})
            profile = interpretation.get("profile", "N/A")
            lines.append(
                f"| {i} | {score.get('sector_name', '')} | "
                f"{score.get('trend_continuation_score', 0):.1f} | "
                f"{_trend_level_cn(score)} | "
                f"{score.get('short_term_burst_score', 0):.1f} | "
                f"{profile} |"
            )
        lines.append("")

    lines.append("## 每日短线爆发 Top 3")
    lines.append("")
    for date_str in sorted(daily_scores.keys()):
        scores = daily_scores[date_str].get("scores", [])
        if not scores:
            continue
        burst_sorted = sorted(scores, key=lambda x: x.get("short_term_burst_score", 0), reverse=True)
        lines.append(f"### {date_str}")
        lines.append("")
        lines.append("| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | Profile |")
        lines.append("|------|------|--------|----------|--------|---------|")
        for i, score in enumerate(burst_sorted[:3], 1):
            interpretation = score.get("score_interpretation", {})
            profile = interpretation.get("profile", "N/A")
            lines.append(
                f"| {i} | {score.get('sector_name', '')} | "
                f"{score.get('short_term_burst_score', 0):.1f} | "
                f"{_burst_level_cn(score)} | "
                f"{score.get('trend_continuation_score', 0):.1f} | "
                f"{profile} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块强弱筛选和研究复盘，不作为个股决策依据或自动交易指令。*")
    return "\n".join(lines)


def generate_timeseries_data(
    daily_scores: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """生成按板块聚合的时间序列数据。"""
    sector_data = {}

    for date_str in sorted(daily_scores.keys()):
        scores = daily_scores[date_str].get("scores", [])
        for i, score in enumerate(scores):
            sector_name = score.get("sector_name", "")
            if not sector_name:
                continue
            if sector_name not in sector_data:
                sector_data[sector_name] = {
                    "sector_name": sector_name,
                    "sector_type": score.get("sector_type", "industry"),
                    "records": [],
                }
            interpretation = score.get("score_interpretation", {})
            sector_data[sector_name]["records"].append({
                "date": date_str,
                "trend_continuation_score": score.get("trend_continuation_score", 0),
                "trend_level": score.get("trend_level", ""),
                "trend_level_cn": _trend_level_cn(score),
                "short_term_burst_score": score.get("short_term_burst_score", 0),
                "burst_level": score.get("burst_level", ""),
                "burst_level_cn": _burst_level_cn(score),
                "profile": interpretation.get("profile", ""),
                "rank_trend": i + 1,
                "history_source": score.get("history_source", ""),
                "benchmark_mode": score.get("benchmark_mode", ""),
            })

    result = []
    for sector_name, data in sector_data.items():
        records = data["records"]
        if records:
            trend_scores = [r["trend_continuation_score"] for r in records]
            burst_scores = [r["short_term_burst_score"] for r in records]
            trend_level_counts = {}
            burst_level_counts = {}
            for r in records:
                trend_level = r.get("trend_level", "")
                burst_level = r.get("burst_level", "")
                trend_level_counts[trend_level] = trend_level_counts.get(trend_level, 0) + 1
                burst_level_counts[burst_level] = burst_level_counts.get(burst_level, 0) + 1
            summary = {
                "days": len(records),
                "avg_trend_score": round(sum(trend_scores) / len(trend_scores), 2),
                "avg_burst_score": round(sum(burst_scores) / len(burst_scores), 2),
                "best_trend_score": round(max(trend_scores), 2),
                "best_burst_score": round(max(burst_scores), 2),
                "trend_level_counts": trend_level_counts,
                "burst_level_counts": burst_level_counts,
            }
        else:
            summary = {
                "days": 0,
                "avg_trend_score": 0,
                "avg_burst_score": 0,
                "best_trend_score": 0,
                "best_burst_score": 0,
                "trend_level_counts": {},
                "burst_level_counts": {},
            }
        result.append({
            "sector_name": data["sector_name"],
            "sector_type": data["sector_type"],
            "records": records,
            "summary": summary,
        })

    result.sort(key=lambda x: x["summary"]["avg_trend_score"], reverse=True)
    return result


def generate_timeseries_markdown(
    timeseries_data: List[Dict[str, Any]],
) -> str:
    """生成时间序列 Markdown 报告。"""
    lines = []
    lines.append("# 板块分数时间序列")
    lines.append("")
    lines.append("> **说明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股决策依据或自动交易指令。")
    lines.append("")
    lines.append("## 板块分数时间序列")
    lines.append("")

    for data in timeseries_data[:10]:
        sector_name = data["sector_name"]
        records = data["records"]
        summary = data["summary"]
        lines.append(f"### {sector_name}")
        lines.append("")
        lines.append(f"- **数据天数**: {summary['days']}")
        lines.append(f"- **平均趋势分**: {summary['avg_trend_score']:.1f}")
        lines.append(f"- **平均短线分**: {summary['avg_burst_score']:.1f}")
        lines.append(f"- **最佳趋势分**: {summary['best_trend_score']:.1f}")
        lines.append(f"- **最佳短线分**: {summary['best_burst_score']:.1f}")
        lines.append("")
        if records:
            lines.append("| 日期 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile | 趋势排名 |")
            lines.append("|------|--------|----------|--------|----------|---------|----------|")
            for r in records:
                lines.append(
                    f"| {r['date']} | "
                    f"{r['trend_continuation_score']:.1f} | "
                    f"{r.get('trend_level_cn', r['trend_level'])} | "
                    f"{r['short_term_burst_score']:.1f} | "
                    f"{r.get('burst_level_cn', r['burst_level'])} | "
                    f"{r['profile']} | "
                    f"{r['rank_trend']} |"
                )
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块强弱筛选和研究复盘，不作为个股决策依据或自动交易指令。*")
    return "\n".join(lines)


def save_batch_reports(
    output_dir: str,
    batch_summary: Dict[str, Any],
    daily_scores: Dict[str, Dict[str, Any]],
    timeseries_data: List[Dict[str, Any]],
):
    """保存批量报告。"""
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "batch_summary.json"), "w", encoding="utf-8") as f:
        json.dump(batch_summary, f, ensure_ascii=False, indent=2)

    md_report = generate_batch_summary_markdown(batch_summary, daily_scores)
    with open(os.path.join(output_dir, "batch_summary.md"), "w", encoding="utf-8") as f:
        f.write(md_report)

    with open(os.path.join(output_dir, "sector_score_timeseries.json"), "w", encoding="utf-8") as f:
        json.dump(timeseries_data, f, ensure_ascii=False, indent=2)

    ts_md_report = generate_timeseries_markdown(timeseries_data)
    with open(os.path.join(output_dir, "sector_score_timeseries.md"), "w", encoding="utf-8") as f:
        f.write(ts_md_report)

    print(f"Batch reports saved to: {output_dir}")
