"""
持续性信号研究

研究多日持续性信号是否对后续表现有解释力。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class PersistenceSignalResearch:
    """
    持续性信号研究

    研究多日持续性信号是否对后续表现有解释力。
    """

    def __init__(self, history_root: str = "data_cache/sector_history"):
        self.history_root = history_root

    def run_analysis(
        self,
        start_date: str,
        end_date: str,
        sector_type: str = "industry",
        report_root: str = "reports",
    ) -> Dict[str, Any]:
        """运行持续性信号分析"""
        # 收集所有样本
        samples = self._collect_samples(start_date, end_date, sector_type, report_root)

        if not samples:
            return {
                "report_type": "persistence_signal_analysis",
                "start_date": start_date,
                "end_date": end_date,
                "total_samples": 0,
                "recommend_persistence_agent": False,
            }

        # 计算持续性信号
        for sample in samples:
            self._compute_persistence_signals(sample, samples)

        # 统计分析
        streak_performance = self._analyze_streak_performance(samples)
        label_persistence_performance = self._analyze_label_persistence(samples)
        label_transition_performance = self._analyze_label_transitions(samples)
        trend_performance = self._analyze_trend_performance(samples)
        regime_persistence = self._analyze_regime_persistence(samples)
        heat叠加 = self._analyze_heat_overlap(samples)

        # 判断是否建议新增 Agent
        recommendation = self._generate_recommendation(
            streak_performance, label_persistence_performance, trend_performance
        )

        result = {
            "report_type": "persistence_signal_analysis",
            "start_date": start_date,
            "end_date": end_date,
            "sector_type": sector_type,
            "total_samples": len(samples),
            "sectors_covered": len(set(s["sector_name"] for s in samples)),
            "streak_performance": streak_performance,
            "label_persistence_performance": label_persistence_performance,
            "label_transition_performance": label_transition_performance,
            "trend_performance": trend_performance,
            "regime_persistence": regime_persistence,
            "heat_overlap": heat叠加,
            "recommendation": recommendation,
            "warnings": [],
        }

        return result

    def _collect_samples(
        self, start_date: str, end_date: str, sector_type: str, report_root: str
    ) -> List[Dict[str, Any]]:
        """收集所有样本"""
        samples = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            path = os.path.join(
                report_root, "sector_research", date_str, "sector_research.json"
            )
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    summary = data.get("daily_summary", {})
                    top_watch = summary.get("top_watch_names", [])
                    regime = summary.get("market_regime", "unknown_regime")

                    for result in data.get("research_results", []):
                        sector_name = result.get("sector_name", "")
                        if not sector_name:
                            continue

                        forward_returns = self._compute_forward_returns(
                            sector_name, date_str, end_date, sector_type
                        )

                        sample = {
                            "as_of_date": date_str,
                            "sector_name": sector_name,
                            "consensus_label": result.get("consensus_label", ""),
                            "ranking_score": result.get("ranking_score", 0),
                            "opportunity_score": result.get("opportunity_score", 0),
                            "confidence_score": result.get("confidence_score", 0),
                            "market_regime": regime,
                            "is_top_watch": sector_name in top_watch,
                            "forward_returns": forward_returns,
                            # 持续性信号（后续计算）
                            "top_watch_streak": 0,
                            "label_persistence_days": 0,
                            "label_transition_from": "",
                            "label_transition_to": "",
                            "ranking_score_trend_3d": "unknown",
                            "opportunity_score_trend_3d": "unknown",
                            "confidence_score_trend_3d": "unknown",
                        }
                        samples.append(sample)

                except Exception:
                    pass

            current += timedelta(days=1)

        return samples

    def _compute_forward_returns(
        self, sector_name: str, signal_date: str, end_date: str, sector_type: str
    ) -> Dict[str, Optional[float]]:
        """计算 forward returns"""
        history_path = os.path.join(
            self.history_root, sector_type, f"{sector_name}.json"
        )
        if not os.path.exists(history_path):
            return {f"forward_{n}d_return": None for n in [1, 3, 5, 10, 20]}

        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except Exception:
            return {f"forward_{n}d_return": None for n in [1, 3, 5, 10, 20]}

        records = history_data.get("records", [])
        dated = []
        for r in records:
            for k, v in r.items():
                if isinstance(v, str) and len(v) == 10 and v[4] == "-":
                    dated.append((v, r))
                    break
        dated.sort(key=lambda x: x[0])

        signal_idx = None
        for i, (d, _) in enumerate(dated):
            if d == signal_date:
                signal_idx = i
                break

        if signal_idx is None:
            return {f"forward_{n}d_return": None for n in [1, 3, 5, 10, 20]}

        future = dated[signal_idx + 1:]
        if not future:
            return {f"forward_{n}d_return": None for n in [1, 3, 5, 10, 20]}

        returns = []
        prev_close = None
        for _, rec in future:
            close = self._get_close(rec)
            if prev_close is None:
                prev_close = close
            if prev_close > 0:
                ret = (close - prev_close) / prev_close * 100
            else:
                ret = 0.0
            returns.append(ret)
            prev_close = close

        def calc(n):
            return sum(returns[:n]) if len(returns) >= n else None

        return {
            "forward_1d_return": calc(1),
            "forward_3d_return": calc(3),
            "forward_5d_return": calc(5),
            "forward_10d_return": calc(10),
            "forward_20d_return": calc(20),
        }

    def _get_close(self, record: Dict) -> float:
        """获取收盘价"""
        for k, v in record.items():
            if isinstance(v, (int, float)) and v > 100:
                return float(v)
        return 0.0

    def _compute_persistence_signals(self, current: Dict, all_samples: List[Dict]):
        """计算当前样本的持续性信号"""
        sector = current["sector_name"]
        date = current["as_of_date"]

        # 获取该板块的历史样本
        history = sorted(
            [s for s in all_samples if s["sector_name"] == sector and s["as_of_date"] <= date],
            key=lambda x: x["as_of_date"]
        )

        if len(history) < 2:
            return

        # 1. top_watch_streak
        streak = 0
        for s in reversed(history):
            if s.get("is_top_watch"):
                streak += 1
            else:
                break
        current["top_watch_streak"] = streak

        # 2. label_persistence
        current_label = current["consensus_label"]
        label_days = 0
        for s in reversed(history):
            if s["consensus_label"] == current_label:
                label_days += 1
            else:
                break
        current["label_persistence_days"] = label_days

        # 3. label_transition
        if len(history) >= 2:
            prev = history[-2]
            current["label_transition_from"] = prev["consensus_label"]
            current["label_transition_to"] = current["consensus_label"]

        # 4. ranking_score_trend
        if len(history) >= 3:
            scores = [s["ranking_score"] for s in history[-3:]]
            current["ranking_score_trend_3d"] = self._compute_trend(scores)

        # 5. opportunity_score_trend
        if len(history) >= 3:
            scores = [s["opportunity_score"] for s in history[-3:]]
            current["opportunity_score_trend_3d"] = self._compute_trend(scores)

        # 6. confidence_score_trend
        if len(history) >= 3:
            scores = [s["confidence_score"] for s in history[-3:]]
            current["confidence_score_trend_3d"] = self._compute_trend(scores)

    def _compute_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return "unknown"

        diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
        avg_diff = sum(diffs) / len(diffs)

        if avg_diff > 0.05:
            return "rising"
        elif avg_diff < -0.05:
            return "falling"
        else:
            # 检查是否波动
            if max(diffs) - min(diffs) > 0.1:
                return "volatile"
            return "flat"

    def _analyze_streak_performance(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析 top_watch_streak 表现"""
        buckets = {"1_day": [], "2_days": [], "3_days": [], "5_plus_days": []}

        for s in samples:
            streak = s.get("top_watch_streak", 0)
            fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")
            if fwd_5d is None:
                continue

            if streak == 1:
                buckets["1_day"].append(fwd_5d)
            elif streak == 2:
                buckets["2_days"].append(fwd_5d)
            elif streak == 3:
                buckets["3_days"].append(fwd_5d)
            elif streak >= 5:
                buckets["5_plus_days"].append(fwd_5d)

        result = {}
        for bucket, values in buckets.items():
            if values:
                result[bucket] = {
                    "sample_count": len(values),
                    "avg_forward_5d": round(sum(values) / len(values), 2),
                    "positive_rate": round(sum(1 for v in values if v > 0) / len(values), 2),
                }
            else:
                result[bucket] = {"sample_count": 0}

        return result

    def _analyze_label_persistence(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析标签持续性表现"""
        # 按标签和持续天数分组
        groups = {}
        for s in samples:
            label = s["consensus_label"]
            days = s.get("label_persistence_days", 0)
            fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")
            if fwd_5d is None:
                continue

            key = f"{label}_persistence_{days}"
            if key not in groups:
                groups[key] = []
            groups[key].append(fwd_5d)

        # 聚合
        result = {}
        for key, values in groups.items():
            if len(values) >= 1:
                result[key] = {
                    "sample_count": len(values),
                    "avg_forward_5d": round(sum(values) / len(values), 2),
                    "positive_rate": round(sum(1 for v in values if v > 0) / len(values), 2),
                }

        return result

    def _analyze_label_transitions(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析标签转换路径"""
        transitions = {}
        for s in samples:
            from_label = s.get("label_transition_from", "")
            to_label = s.get("label_transition_to", "")
            fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")

            if not from_label or not to_label or from_label == to_label:
                continue
            if fwd_5d is None:
                continue

            key = f"{from_label} -> {to_label}"
            if key not in transitions:
                transitions[key] = []
            transitions[key].append(fwd_5d)

        # 聚合
        result = {}
        for key, values in transitions.items():
            if len(values) >= 1:
                result[key] = {
                    "sample_count": len(values),
                    "avg_forward_5d": round(sum(values) / len(values), 2),
                    "positive_rate": round(sum(1 for v in values if v > 0) / len(values), 2),
                }

        return result

    def _analyze_trend_performance(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析分数趋势表现"""
        result = {}

        for trend_field in ["ranking_score_trend_3d", "opportunity_score_trend_3d", "confidence_score_trend_3d"]:
            trend_groups = {}
            for s in samples:
                trend = s.get(trend_field, "unknown")
                fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")
                if fwd_5d is None or trend == "unknown":
                    continue

                if trend not in trend_groups:
                    trend_groups[trend] = []
                trend_groups[trend].append(fwd_5d)

            result[trend_field] = {}
            for trend, values in trend_groups.items():
                if len(values) >= 3:
                    result[trend_field][trend] = {
                        "sample_count": len(values),
                        "avg_forward_5d": round(sum(values) / len(values), 2),
                        "positive_rate": round(sum(1 for v in values if v > 0) / len(values), 2),
                    }

        return result

    def _analyze_regime_persistence(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析 regime 下的持续性"""
        regime_groups = {}
        for s in samples:
            regime = s.get("market_regime", "unknown_regime")
            streak = s.get("top_watch_streak", 0)
            fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")

            if fwd_5d is None:
                continue

            if regime not in regime_groups:
                regime_groups[regime] = {"streak_1": [], "streak_2_plus": []}

            if streak >= 2:
                regime_groups[regime]["streak_2_plus"].append(fwd_5d)
            else:
                regime_groups[regime]["streak_1"].append(fwd_5d)

        result = {}
        for regime, groups in regime_groups.items():
            result[regime] = {}
            for streak_bucket, values in groups.items():
                if values:
                    result[regime][streak_bucket] = {
                        "sample_count": len(values),
                        "avg_forward_5d": round(sum(values) / len(values), 2),
                        "positive_rate": round(sum(1 for v in values if v > 0) / len(values), 2),
                    }

        return result

    def _analyze_heat_overlap(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析与 short_term_heat 的叠加"""
        # 需要从 agent_opinions 获取 short_term_heat 的 vote
        # 简化：使用 is_top_watch 作为代理
        overlap_groups = {
            "top_watch_only": [],
            "not_top_watch": [],
        }

        for s in samples:
            fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")
            if fwd_5d is None:
                continue

            if s.get("is_top_watch"):
                overlap_groups["top_watch_only"].append(fwd_5d)
            else:
                overlap_groups["not_top_watch"].append(fwd_5d)

        result = {}
        for group, values in overlap_groups.items():
            if values:
                result[group] = {
                    "sample_count": len(values),
                    "avg_forward_5d": round(sum(values) / len(values), 2),
                    "positive_rate": round(sum(1 for v in values if v > 0) / len(values), 2),
                }

        return result

    def _generate_recommendation(
        self,
        streak_perf: Dict,
        label_perf: Dict,
        trend_perf: Dict,
    ) -> Dict[str, Any]:
        """生成 Phase 40 建议"""
        # 检查 streak >= 3 是否有显著差异
        streak_3 = streak_perf.get("3_days", {})
        streak_1 = streak_perf.get("1_day", {})

        streak_has_value = False
        if streak_3.get("sample_count", 0) >= 5 and streak_1.get("sample_count", 0) >= 5:
            if streak_3.get("avg_forward_5d", 0) > streak_1.get("avg_forward_5d", 0) + 0.5:
                streak_has_value = True

        # 检查趋势是否有解释力
        trend_has_value = False
        ranking_trend = trend_perf.get("ranking_score_trend_3d", {})
        if ranking_trend.get("rising", {}).get("sample_count", 0) >= 5:
            if ranking_trend["rising"].get("avg_forward_5d", 0) > 0:
                trend_has_value = True

        recommend = streak_has_value or trend_has_value

        if recommend:
            reason = "持续性信号（streak 或 trend）对后续表现有正向解释力"
        else:
            reason = "持续性信号对后续表现的解释力有限，建议继续观察"

        return {
            "recommend_persistence_agent": recommend,
            "recommended_role": "L2_specialized" if recommend else None,
            "reason": reason,
            "streak_has_value": streak_has_value,
            "trend_has_value": trend_has_value,
            "risks": [
                "样本量可能不足",
                "持续性信号可能只是噪声",
                "需要更多市场环境验证",
            ] if recommend else ["持续性信号无明显解释力"],
            "next_phase": "Phase 40" if recommend else "继续观察",
        }
