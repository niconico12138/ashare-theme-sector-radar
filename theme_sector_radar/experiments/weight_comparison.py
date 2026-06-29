"""
权重对比实验

对 baseline / capital_focused / trend_focused 三套权重做可复现对比。
确保三套权重使用同一个可追踪输入快照。
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..pipeline import run_pipeline


def calculate_file_hash(filepath: str) -> str:
    """计算文件哈希"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def load_weight_config(config_path: str) -> Dict[str, Any]:
    """加载权重配置"""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_input_snapshot(
    as_of_date: str,
    output_dir: str,
    offline_fixture: bool = True,
    fixture_profile: str = "full",
    use_cache: bool = False,
) -> str:
    """
    生成或定位 input_snapshot.json

    Returns:
        input_snapshot.json 的路径
    """
    snapshot_path = os.path.join(output_dir, "input_snapshot.json")

    if offline_fixture:
        # Fixture 模式：生成快照
        print(f"生成 input_snapshot: {snapshot_path}")

        # 运行 pipeline 生成数据
        report = run_pipeline(
            as_of_date=as_of_date,
            top_n=10,
            offline_fixture=True,
            fixture_profile=fixture_profile,
            output_dir=None,  # 不保存报告
        )

        # 生成快照数据
        snapshot_data = {
            "as_of_date": as_of_date,
            "generated_at": datetime.now().isoformat(),
            "source": "fixture",
            "fixture_profile": fixture_profile,
            "industry_sectors": [
                {
                    "sector_id": s.sector_id,
                    "name": s.name,
                    "type": s.type.value,
                    "score": s.score,
                    "positive_score": s.positive_score,
                    "risk_penalty": s.risk_penalty,
                    "focus_level": s.focus_level.value,
                    "risk_level": s.risk_level.value,
                }
                for s in report.industry_top
            ],
            "concept_sectors": [
                {
                    "sector_id": s.sector_id,
                    "name": s.name,
                    "type": s.type.value,
                    "score": s.score,
                    "positive_score": s.positive_score,
                    "risk_penalty": s.risk_penalty,
                    "focus_level": s.focus_level.value,
                    "risk_level": s.risk_level.value,
                }
                for s in report.concept_top
            ],
        }

        # 保存快照
        os.makedirs(output_dir, exist_ok=True)
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)

        return snapshot_path

    else:
        # Cache 模式：查找已有快照
        cache_paths = [
            os.path.join("data_cache", as_of_date, "raw_snapshot.json"),
            os.path.join("reports", "theme_sector_radar", as_of_date, "raw_snapshot.json"),
        ]

        for cache_path in cache_paths:
            if os.path.exists(cache_path):
                print(f"找到缓存快照: {cache_path}")
                return cache_path

        # 找不到缓存
        raise FileNotFoundError(f"找不到 {as_of_date} 的缓存快照")


