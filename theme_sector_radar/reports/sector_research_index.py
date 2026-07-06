"""
多日 Sector Research 索引

扫描多日 sector_research.json，生成跨日索引，辅助人工复盘。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# 中文标签解释
LABEL_CN = {
    "strong_consensus": "多维共识较强",
    "trend_confirmed": "趋势确认",
    "trend_confirmed_but_strength_limited": "趋势有确认但强度有限",
    "short_term_active_unconfirmed": "短线活跃但趋势未确认",
    "rotation_candidate": "轮动观察候选",
    "defensive_watch": "防御观察",
    "conflicted": "信号分歧",
    "oversold_rebound_candidate": "弱修复观察",
    "low_signal_noise": "低信号噪声",
    "weak_continuation": "偏弱延续",
    "weak_or_avoid": "正向观察强度有限",
    "insufficient_data": "数据不足",
    "early_repair_watch": "早期修复观察",
    "data_limited_neutral": "数据有限中性",
    "defensive_stable_watch": "防御稳定观察",
}


class SectorResearchIndex:
    """
    多日 Sector Research 索引

    扫描多日 sector_research.json，生成跨日索引。
    """

    def __init__(self, report_root: str = "reports"):
        """
        初始化

        Args:
            report_root: 报告根目录
        """
        self.report_root = report_root

    def build_index(
        self,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        构建多日索引

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            索引数据
        """
        # 收集所有日报数据
        daily_data = self._collect_daily_data(start_date, end_date)

        if not daily_data:
            return {
                "report_type": "sector_research_index",
                "start_date": start_date,
                "end_date": end_date,
                "total_days": 0,
                "sector_frequency": {},
                "label_changes": [],
                "score_trends": {},
                "risk_signals": [],
                "regime_correlation": {},
                "review_template": self._generate_review_template(),
            }

        # 1. 板块出现频率
        sector_frequency = self._compute_sector_frequency(daily_data)

        # 2. 标签变化
        label_changes = self._detect_label_changes(daily_data)

        # 3. 分数趋势
        score_trends = self._compute_score_trends(daily_data)

        # 4. 风险信号
        risk_signals = self._detect_risk_signals(daily_data)

        # 5. regime 关联
        regime_correlation = self._compute_regime_correlation(daily_data)

        # 6. 复盘模板
        review_template = self._generate_review_template()

        result = {
            "report_type": "sector_research_index",
            "start_date": start_date,
            "end_date": end_date,
            "total_days": len(daily_data),
            "dates": list(daily_data.keys()),
            "sector_frequency": sector_frequency,
            "label_changes": label_changes,
            "score_trends": score_trends,
            "risk_signals": risk_signals,
            "regime_correlation": regime_correlation,
            "review_template": review_template,
        }

        return result

    def _collect_daily_data(
        self, start_date: str, end_date: str
    ) -> Dict[str, Dict[str, Any]]:
        """收集每日数据"""
        daily_data = {}
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            path = os.path.join(
                self.report_root, "sector_research", date_str, "sector_research.json"
            )
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    daily_data[date_str] = data
                except Exception:
                    pass
            current += timedelta(days=1)

        return daily_data

    def _compute_sector_frequency(
        self, daily_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """计算板块出现频率"""
        frequency = {}

        for date_str, data in daily_data.items():
            summary = data.get("daily_summary", {})
            top_names = summary.get("top_watch_names", [])

            for name in top_names:
                if name not in frequency:
                    frequency[name] = {
                        "count": 0,
                        "dates": [],
                        "labels": [],
                        "regimes": [],
                    }
                frequency[name]["count"] += 1
                frequency[name]["dates"].append(date_str)

            # 也统计所有 research_results 中的板块
            for result in data.get("research_results", []):
                name = result.get("sector_name", "")
                if name and name not in frequency:
                    frequency[name] = {
                        "count": 0,
                        "dates": [],
                        "labels": [],
                        "regimes": [],
                    }
                if name:
                    label = result.get("consensus_label", "")
                    regime = summary.get("market_regime", "")
                    if label and label not in frequency[name]["labels"]:
                        frequency[name]["labels"].append(label)
                    if regime and regime not in frequency[name]["regimes"]:
                        frequency[name]["regimes"].append(regime)

        # 按出现次数排序
        sorted_freq = dict(
            sorted(frequency.items(), key=lambda x: -x[1]["count"])
        )

        return sorted_freq

    def _detect_label_changes(
        self, daily_data: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """检测标签变化"""
        changes = []

        # 按板块跟踪标签变化
        sector_labels = {}
        for date_str in sorted(daily_data.keys()):
            data = daily_data[date_str]
            for result in data.get("research_results", []):
                name = result.get("sector_name", "")
                label = result.get("consensus_label", "")
                if name and label:
                    if name not in sector_labels:
                        sector_labels[name] = []
                    sector_labels[name].append({
                        "date": date_str,
                        "label": label,
                    })

        # 检测变化
        for name, history in sector_labels.items():
            if len(history) < 2:
                continue

            for i in range(1, len(history)):
                if history[i]["label"] != history[i - 1]["label"]:
                    changes.append({
                        "sector_name": name,
                        "from_date": history[i - 1]["date"],
                        "from_label": history[i - 1]["label"],
                        "from_label_cn": LABEL_CN.get(history[i - 1]["label"], history[i - 1]["label"]),
                        "to_date": history[i]["date"],
                        "to_label": history[i]["label"],
                        "to_label_cn": LABEL_CN.get(history[i]["label"], history[i]["label"]),
                    })

        return changes

    def _compute_score_trends(
        self, daily_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """计算分数趋势"""
        trends = {}

        for date_str in sorted(daily_data.keys()):
            data = daily_data[date_str]
            for result in data.get("research_results", []):
                name = result.get("sector_name", "")
                if not name:
                    continue

                if name not in trends:
                    trends[name] = {
                        "ranking_score": [],
                        "opportunity_score": [],
                        "confidence_score": [],
                    }

                trends[name]["ranking_score"].append({
                    "date": date_str,
                    "value": result.get("ranking_score", 0),
                })
                trends[name]["opportunity_score"].append({
                    "date": date_str,
                    "value": result.get("opportunity_score", 0),
                })
                trends[name]["confidence_score"].append({
                    "date": date_str,
                    "value": result.get("confidence_score", 0),
                })

        return trends

    def _detect_risk_signals(
        self, daily_data: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """检测风险信号"""
        signals = []

        for date_str in sorted(daily_data.keys()):
            data = daily_data[date_str]
            for result in data.get("research_results", []):
                name = result.get("sector_name", "")
                veto = result.get("veto", {})
                conflict_level = result.get("conflict_level", "none")

                if veto.get("veto_triggered", False):
                    signals.append({
                        "date": date_str,
                        "sector_name": name,
                        "signal_type": "veto",
                        "details": veto.get("veto_reasons", []),
                    })

                if conflict_level in ["high", "medium"]:
                    signals.append({
                        "date": date_str,
                        "sector_name": name,
                        "signal_type": "conflict",
                        "details": [f"conflict_level={conflict_level}"],
                    })

        return signals

    def _compute_regime_correlation(
        self, daily_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, List[str]]]:
        """计算 regime 关联"""
        correlation = {}

        for date_str, data in daily_data.items():
            summary = data.get("daily_summary", {})
            regime = summary.get("market_regime", "unknown")

            if regime not in correlation:
                correlation[regime] = {"sectors": [], "dates": []}

            correlation[regime]["dates"].append(date_str)

            for result in data.get("research_results", []):
                name = result.get("sector_name", "")
                if name and name not in correlation[regime]["sectors"]:
                    correlation[regime]["sectors"].append(name)

        return correlation

    def _generate_review_template(self) -> Dict[str, Any]:
        """生成复盘模板"""
        return {
            "sections": [
                {
                    "name": "市场环境回顾",
                    "questions": [
                        "今日 market_regime 是什么？",
                        "与昨日相比 regime 是否变化？",
                        "市场温度和广度如何？",
                    ],
                },
                {
                    "name": "重点板块跟踪",
                    "questions": [
                        "哪些板块连续出现在今日重点观察中？",
                        "这些板块的 ranking_score 趋势如何？",
                        "是否有新的观察候选？",
                    ],
                },
                {
                    "name": "标签变化复盘",
                    "questions": [
                        "哪些板块标签发生变化？",
                        "变化方向是否合理？",
                        "是否有误判需要记录？",
                    ],
                },
                {
                    "name": "风险信号复盘",
                    "questions": [
                        "哪些板块触发了 veto？",
                        "是否有新的冲突信号？",
                        "风险是否在可控范围内？",
                    ],
                },
                {
                    "name": "下一交易日准备",
                    "questions": [
                        "哪些板块需要继续跟踪？",
                        "是否有需要调整观察权重的板块？",
                        "市场环境是否需要调整策略？",
                    ],
                },
            ],
        }


def save_research_index(
    output_dir: str,
    index_data: Dict[str, Any],
):
    """保存研究索引"""
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "research_index.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON index saved: {json_path}")

    # 生成 Markdown
    md_report = generate_research_index_markdown(index_data)
    md_path = os.path.join(output_dir, "research_index.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown index saved: {md_path}")


def generate_research_index_markdown(index_data: Dict[str, Any]) -> str:
    """生成研究索引 Markdown"""
    lines = []

    lines.append("# 多日研究索引")
    lines.append("")
    lines.append(f"- **日期范围**: {index_data.get('start_date', '')} ~ {index_data.get('end_date', '')}")
    lines.append(f"- **覆盖天数**: {index_data.get('total_days', 0)}")
    lines.append("")

    # 板块出现频率
    lines.append("## 板块出现频率")
    lines.append("")
    lines.append("| 板块 | 出现天数 | 标签历史 | Regime 历史 |")
    lines.append("|------|----------|----------|-------------|")

    freq = index_data.get("sector_frequency", {})
    for name, info in list(freq.items())[:20]:
        labels = ", ".join(info.get("labels", [])[:3])
        regimes = ", ".join(info.get("regimes", [])[:3])
        lines.append(f"| {name} | {info.get('count', 0)} | {labels} | {regimes} |")
    lines.append("")

    # 标签变化
    changes = index_data.get("label_changes", [])
    if changes:
        lines.append("## 标签变化")
        lines.append("")
        lines.append("| 板块 | 日期 | 从标签 | 到标签 |")
        lines.append("|------|------|--------|--------|")
        for c in changes[:20]:
            lines.append(
                f"| {c.get('sector_name', '')} | {c.get('to_date', '')} | "
                f"{c.get('from_label_cn', '')} | {c.get('to_label_cn', '')} |"
            )
        lines.append("")

    # 风险信号
    signals = index_data.get("risk_signals", [])
    if signals:
        lines.append("## 风险信号")
        lines.append("")
        lines.append("| 日期 | 板块 | 类型 | 详情 |")
        lines.append("|------|------|------|------|")
        for s in signals[:20]:
            details = "; ".join(s.get("details", [])[:2])
            lines.append(
                f"| {s.get('date', '')} | {s.get('sector_name', '')} | "
                f"{s.get('signal_type', '')} | {details[:50]} |"
            )
        lines.append("")

    # regime 关联
    regime_corr = index_data.get("regime_correlation", {})
    if regime_corr:
        lines.append("## Regime 关联")
        lines.append("")
        lines.append("| Regime | 覆盖天数 | 板块数 |")
        lines.append("|--------|----------|--------|")
        for regime, info in regime_corr.items():
            lines.append(
                f"| {regime} | {len(info.get('dates', []))} | {len(info.get('sectors', []))} |"
            )
        lines.append("")

    # 复盘模板
    template = index_data.get("review_template", {})
    sections = template.get("sections", [])
    if sections:
        lines.append("## 人工复盘模板")
        lines.append("")
        for section in sections:
            lines.append(f"### {section.get('name', '')}")
            lines.append("")
            for q in section.get("questions", []):
                lines.append(f"- [ ] {q}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本索引由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)
