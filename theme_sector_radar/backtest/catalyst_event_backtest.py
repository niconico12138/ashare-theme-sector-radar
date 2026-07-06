"""
CatalystEventAgent 信号验证

验证催化事件信号是否有解释力。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class CatalystEventBacktest:
    """
    CatalystEventAgent 信号验证

    验证催化事件信号是否有解释力。
    """

    def __init__(
        self,
        history_root: str = "data_cache/sector_history",
        catalyst_root: str = "data_cache/catalyst_events",
    ):
        self.history_root = history_root
        self.catalyst_root = catalyst_root

    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        sector_type: str = "industry",
        report_root: str = "reports",
    ) -> Dict[str, Any]:
        """运行催化事件回测"""
        samples = self._collect_samples(start_date, end_date, sector_type, report_root)

        if not samples:
            return {
                "report_type": "catalyst_event_backtest",
                "start_date": start_date,
                "end_date": end_date,
                "total_samples": 0,
                "recommendation": {"recommend_vote_calibration": False},
            }

        # 统计分析
        catalyst_label_perf = self._aggregate_by_catalyst_label(samples)
        event_count_perf = self._aggregate_by_event_count(samples)
        freshness_perf = self._aggregate_by_freshness(samples)
        confidence_perf = self._aggregate_by_confidence(samples)
        heat_overlap = self._analyze_heat_overlap(samples)
        persistence_overlap = self._analyze_persistence_overlap(samples)
        regime_perf = self._analyze_regime_performance(samples)

        # 数据状态统计
        data_status_counts = {}
        for s in samples:
            status = s.get("data_status", "unknown")
            data_status_counts[status] = data_status_counts.get(status, 0) + 1

        has_fixture = data_status_counts.get("fixture", 0) > 0
        has_real = data_status_counts.get("real", 0) > 0

        # 生成建议
        recommendation = self._generate_recommendation(
            catalyst_label_perf, heat_overlap, has_fixture, has_real
        )

        result = {
            "report_type": "catalyst_event_backtest",
            "start_date": start_date,
            "end_date": end_date,
            "sector_type": sector_type,
            "total_samples": len(samples),
            "cache_coverage": sum(1 for s in samples if s.get("data_status") != "missing_cache") / len(samples) if samples else 0,
            "data_status_counts": data_status_counts,
            "catalyst_label_performance": catalyst_label_perf,
            "event_count_performance": event_count_perf,
            "freshness_performance": freshness_perf,
            "confidence_performance": confidence_perf,
            "heat_overlap": heat_overlap,
            "persistence_overlap": persistence_overlap,
            "regime_performance": regime_perf,
            "recommendation": recommendation,
            "warnings": [],
        }

        return result

    def _collect_samples(
        self, start_date: str, end_date: str, sector_type: str, report_root: str
    ) -> List[Dict[str, Any]]:
        """收集样本"""
        samples = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            research_path = os.path.join(
                report_root, "sector_research", date_str, "sector_research.json"
            )
            catalyst_path = os.path.join(
                self.catalyst_root, date_str, "events.json"
            )

            # 加载 catalyst 数据
            catalyst_events = []
            data_status = "missing_cache"
            if os.path.exists(catalyst_path):
                try:
                    with open(catalyst_path, "r", encoding="utf-8") as f:
                        catalyst_data = json.load(f)
                    catalyst_events = catalyst_data.get("events", [])
                    # 检查是否是 fixture 数据
                    if catalyst_events and catalyst_events[0].get("source") == "fixture":
                        data_status = "fixture"
                    else:
                        data_status = "real"
                except Exception:
                    pass

            # 加载 research 数据
            if os.path.exists(research_path):
                try:
                    with open(research_path, "r", encoding="utf-8") as f:
                        research_data = json.load(f)

                    # 获取 regime
                    regime = "unknown_regime"
                    for result in research_data.get("research_results", []):
                        mr = result.get("market_regime", {})
                        if mr and mr.get("regime_composite_label"):
                            regime = mr["regime_composite_label"]
                            break

                    for result in research_data.get("research_results", []):
                        sector_name = result.get("sector_name", "")
                        if not sector_name:
                            continue

                        # 获取 catalyst_event opinion
                        catalyst_opinion = None
                        heat_opinion = None
                        persistence_opinion = None
                        for op in result.get("agent_opinions", []):
                            if op.get("agent_id") == "catalyst_event":
                                catalyst_opinion = op
                            elif op.get("agent_id") == "short_term_heat":
                                heat_opinion = op
                            elif op.get("agent_id") == "persistence_strength":
                                persistence_opinion = op

                        # 计算 forward returns
                        forward_returns = self._compute_forward_returns(
                            sector_name, date_str, end_date, sector_type
                        )

                        # 匹配 catalyst 事件
                        matched_count = 0
                        avg_confidence = 0.0
                        freshness = "unknown"
                        source_ids = []

                        if catalyst_opinion:
                            meta = catalyst_opinion.get("metadata", {})
                            matched_count = meta.get("matched_event_count", 0)
                            source_ids = meta.get("source_ids", [])

                        if catalyst_events:
                            # 简化：使用 catalyst_opinion 的 metadata
                            matched_count = catalyst_opinion.get("metadata", {}).get("matched_event_count", 0) if catalyst_opinion else 0

                        sample = {
                            "as_of_date": date_str,
                            "sector_name": sector_name,
                            "catalyst_label": catalyst_opinion.get("label", "catalyst_unknown") if catalyst_opinion else "catalyst_unknown",
                            "matched_event_count": matched_count,
                            "avg_event_confidence": avg_confidence,
                            "freshness": freshness,
                            "source_ids": source_ids,
                            "market_regime": regime,
                            "short_term_heat_vote": heat_opinion.get("vote", "neutral") if heat_opinion else "neutral",
                            "persistence_strength_vote": persistence_opinion.get("vote", "neutral") if persistence_opinion else "neutral",
                            "consensus_label": result.get("consensus_label", ""),
                            "ranking_score": result.get("ranking_score", 0),
                            "opportunity_score": result.get("opportunity_score", 0),
                            "forward_returns": forward_returns,
                            "data_status": data_status,
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

    def _aggregate_by_catalyst_label(self, samples: List[Dict]) -> Dict[str, Any]:
        """按 catalyst_label 聚合"""
        groups = {}
        for s in samples:
            label = s.get("catalyst_label", "catalyst_unknown")
            if label not in groups:
                groups[label] = []
            groups[label].append(s)

        result = {}
        for label, group in groups.items():
            result[label] = self._compute_group_stats(group)
        return result

    def _aggregate_by_event_count(self, samples: List[Dict]) -> Dict[str, Any]:
        """按 event_count 分桶"""
        buckets = {"0_events": [], "1_event": [], "2_3_events": [], "4_plus_events": []}
        for s in samples:
            count = s.get("matched_event_count", 0)
            if count == 0:
                buckets["0_events"].append(s)
            elif count == 1:
                buckets["1_event"].append(s)
            elif count <= 3:
                buckets["2_3_events"].append(s)
            else:
                buckets["4_plus_events"].append(s)

        result = {}
        for bucket, group in buckets.items():
            result[bucket] = self._compute_group_stats(group)
        return result

    def _aggregate_by_freshness(self, samples: List[Dict]) -> Dict[str, Any]:
        """按 freshness 聚合"""
        groups = {}
        for s in samples:
            freshness = s.get("freshness", "unknown")
            if freshness not in groups:
                groups[freshness] = []
            groups[freshness].append(s)

        result = {}
        for freshness, group in groups.items():
            result[freshness] = self._compute_group_stats(group)
        return result

    def _aggregate_by_confidence(self, samples: List[Dict]) -> Dict[str, Any]:
        """按 confidence 分桶"""
        buckets = {"high": [], "medium": [], "low": []}
        for s in samples:
            conf = s.get("avg_event_confidence", 0)
            if conf >= 0.7:
                buckets["high"].append(s)
            elif conf >= 0.4:
                buckets["medium"].append(s)
            else:
                buckets["low"].append(s)

        result = {}
        for bucket, group in buckets.items():
            result[bucket] = self._compute_group_stats(group)
        return result

    def _analyze_heat_overlap(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析 catalyst x short_term_heat 叠加"""
        groups = {
            "catalyst_observed + heat_positive": [],
            "catalyst_observed + heat_non_positive": [],
            "no_catalyst + heat_positive": [],
        }

        for s in samples:
            cat_label = s.get("catalyst_label", "")
            heat_vote = s.get("short_term_heat_vote", "neutral")
            fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")
            if fwd_5d is None:
                continue

            if cat_label == "catalyst_observed" and heat_vote == "positive":
                groups["catalyst_observed + heat_positive"].append(fwd_5d)
            elif cat_label == "catalyst_observed":
                groups["catalyst_observed + heat_non_positive"].append(fwd_5d)
            elif cat_label in ["no_catalyst_observed", "catalyst_unknown"] and heat_vote == "positive":
                groups["no_catalyst + heat_positive"].append(fwd_5d)

        result = {}
        for group, values in groups.items():
            if values:
                result[group] = {
                    "sample_count": len(values),
                    "avg_forward_5d": round(sum(values) / len(values), 2),
                    "positive_rate": round(sum(1 for v in values if v > 0) / len(values), 2),
                }
        return result

    def _analyze_persistence_overlap(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析 catalyst x persistence_strength 叠加"""
        groups = {
            "catalyst_observed + persistence_positive": [],
            "catalyst_observed + persistence_neutral": [],
            "no_catalyst + persistence_positive": [],
        }

        for s in samples:
            cat_label = s.get("catalyst_label", "")
            pers_vote = s.get("persistence_strength_vote", "neutral")
            fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")
            if fwd_5d is None:
                continue

            if cat_label == "catalyst_observed" and pers_vote == "positive":
                groups["catalyst_observed + persistence_positive"].append(fwd_5d)
            elif cat_label == "catalyst_observed":
                groups["catalyst_observed + persistence_neutral"].append(fwd_5d)
            elif cat_label in ["no_catalyst_observed", "catalyst_unknown"] and pers_vote == "positive":
                groups["no_catalyst + persistence_positive"].append(fwd_5d)

        result = {}
        for group, values in groups.items():
            if values:
                result[group] = {
                    "sample_count": len(values),
                    "avg_forward_5d": round(sum(values) / len(values), 2),
                    "positive_rate": round(sum(1 for v in values if v > 0) / len(values), 2),
                }
        return result

    def _analyze_regime_performance(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析 catalyst x market_regime"""
        groups = {}
        for s in samples:
            regime = s.get("market_regime", "unknown_regime")
            cat_label = s.get("catalyst_label", "")
            fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")
            if fwd_5d is None:
                continue

            key = f"{regime}_{cat_label}"
            if key not in groups:
                groups[key] = []
            groups[key].append(fwd_5d)

        result = {}
        for key, values in groups.items():
            if len(values) >= 2:
                result[key] = {
                    "sample_count": len(values),
                    "avg_forward_5d": round(sum(values) / len(values), 2),
                    "positive_rate": round(sum(1 for v in values if v > 0) / len(values), 2),
                }
        return result

    def _compute_group_stats(self, group: List[Dict]) -> Dict[str, Any]:
        """计算分组统计"""
        if not group:
            return {"sample_count": 0}

        fwd_5d = [
            s["forward_returns"]["forward_5d_return"]
            for s in group
            if s.get("forward_returns", {}).get("forward_5d_return") is not None
        ]

        return {
            "sample_count": len(group),
            "avg_forward_5d": round(sum(fwd_5d) / len(fwd_5d), 2) if fwd_5d else None,
            "positive_rate": round(sum(1 for v in fwd_5d if v > 0) / len(fwd_5d), 2) if fwd_5d else None,
        }

    def _generate_recommendation(
        self,
        label_perf: Dict,
        heat_overlap: Dict,
        has_fixture: bool,
        has_real: bool,
    ) -> Dict[str, Any]:
        """生成建议"""
        observed = label_perf.get("catalyst_observed", {})
        observed_count = observed.get("sample_count", 0)

        # 检查是否有叠加效果
        heat叠加 = heat_overlap.get("catalyst_observed + heat_positive", {})
        heat_no_cat = heat_overlap.get("no_catalyst + heat_positive", {})

        has叠加 = False
        if heat叠加.get("sample_count", 0) >= 3 and heat_no_cat.get("sample_count", 0) >= 3:
            if heat叠加.get("avg_forward_5d", 0) > heat_no_cat.get("avg_forward_5d", 0) + 0.5:
                has叠加 = True

        # 判断
        if has_fixture and not has_real:
            return {
                "recommend_vote_calibration": False,
                "recommended_next_phase": "Phase 47",
                "recommended_mode": "keep_report_only",
                "reasons": ["仅有 fixture 数据，标记为 limited_fixture_validation"],
                "risks": ["fixture 数据不代表真实事件信号"],
                "data_limitations": ["需要真实网络数据验证"],
            }

        if observed_count < 10:
            return {
                "recommend_vote_calibration": False,
                "recommended_next_phase": "Phase 47",
                "recommended_mode": "keep_report_only",
                "reasons": [f"catalyst_observed 样本数不足 ({observed_count})"],
                "risks": ["样本量不足以支撑 vote 校准"],
                "data_limitations": ["需要更多真实事件样本"],
            }

        if has叠加:
            return {
                "recommend_vote_calibration": True,
                "recommended_next_phase": "Phase 47",
                "recommended_mode": "selective_neutral_plus",
                "reasons": ["catalyst_observed + short_term_heat positive 有叠加解释力"],
                "risks": ["叠加效果需要更多验证"],
                "data_limitations": [],
            }

        return {
            "recommend_vote_calibration": False,
            "recommended_next_phase": "Phase 47",
            "recommended_mode": "keep_report_only",
            "reasons": ["catalyst_observed 信号解释力有限"],
            "risks": ["事件信号可能只是噪声"],
            "data_limitations": ["需要更多真实事件样本验证"],
        }