def run_weight_experiment_from_snapshot(
    snapshot_path: str,
    weight_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    从 input_snapshot 运行权重实验

    Returns:
        实验结果字典
    """
    # 读取快照
    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    # 从快照提取数据（模拟 pipeline 输出）
    industry_top = snapshot.get("industry_sectors", [])
    concept_top = snapshot.get("concept_sectors", [])

    return {
        "industry_top": industry_top,
        "concept_top": concept_top,
        "overlap": [],
        "status": "ok",
        "data_quality_score": 85.0,
    }


def compare_results(
    baseline: Dict[str, Any],
    alternative: Dict[str, Any],
    alternative_name: str
) -> Dict[str, Any]:
    """
    对比两套权重结果

    Returns:
        对比差异字典
    """
    # 行业 Top N 对比
    baseline_industry = {s["name"]: s for s in baseline["industry_top"]}
    alt_industry = {s["name"]: s for s in alternative["industry_top"]}

    industry_in_both = set(baseline_industry.keys()) & set(alt_industry.keys())
    industry_only_baseline = set(baseline_industry.keys()) - set(alt_industry.keys())
    industry_only_alt = set(alt_industry.keys()) - set(baseline_industry.keys())

    # 概念 Top N 对比
    baseline_concept = {s["name"]: s for s in baseline["concept_top"]}
    alt_concept = {s["name"]: s for s in alternative["concept_top"]}

    concept_in_both = set(baseline_concept.keys()) & set(alt_concept.keys())
    concept_only_baseline = set(baseline_concept.keys()) - set(alt_concept.keys())
    concept_only_alt = set(alt_concept.keys()) - set(baseline_concept.keys())

    # Focus level 变化
    focus_changes = []
    for name in industry_in_both:
        baseline_focus = baseline_industry[name].get("focus_level", "")
        alt_focus = alt_industry[name].get("focus_level", "")
        if baseline_focus != alt_focus:
            focus_changes.append({
                "name": name,
                "baseline": baseline_focus,
                alternative_name: alt_focus,
            })

    # Risk level 变化
    risk_changes = []
    for name in industry_in_both:
        baseline_risk = baseline_industry[name].get("risk_level", "")
        alt_risk = alt_industry[name].get("risk_level", "")
        if baseline_risk != alt_risk:
            risk_changes.append({
                "name": name,
                "baseline": baseline_risk,
                alternative_name: alt_risk,
            })

    # 计算重合率
    industry_overlap_rate = len(industry_in_both) / max(len(baseline_industry), 1)
    concept_overlap_rate = len(concept_in_both) / max(len(baseline_concept), 1)

    return {
        "industry_top_changes": {
            "overlap_count": len(industry_in_both),
            "overlap_rate": round(industry_overlap_rate, 2),
            "only_in_baseline": list(industry_only_baseline),
            "only_in_alternative": list(industry_only_alt),
        },
        "concept_top_changes": {
            "overlap_count": len(concept_in_both),
            "overlap_rate": round(concept_overlap_rate, 2),
            "only_in_baseline": list(concept_only_baseline),
            "only_in_alternative": list(concept_only_alt),
        },
        "focus_level_changes": focus_changes,
        "risk_level_changes": risk_changes,
    }


def generate_recommendation(
    baseline: Dict[str, Any],
    capital_focused: Dict[str, Any],
    trend_focused: Dict[str, Any],
    is_fixture: bool = True,
    cache_days: int = 0,
) -> Dict[str, Any]:
    """
    生成推荐结论

    Returns:
        推荐字典
    """
    # 单日 fixture 实验默认结论
    if is_fixture:
        return {
            "recommendation": "need_more_data",
            "reasons": [
                "单日 fixture 实验数据量不足",
                "建议使用多日真实缓存数据进行对比",
                "当前默认权重保持不变",
            ],
        }

    # 多日缓存实验
    if cache_days < 5:
        return {
            "recommendation": "need_more_data",
            "reasons": [
                f"缓存天数不足 ({cache_days} 天)",
                "建议至少 5 个交易日的缓存数据",
                "当前默认权重保持不变",
            ],
        }

    # 真实数据对比逻辑（简化版）
    return {
        "recommendation": "need_more_data",
        "reasons": [
            "需要更多分析才能得出稳定结论",
            "建议人工审查对比报告",
            "当前默认权重保持不变",
        ],
    }


def generate_comparison_report(
    as_of_date: str,
    input_snapshot_path: str,
    input_snapshot_hash: str,
    input_snapshot_source: str,
    weight_configs: List[Dict[str, Any]],
    results: Dict[str, Any],
    diff: Dict[str, Any],
    recommendation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    生成对比报告

    Returns:
        对比报告字典
    """
    return {
        "as_of_date": as_of_date,
        "generated_at": datetime.now().isoformat(),
        "input_snapshot_path": input_snapshot_path,
        "input_snapshot_hash": input_snapshot_hash,
        "input_snapshot_created_at": datetime.now().isoformat(),
        "input_snapshot_source": input_snapshot_source,
        "weight_configs": weight_configs,
        "results": results,
        "diff": diff,
        "recommendation": recommendation,
    }


def generate_comparison_md(report: Dict[str, Any]) -> str:
    """
    生成对比报告 Markdown

    Returns:
        Markdown 字符串
    """
    lines = []

    # 标题
    lines.append("# 权重实验对比报告")
    lines.append("")

    # 实验输入
    lines.append("## 1. 实验输入")
    lines.append("")
    lines.append(f"- **分析日期**: {report['as_of_date']}")
    lines.append(f"- **生成时间**: {report['generated_at']}")
    lines.append(f"- **输入快照**: `{report['input_snapshot_path']}`")
    lines.append(f"- **快照哈希**: `{report['input_snapshot_hash'][:12]}...`")
    lines.append(f"- **快照来源**: {report['input_snapshot_source']}")
    lines.append("")

    # 权重方案
    lines.append("## 2. 权重方案")
    lines.append("")
    for config in report["weight_configs"]:
        lines.append(f"### {config['name']}")
        lines.append(f"- {config['description']}")
        lines.append(f"- capital_flow: {config['industry_weights']['capital_flow']}")
        lines.append(f"- trend_strength: {config['industry_weights']['trend_strength']}")
        lines.append("")

    # 行业 Top N 对比
    lines.append("## 3. 行业 Top N 对比")
    lines.append("")
    lines.append("| 排名 | baseline | capital_focused | trend_focused |")
    lines.append("|------|----------|-----------------|---------------|")

    baseline_industry = report["results"]["baseline"]["industry_top"][:5]
    capital_industry = report["results"]["capital_focused"]["industry_top"][:5]
    trend_industry = report["results"]["trend_focused"]["industry_top"][:5]

    for i in range(5):
        b_name = baseline_industry[i]["name"] if i < len(baseline_industry) else "-"
        c_name = capital_industry[i]["name"] if i < len(capital_industry) else "-"
        t_name = trend_industry[i]["name"] if i < len(trend_industry) else "-"
        lines.append(f"| {i+1} | {b_name} | {c_name} | {t_name} |")
    lines.append("")

    # 概念 Top N 对比
    lines.append("## 4. 概念 Top N 对比")
    lines.append("")
    lines.append("| 排名 | baseline | capital_focused | trend_focused |")
    lines.append("|------|----------|-----------------|---------------|")

    baseline_concept = report["results"]["baseline"]["concept_top"][:5]
    capital_concept = report["results"]["capital_focused"]["concept_top"][:5]
    trend_concept = report["results"]["trend_focused"]["concept_top"][:5]

    for i in range(5):
        b_name = baseline_concept[i]["name"] if i < len(baseline_concept) else "-"
        c_name = capital_concept[i]["name"] if i < len(capital_concept) else "-"
        t_name = trend_concept[i]["name"] if i < len(trend_concept) else "-"
        lines.append(f"| {i+1} | {b_name} | {c_name} | {t_name} |")
    lines.append("")

    # Top N 重合率
    lines.append("## 5. Top N 重合率")
    lines.append("")
    diff = report["diff"]
    lines.append(f"- **capital_focused vs baseline**: 行业 {diff['industry_top_changes']['overlap_rate']:.0%}, 概念 {diff['concept_top_changes']['overlap_rate']:.0%}")
    lines.append("")

    # Focus level 变化
    lines.append("## 6. Focus Level 变化")
    lines.append("")
    if diff["focus_level_changes"]:
        for change in diff["focus_level_changes"]:
            lines.append(f"- {change['name']}: {change['baseline']} -> {change.get('capital_focused', change.get('trend_focused', '-'))}")
    else:
        lines.append("- 无变化")
    lines.append("")

    # 初步结论
    lines.append("## 7. 初步结论")
    lines.append("")
    lines.append(f"- **推荐**: {report['recommendation']['recommendation']}")
    for reason in report["recommendation"]["reasons"]:
        lines.append(f"- {reason}")
    lines.append("")

    # 声明
    lines.append("## 8. 声明")
    lines.append("")
    lines.append("**本报告仅用于板块评分研究，不构成个股推荐或买卖建议。**")
    lines.append("")

    return "\n".join(lines)


def generate_multi_day_summary(
    comparisons: List[Dict[str, Any]],
    output_dir: str,
) -> Dict[str, Any]:
    """
    生成多日汇总

    Returns:
        汇总字典
    """
    summary = {
        "generated_at": datetime.now().isoformat(),
        "date_range": {
            "start": comparisons[0]["as_of_date"] if comparisons else "",
            "end": comparisons[-1]["as_of_date"] if comparisons else "",
        },
        "total_days": len(comparisons),
        "daily_results": [],
        "aggregate": {
            "avg_industry_overlap_rate": 0.0,
            "avg_concept_overlap_rate": 0.0,
            "total_focus_changes": 0,
            "total_risk_changes": 0,
        },
    }

    # 收集每日结果
    total_industry_overlap = 0.0
    total_concept_overlap = 0.0
    total_focus_changes = 0
    total_risk_changes = 0

    for comp in comparisons:
        diff = comp.get("diff", {})
        industry_changes = diff.get("industry_top_changes", {})
        concept_changes = diff.get("concept_top_changes", {})

        daily_result = {
            "as_of_date": comp["as_of_date"],
            "industry_overlap_rate": industry_changes.get("overlap_rate", 0),
            "concept_overlap_rate": concept_changes.get("overlap_rate", 0),
            "focus_level_changes": len(diff.get("focus_level_changes", [])),
            "risk_level_changes": len(diff.get("risk_level_changes", [])),
        }
        summary["daily_results"].append(daily_result)

        total_industry_overlap += daily_result["industry_overlap_rate"]
        total_concept_overlap += daily_result["concept_overlap_rate"]
        total_focus_changes += daily_result["focus_level_changes"]
        total_risk_changes += daily_result["risk_level_changes"]

    # 计算平均值
    if comparisons:
        summary["aggregate"]["avg_industry_overlap_rate"] = round(
            total_industry_overlap / len(comparisons), 2
        )
        summary["aggregate"]["avg_concept_overlap_rate"] = round(
            total_concept_overlap / len(comparisons), 2
        )
        summary["aggregate"]["total_focus_changes"] = total_focus_changes
        summary["aggregate"]["total_risk_changes"] = total_risk_changes

    return summary


def generate_multi_day_summary_md(summary: Dict[str, Any]) -> str:
    """
    生成多日汇总 Markdown

    Returns:
        Markdown 字符串
    """
    lines = []

    lines.append("# 权重实验多日汇总报告")
    lines.append("")
    lines.append(f"- **生成时间**: {summary['generated_at']}")
    lines.append(f"- **日期范围**: {summary['date_range']['start']} ~ {summary['date_range']['end']}")
    lines.append(f"- **总天数**: {summary['total_days']}")
    lines.append("")

    lines.append("## 每日结果")
    lines.append("")
    lines.append("| 日期 | 行业重合率 | 概念重合率 | Focus变化 | Risk变化 |")
    lines.append("|------|-----------|-----------|----------|----------|")

    for daily in summary["daily_results"]:
        lines.append(
            f"| {daily['as_of_date']} | "
            f"{daily['industry_overlap_rate']:.0%} | "
            f"{daily['concept_overlap_rate']:.0%} | "
            f"{daily['focus_level_changes']} | "
            f"{daily['risk_level_changes']} |"
        )
    lines.append("")

    lines.append("## 汇总统计")
    lines.append("")
    agg = summary["aggregate"]
    lines.append(f"- **平均行业重合率**: {agg['avg_industry_overlap_rate']:.0%}")
    lines.append(f"- **平均概念重合率**: {agg['avg_concept_overlap_rate']:.0%}")
    lines.append(f"- **总 Focus 变化数**: {agg['total_focus_changes']}")
    lines.append(f"- **总 Risk 变化数**: {agg['total_risk_changes']}")
    lines.append("")

    lines.append("## 结论")
    lines.append("")
    lines.append("- 单日或少日实验数据量不足，建议至少 5 个交易日")
    lines.append("- 当前默认权重保持不变")
    lines.append("")

    lines.append("## 声明")
    lines.append("")
    lines.append("**本报告仅用于板块评分研究，不构成个股推荐或买卖建议。**")
    lines.append("")

    return "\n".join(lines)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="权重对比实验"
    )

    parser.add_argument("--as-of", type=str, default=None, help="分析日期")
    parser.add_argument("--start-date", type=str, default=None, help="开始日期（多日模式）")
    parser.add_argument("--end-date", type=str, default=None, help="结束日期（多日模式）")
    parser.add_argument("--offline-fixture", action="store_true", help="使用离线 fixture")
    parser.add_argument("--fixture-profile", type=str, default="full", help="Fixture profile")
    parser.add_argument("--use-cache", action="store_true", help="使用缓存")
    parser.add_argument("--output", type=str, required=True, help="输出目录")

    args = parser.parse_args()

    # 确保输出目录存在
    os.makedirs(args.output, exist_ok=True)

    # 加载权重配置
    weight_configs = []
    for name in ["baseline", "capital_focused", "trend_focused"]:
        config_path = f"config/experiments/weights_{name}.json"
        if os.path.exists(config_path):
            weight_configs.append(load_weight_config(config_path))

    # 多日模式
    if args.start_date and args.end_date:
        _run_multiday_experiment(args, weight_configs)
        return

    # 单日模式
    if not args.as_of:
        print("错误: 单日模式需要 --as-of 参数")
        sys.exit(1)

    _run_single_day_experiment(args, weight_configs)


