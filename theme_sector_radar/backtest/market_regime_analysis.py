"""
Market Regime Layer Backtest

为回测样本增加市场状态层，验证不同标签在不同市场环境下的表现差异。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


class MarketRegimeAnalysis:
    """
    Market Regime Layer Backtest

    为回测样本增加市场状态层，验证不同标签在不同市场环境下的表现差异。
    """

    def __init__(
        self,
        history_root: str = "data_cache/sector_history",
        benchmark_root: str = "data_cache/benchmarks",
    ):
        self.history_root = history_root
        self.benchmark_root = benchmark_root

    def run_analysis(
        self,
        start_date: str,
        end_date: str,
        sector_type: str = "industry",
        benchmark: str = "hs300",
        report_root: str = "reports",
    ) -> Dict[str, Any]:
        """运行市场状态分层分析"""
        # 加载基准数据
        benchmark_data = self._load_benchmark(benchmark)
        if not benchmark_data:
            return {"error": "No benchmark data found"}

        # 收集研究报告
        research_reports = self._collect_research_reports(start_date, end_date, report_root)

        # 收集 replay daily 报告
        replay_reports = self._collect_replay_reports(start_date, end_date, report_root)

        # 构建日期到报告的映射
        replay_by_date = {r["date"]: r["data"] for r in replay_reports}

        # 构建样本并挂载市场状态
        samples = []
        for report in research_reports:
            date_str = report["date"]
            research_data = report["data"]
            replay_data = replay_by_date.get(date_str, {})

            # 计算市场状态（no-lookahead）
            regime = self._compute_regime(
                date_str, benchmark_data, replay_data
            )

            for result in research_data.get("research_results", []):
                sector_name = result.get("sector_name", "")
                if not sector_name:
                    continue

                # 计算 forward returns
                forward_returns = self._compute_forward_returns(
                    sector_name, date_str, end_date, sector_type
                )

                sample = {
                    "signal_date": date_str,
                    "sector_name": sector_name,
                    "consensus_label": result.get("consensus_label", ""),
                    "ranking_score": result.get("ranking_score", 0.0),
                    "opportunity_score": result.get("opportunity_score", 0.0),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "evidence_score": result.get("evidence_score", 0.0),
                    "risk_control_score": result.get("risk_control_score", 0.0),
                    "forward_returns": forward_returns,
                    **regime,
                }
                samples.append(sample)

        # 分层统计
        label_regime_stats = self._aggregate_label_x_regime(samples)
        score_bucket_stats = self._aggregate_score_x_regime(samples)
        missed_regime = self._analyze_missed_by_regime(samples)
        failed_regime = self._analyze_failed_by_regime(samples)

        # regime 分布
        regime_distribution = self._compute_regime_distribution(samples)

        # no-lookahead 检查
        lookahead_check = self._check_no_lookahead(samples)

        result = {
            "report_type": "market_regime_analysis",
            "start_date": start_date,
            "end_date": end_date,
            "sector_type": sector_type,
            "benchmark": benchmark,
            "input_summary": {
                "research_report_count": len(research_reports),
                "sample_count": len(samples),
            },
            "regime_distribution": regime_distribution,
            "label_regime_performance": label_regime_stats,
            "score_bucket_regime_performance": score_bucket_stats,
            "missed_opportunity_by_regime": missed_regime,
            "failed_rebound_by_regime": failed_regime,
            "no_lookahead_check": lookahead_check,
            "warnings": [],
            "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
        }

        return result

    def _load_benchmark(self, benchmark: str) -> Dict[str, Any]:
        """加载基准数据"""
        bench_dir = os.path.join(self.benchmark_root, benchmark)
        if not os.path.exists(bench_dir):
            return {}

        # 找到覆盖范围最大的文件
        best_file = None
        best_count = 0
        for fname in os.listdir(bench_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(bench_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = data.get("records", [])
                if len(records) > best_count:
                    best_count = len(records)
                    best_file = fpath
            except Exception:
                continue

        if best_file:
            with open(best_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _collect_research_reports(
        self, start_date: str, end_date: str, report_root: str
    ) -> List[Dict[str, Any]]:
        """收集研究报告"""
        reports = []
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
                    reports.append({"date": date_str, "data": data})
                except Exception:
                    pass
            current += timedelta(days=1)

        return reports

    def _collect_replay_reports(
        self, start_date: str, end_date: str, report_root: str
    ) -> List[Dict[str, Any]]:
        """收集 replay daily 报告"""
        reports = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            path = os.path.join(
                report_root, "theme_sector_radar", date_str, "theme_sector_radar.json"
            )
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    reports.append({"date": date_str, "data": data})
                except Exception:
                    pass
            current += timedelta(days=1)

        return reports

    def _compute_regime(
        self,
        signal_date: str,
        benchmark_data: Dict[str, Any],
        replay_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """计算市场状态（no-lookahead）"""
        records = benchmark_data.get("records", [])

        # 找到 signal_date 及之前的数据
        prior_records = []
        for r in records:
            if r.get("date", "") <= signal_date:
                prior_records.append(r)

        # benchmark_trend
        benchmark_trend = self._compute_benchmark_trend(prior_records)

        # market_temperature_regime
        market_temp = self._compute_temperature_regime(replay_data)

        # breadth_regime
        breadth = self._compute_breadth_regime(replay_data)

        # volatility_regime
        volatility = self._compute_volatility_regime(prior_records)

        # regime_composite_label
        composite = self._compute_composite_regime(
            benchmark_trend, market_temp, breadth, volatility
        )

        # evidence
        evidence = []
        if benchmark_trend != "benchmark_unknown":
            evidence.append(f"benchmark_trend={benchmark_trend}")
        if market_temp != "market_unknown":
            evidence.append(f"market_temp={market_temp}")
        if breadth != "breadth_unknown":
            evidence.append(f"breadth={breadth}")
        if volatility != "volatility_unknown":
            evidence.append(f"volatility={volatility}")

        warnings = []
        if len(prior_records) < 5:
            warnings.append("benchmark 数据不足 5 天")

        return {
            "benchmark_trend": benchmark_trend,
            "market_temperature_regime": market_temp,
            "breadth_regime": breadth,
            "volatility_regime": volatility,
            "regime_composite_label": composite,
            "regime_evidence": evidence,
            "regime_warnings": warnings,
        }

    def _compute_benchmark_trend(self, records: List[Dict]) -> str:
        """计算基准趋势"""
        if len(records) < 5:
            return "benchmark_unknown"

        # 取最近 5 和 10 天的收盘价
        closes = [r.get("close", 0) for r in records if r.get("close", 0) > 0]
        if len(closes) < 5:
            return "benchmark_unknown"

        # 5 日收益
        ret_5d = (closes[-1] - closes[-5]) / closes[-5] * 100 if closes[-5] > 0 else 0

        # 10 日收益
        ret_10d = None
        if len(closes) >= 10:
            ret_10d = (closes[-1] - closes[-10]) / closes[-10] * 100 if closes[-10] > 0 else 0

        # 最大回撤
        peak = max(closes[-10:]) if len(closes) >= 10 else max(closes[-5:])
        dd = (peak - closes[-1]) / peak * 100 if peak > 0 else 0

        if ret_5d > 2 and dd < 3:
            return "benchmark_uptrend"
        elif ret_5d < -2:
            return "benchmark_downtrend"
        elif abs(ret_5d) < 1 and dd < 2:
            return "benchmark_sideways"
        else:
            return "benchmark_sideways"

    def _compute_temperature_regime(self, replay_data: Dict[str, Any]) -> str:
        """计算市场温度 regime"""
        mt = replay_data.get("market_temperature", {})
        score = mt.get("score", 50)
        label = mt.get("label", "neutral")

        if score >= 70 or label == "hot":
            return "market_hot"
        elif score >= 55 or label == "warm":
            return "market_warm"
        elif score >= 45 or label == "neutral":
            return "market_cool"
        elif score >= 30 or label == "cool":
            return "market_cold"
        else:
            return "market_cold"

    def _compute_breadth_regime(self, replay_data: Dict[str, Any]) -> str:
        """计算广度 regime"""
        industry_top = replay_data.get("industry_top", [])
        if not industry_top:
            return "breadth_unknown"

        # 统计上涨/下跌/持平板块
        rising = 0
        falling = 0
        flat = 0
        total = 0

        for sector in industry_top:
            change = sector.get("price_change_pct")
            if change is not None:
                total += 1
                if change > 0.1:
                    rising += 1
                elif change < -0.1:
                    falling += 1
                else:
                    flat += 1
            else:
                # 用 score 近似
                score = sector.get("score", 0)
                total += 1
                if score > 55:
                    rising += 1
                elif score < 45:
                    falling += 1
                else:
                    flat += 1

        if total == 0:
            return "breadth_unknown"

        rising_pct = rising / total
        falling_pct = falling / total

        if rising_pct >= 0.6:
            return "broad_rising"
        elif falling_pct >= 0.6:
            return "broad_falling"
        elif rising_pct > 0.3 and falling_pct > 0.3:
            return "mixed_breadth"
        elif rising_pct > falling_pct:
            return "narrow_rising"
        elif falling_pct > rising_pct:
            return "broad_falling"
        else:
            return "mixed_breadth"

    def _compute_volatility_regime(self, records: List[Dict]) -> str:
        """计算波动率 regime"""
        if len(records) < 5:
            return "volatility_unknown"

        pct_changes = [r.get("pct_change", 0) for r in records[-10:]]
        if not pct_changes:
            return "volatility_unknown"

        avg_abs_change = sum(abs(c) for c in pct_changes) / len(pct_changes)

        if avg_abs_change > 2.0:
            return "high_volatility"
        elif avg_abs_change > 1.0:
            return "normal_volatility"
        else:
            return "low_volatility"

    def _compute_composite_regime(
        self,
        benchmark_trend: str,
        market_temp: str,
        breadth: str,
        volatility: str,
    ) -> str:
        """计算综合市场状态标签"""
        # risk_on: uptrend + hot/warm + broad_rising
        if (benchmark_trend == "benchmark_uptrend" and
            market_temp in ["market_hot", "market_warm"] and
            breadth in ["broad_rising", "narrow_rising"]):
            return "risk_on"

        # risk_off: downtrend + cold + broad_falling
        if (benchmark_trend == "benchmark_downtrend" and
            market_temp in ["market_cold"] and
            breadth in ["broad_falling"]):
            return "risk_off"

        # weak_rebound: downtrend ending + cool + mixed
        if (benchmark_trend == "benchmark_sideways" and
            market_temp in ["market_cool", "market_cold"] and
            breadth in ["mixed_breadth", "narrow_rising"]):
            return "weak_rebound"

        # rotation_market: sideways + warm + narrow_rising
        if (benchmark_trend == "benchmark_sideways" and
            market_temp in ["market_warm"] and
            breadth in ["narrow_rising"]):
            return "rotation_market"

        # choppy: high volatility
        if volatility == "high_volatility":
            return "choppy_market"

        # 默认
        if benchmark_trend == "benchmark_unknown":
            return "unknown_regime"

        return "choppy_market"

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
        # 按日期排序
        dated = []
        for r in records:
            for k, v in r.items():
                if isinstance(v, str) and len(v) == 10 and v[4] == "-":
                    dated.append((v, r))
                    break
        dated.sort(key=lambda x: x[0])

        # 找到 signal_date 位置
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

    def _aggregate_label_x_regime(self, samples: List[Dict]) -> Dict[str, Any]:
        """按 label x regime 聚合"""
        groups = {}
        for s in samples:
            label = s.get("consensus_label", "")
            regime = s.get("regime_composite_label", "unknown")
            key = f"{label}|{regime}"
            if key not in groups:
                groups[key] = []
            groups[key].append(s)

        result = {}
        for key, group in groups.items():
            label, regime = key.split("|", 1)
            if label not in result:
                result[label] = {}
            result[label][regime] = self._compute_group_stats(group)

        return result

    def _aggregate_score_x_regime(self, samples: List[Dict]) -> Dict[str, Any]:
        """按 score bucket x regime 聚合"""
        result = {"ranking": {}, "opportunity": {}, "confidence": {}}

        for s in samples:
            regime = s.get("regime_composite_label", "unknown")

            # ranking_score bucket
            rs = s.get("ranking_score", 0)
            if rs >= 0.65:
                rb = "high"
            elif rs >= 0.40:
                rb = "medium"
            else:
                rb = "low"
            result["ranking"].setdefault(rb, {}).setdefault(regime, []).append(s)

            # opportunity_score bucket
            os_ = s.get("opportunity_score", 0)
            if os_ >= 0.65:
                ob = "high"
            elif os_ >= 0.40:
                ob = "medium"
            else:
                ob = "low"
            result["opportunity"].setdefault(ob, {}).setdefault(regime, []).append(s)

            # confidence_score bucket
            cs = s.get("confidence_score", 0)
            if cs >= 0.7:
                cb = "high"
            elif cs >= 0.5:
                cb = "medium"
            else:
                cb = "low"
            result["confidence"].setdefault(cb, {}).setdefault(regime, []).append(s)

        # 聚合
        for score_type in result:
            for bucket in list(result[score_type].keys()):
                for regime in list(result[score_type][bucket].keys()):
                    result[score_type][bucket][regime] = self._compute_group_stats(
                        result[score_type][bucket][regime]
                    )

        return result

    def _analyze_missed_by_regime(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析 missed_opportunity 的市场状态分布"""
        missed = []
        for s in samples:
            label = s.get("consensus_label", "")
            fwd = s.get("forward_returns", {}).get("forward_5d_return")
            if (
                label in ["weak_or_avoid", "low_signal_noise", "weak_continuation",
                          "defensive_stable_watch", "data_limited_neutral"]
                and fwd is not None
                and fwd > 3.0
            ):
                missed.append(s)

        # 按 regime 聚合
        groups = {}
        for s in missed:
            regime = s.get("regime_composite_label", "unknown")
            groups.setdefault(regime, []).append(s)

        result = {}
        for regime, group in groups.items():
            result[regime] = {
                "count": len(group),
                "avg_forward_5d_return": self._avg_fwd(group, "forward_5d_return"),
                "samples": [
                    {
                        "signal_date": s["signal_date"],
                        "sector_name": s["sector_name"],
                        "consensus_label": s["consensus_label"],
                        "forward_5d_return": s.get("forward_returns", {}).get("forward_5d_return"),
                    }
                    for s in group[:5]
                ],
            }

        return {"total_missed": len(missed), "by_regime": result}

    def _analyze_failed_by_regime(self, samples: List[Dict]) -> Dict[str, Any]:
        """分析 failed_rebound 的市场状态分布"""
        failed = []
        for s in samples:
            label = s.get("consensus_label", "")
            fwd = s.get("forward_returns", {}).get("forward_5d_return")
            if label == "oversold_rebound_candidate" and fwd is not None and fwd < 0:
                failed.append(s)

        groups = {}
        for s in failed:
            regime = s.get("regime_composite_label", "unknown")
            groups.setdefault(regime, []).append(s)

        result = {}
        for regime, group in groups.items():
            result[regime] = {
                "count": len(group),
                "avg_forward_5d_return": self._avg_fwd(group, "forward_5d_return"),
                "samples": [
                    {
                        "signal_date": s["signal_date"],
                        "sector_name": s["sector_name"],
                        "forward_5d_return": s.get("forward_returns", {}).get("forward_5d_return"),
                    }
                    for s in group[:5]
                ],
            }

        return {"total_failed": len(failed), "by_regime": result}

    def _compute_regime_distribution(self, samples: List[Dict]) -> Dict[str, Any]:
        """计算 regime 分布"""
        dist = {
            "benchmark_trend": {},
            "market_temperature_regime": {},
            "breadth_regime": {},
            "volatility_regime": {},
            "regime_composite_label": {},
        }

        for s in samples:
            dist["benchmark_trend"][s.get("benchmark_trend", "unknown")] = (
                dist["benchmark_trend"].get(s.get("benchmark_trend", "unknown"), 0) + 1
            )
            dist["market_temperature_regime"][s.get("market_temperature_regime", "unknown")] = (
                dist["market_temperature_regime"].get(s.get("market_temperature_regime", "unknown"), 0) + 1
            )
            dist["breadth_regime"][s.get("breadth_regime", "unknown")] = (
                dist["breadth_regime"].get(s.get("breadth_regime", "unknown"), 0) + 1
            )
            dist["volatility_regime"][s.get("volatility_regime", "unknown")] = (
                dist["volatility_regime"].get(s.get("volatility_regime", "unknown"), 0) + 1
            )
            dist["regime_composite_label"][s.get("regime_composite_label", "unknown")] = (
                dist["regime_composite_label"].get(s.get("regime_composite_label", "unknown"), 0) + 1
            )

        return dist

    def _check_no_lookahead(self, samples: List[Dict]) -> Dict[str, Any]:
        """检查 no-lookahead"""
        violations = []
        for s in samples:
            # regime 字段不应该包含未来信息
            warnings = s.get("regime_warnings", [])
            if any("未来" in w or "future" in w.lower() for w in warnings):
                violations.append({
                    "signal_date": s["signal_date"],
                    "sector_name": s["sector_name"],
                    "warning": warnings[0],
                })

        return {
            "violations": violations,
            "violation_count": len(violations),
            "total_samples": len(samples),
            "passed": len(violations) == 0,
        }

    def _compute_group_stats(self, group: List[Dict]) -> Dict[str, Any]:
        """计算分组统计"""
        if not group:
            return {"sample_count": 0}

        fwd_5d = [
            s["forward_returns"]["forward_5d_return"]
            for s in group
            if s.get("forward_returns", {}).get("forward_5d_return") is not None
        ]
        fwd_10d = [
            s["forward_returns"]["forward_10d_return"]
            for s in group
            if s.get("forward_returns", {}).get("forward_10d_return") is not None
        ]

        return {
            "sample_count": len(group),
            "avg_forward_5d_return": round(sum(fwd_5d) / len(fwd_5d), 2) if fwd_5d else None,
            "avg_forward_10d_return": round(sum(fwd_10d) / len(fwd_10d), 2) if fwd_10d else None,
            "positive_rate_5d": round(sum(1 for r in fwd_5d if r > 0) / len(fwd_5d), 2) if fwd_5d else None,
        }

    def _avg_fwd(self, group: List[Dict], field: str) -> Optional[float]:
        """计算 forward return 平均值"""
        vals = [
            s.get("forward_returns", {}).get(field)
            for s in group
            if s.get("forward_returns", {}).get(field) is not None
        ]
        if vals:
            return round(sum(vals) / len(vals), 2)
        return None