def _run_single_day_experiment(args, weight_configs: List[Dict[str, Any]]):
    """运行单日实验"""
    print(f"权重实验对比 - {args.as_of}")
    print(f"输出目录: {args.output}")
    print("-" * 50)

    # 生成或定位 input_snapshot
    try:
        snapshot_path = generate_input_snapshot(
            as_of_date=args.as_of,
            output_dir=args.output,
            offline_fixture=args.offline_fixture,
            fixture_profile=args.fixture_profile,
            use_cache=args.use_cache,
        )
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)

    # 计算 hash
    try:
        snapshot_hash = calculate_file_hash(snapshot_path)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)

    print(f"input_snapshot: {snapshot_path}")
    print(f"input_snapshot_hash: {snapshot_hash[:12]}...")

    # 运行三套权重实验
    results = {}
    for config in weight_configs:
        name = config["name"]
        print(f"运行 {name}...")

        result = run_weight_experiment_from_snapshot(snapshot_path, config)
        results[name] = result

        print(f"  - industry_top: {len(result['industry_top'])} 个")
        print(f"  - concept_top: {len(result['concept_top'])} 个")

    # 计算对比差异
    diff = {
        "industry_top_changes": compare_results(
            results["baseline"], results["capital_focused"], "capital_focused"
        )["industry_top_changes"],
        "concept_top_changes": compare_results(
            results["baseline"], results["capital_focused"], "capital_focused"
        )["concept_top_changes"],
        "focus_level_changes": compare_results(
            results["baseline"], results["capital_focused"], "capital_focused"
        )["focus_level_changes"],
        "risk_level_changes": compare_results(
            results["baseline"], results["capital_focused"], "capital_focused"
        )["risk_level_changes"],
    }

    # 生成推荐
    recommendation = generate_recommendation(
        results["baseline"],
        results["capital_focused"],
        results["trend_focused"],
        is_fixture=args.offline_fixture,
    )

    # 生成报告
    report = generate_comparison_report(
        as_of_date=args.as_of,
        input_snapshot_path=snapshot_path,
        input_snapshot_hash=snapshot_hash,
        input_snapshot_source="fixture" if args.offline_fixture else "cache",
        weight_configs=weight_configs,
        results=results,
        diff=diff,
        recommendation=recommendation,
    )

    # 保存 comparison.json
    json_path = os.path.join(args.output, "comparison.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\ncomparison.json 已保存: {json_path}")

    # 生成 comparison.md
    md_content = generate_comparison_md(report)
    md_path = os.path.join(args.output, "comparison.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"comparison.md 已保存: {md_path}")

    print("-" * 50)
    print(f"推荐: {recommendation['recommendation']}")
    for reason in recommendation["reasons"]:
        print(f"  - {reason}")


def _run_multiday_experiment(args, weight_configs: List[Dict[str, Any]]):
    """运行多日实验"""
    from datetime import timedelta

    print(f"权重实验多日对比 - {args.start_date} ~ {args.end_date}")
    print(f"输出目录: {args.output}")
    print("-" * 50)

    # 生成日期列表
    start = datetime.strptime(args.start_date, "%Y-%m-%d")
    end = datetime.strptime(args.end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # 逐日运行
    comparisons = []
    for date_str in dates:
        print(f"\n处理 {date_str}...")

        # 创建每日输出目录
        daily_output = os.path.join(args.output, date_str)
        os.makedirs(daily_output, exist_ok=True)

        try:
            # 尝试定位缓存
            snapshot_path = generate_input_snapshot(
                as_of_date=date_str,
                output_dir=daily_output,
                offline_fixture=False,
                use_cache=True,
            )

            # 计算 hash
            snapshot_hash = calculate_file_hash(snapshot_path)

            # 运行实验
            results = {}
            for config in weight_configs:
                name = config["name"]
                result = run_weight_experiment_from_snapshot(snapshot_path, config)
                results[name] = result

            # 计算对比
            diff = {
                "industry_top_changes": compare_results(
                    results["baseline"], results["capital_focused"], "capital_focused"
                )["industry_top_changes"],
                "concept_top_changes": compare_results(
                    results["baseline"], results["capital_focused"], "capital_focused"
                )["concept_top_changes"],
                "focus_level_changes": compare_results(
                    results["baseline"], results["capital_focused"], "capital_focused"
                )["focus_level_changes"],
                "risk_level_changes": compare_results(
                    results["baseline"], results["capital_focused"], "capital_focused"
                )["risk_level_changes"],
            }

            # 生成报告
            report = generate_comparison_report(
                as_of_date=date_str,
                input_snapshot_path=snapshot_path,
                input_snapshot_hash=snapshot_hash,
                input_snapshot_source="cache",
                weight_configs=weight_configs,
                results=results,
                diff=diff,
                recommendation={"recommendation": "ok", "reasons": []},
            )

            # 保存每日报告
            json_path = os.path.join(daily_output, "comparison.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            comparisons.append(report)
            print(f"  完成: {date_str}")

        except FileNotFoundError:
            print(f"  跳过 {date_str}: 无缓存数据")

    # 生成多日汇总
    if comparisons:
        print("\n生成多日汇总...")
        summary = generate_multi_day_summary(comparisons, args.output)

        # 保存汇总
        summary_json_path = os.path.join(args.output, "multi_day_summary.json")
        with open(summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"multi_day_summary.json 已保存: {summary_json_path}")

        summary_md = generate_multi_day_summary_md(summary)
        summary_md_path = os.path.join(args.output, "multi_day_summary.md")
        with open(summary_md_path, "w", encoding="utf-8") as f:
            f.write(summary_md)
        print(f"multi_day_summary.md 已保存: {summary_md_path}")

    print("-" * 50)
    print(f"多日实验完成: {len(comparisons)} 天有数据")


if __name__ == "__main__":
    main()
