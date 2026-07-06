"""
Opportunity Score and Rebound Label 归因分析

分析 missed opportunities、failed rebounds、opportunity_score 分布。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


class OpportunityReboundAnalysis:
    """
    Opportunity Score and Rebound Label 归因分析

    分析 missed opportunities、failed rebounds、opportunity_score 分布。
    """

    def __init__(self, history_root: str = "data_cache/sector_history"):
        """
        初始化

        Args:
            history_root: 历史数据根目录
        """
        self.history_root = history_root

    def run_analysis(
        self,
        start_date: str,
        end_date: str,
        sector_type: str = "industry",
        report_root: str = "reports",
    ) -> Dict[str, Any]:
        """
        运行归因分析

        Args:
            start_date: 开始日期
            end_date: 结束日期
            sector_type: 板块类型
            report_root: 报告根目录

        Returns:
            归因分析结果
        """
        # 收集研究报告
        research_reports = self._collect_research_reports(
            start_date, end_date, report_root
        )

        # 提取样本并计算归因
        samples = []
        for report in research_reports:
            date_str = report["date"]
            research_data = report["data"]

            for result in research_data.get("research_results", []):
                sector_name = result.get("sector_name", "")
                if not sector_name:
                    continue

                attribution = self._build_attribution(
                    sector_name, sector_type, date_str, result
                )
                if attribution:
                    samples.append(attribution)

        # 分类
        missed_opportunity = self._identify_missed_opportunity(samples)
        failed_rebound = self._identify_failed_rebound(samples)

        # 聚类
        missed_clusters = self._cluster_missed_opportunity(missed_opportunity)
        failed_clusters = self._cluster_failed_rebound(failed_rebound)

        # opportunity_score 分桶
        opportunity_buckets = self._aggregate_opportunity_buckets(samples)

        # 诊断 high 桶为空的原因
        high_bucket_diagnosis = self._diagnose_high_bucket(samples)

        # 构建结果
        result = {
            "report_type": "opportunity_rebound_analysis",
            "start_date": start_date,
            "end_date": end_date,
            "sector_type": sector_type,
            "input_summary": {
                "research_report_count": len(research_reports),
                "sample_count": len(samples),
            },
            "missed_opportunity": {
                "count": len(missed_opportunity),
                "samples": missed_opportunity[:20],
                "clusters": missed_clusters,
            },
            "failed_rebound": {
                "count": len(failed_rebound),
                "samples": failed_rebound[:20],
                "clusters": failed_clusters,
            },
            "opportunity_buckets": opportunity_buckets,
            "high_bucket_diagnosis": high_bucket_diagnosis,
            "warnings": [],
            "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
        }

        return result

    def _collect_research_reports(
        self,
        start_date: str,
        end_date: str,
        report_root: str,
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

    def _build_attribution(
        self,
        sector_name: str,
        sector_type: str,
        signal_date: str,
        result: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """构建单条归因记录"""
        # 读取历史数据
        history_path = os.path.join(
            self.history_root, sector_type, f"{sector_name}.json"
        )
        if not os.path.exists(history_path):
            return None

        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except Exception:
            return None

        records = history_data.get("records", [])
        if not records:
            return None

        # 按日期排序
        dated_records = []
        for r in records:
            date_val = None
            for k, v in r.items():
                if isinstance(v, str) and len(v) == 10 and v[4] == "-":
                    date_val = v
                    break
            if date_val:
                dated_records.append((date_val, r))
        dated_records.sort(key=lambda x: x[0])

        # 找到 signal_date 的位置
        signal_idx = None
        for i, (d, _) in enumerate(dated_records):
            if d == signal_date:
                signal_idx = i
                break

        if signal_idx is None:
            return None

        # 计算 forward returns
        forward_returns = self._compute_forward_returns(dated_records, signal_idx)

        # 计算 pre returns
        pre_returns = self._compute_pre_returns(dated_records, signal_idx)

        # 计算 max drawdown before signal
        max_dd = self._compute_max_drawdown(dated_records, signal_idx, lookback=20)

        # 计算 rebound from recent low
        rebound = self._compute_rebound_from_low(dated_records, signal_idx, lookback=10)

        # 提取 views
        views = result.get("views", {})
        technical_view = views.get("technical", {})
        heat_view = views.get("heat", {})
        rotation_view = views.get("rotation", {})
        risk_view = views.get("risk", {})
        data_quality_view = views.get("data_quality", {})

        # 提取 score_data 中的关键字段
        dimension_scores = result.get("dimension_scores", {})

        # 构建归因记录
        attribution = {
            "signal_date": signal_date,
            "sector_name": sector_name,
            "consensus_label": result.get("consensus_label", ""),
            "ranking_score": result.get("ranking_score", 0.0),
            "opportunity_score": result.get("opportunity_score", 0.0),
            "confidence_score": result.get("confidence_score", 0.0),
            "evidence_score": result.get("evidence_score", 0.0),
            "risk_control_score": result.get("risk_control_score", 0.0),
            # views
            "technical_label": technical_view.get("technical_label", ""),
            "technical_score": technical_view.get("technical_score", 0.0),
            "heat_label": heat_view.get("heat_label", ""),
            "heat_score": heat_view.get("heat_score", 0.0),
            "rotation_label": rotation_view.get("rotation_label", ""),
            "rotation_score": rotation_view.get("rotation_score", 0.0),
            "risk_label": risk_view.get("risk_label", ""),
            "risk_score": risk_view.get("risk_score", 0.0),
            "data_quality_label": data_quality_view.get("data_quality_label", ""),
            "data_quality_score": data_quality_view.get("data_quality_score", 0.0),
            # dimension scores
            "dimension_technical": dimension_scores.get("technical", 0.0),
            "dimension_heat": dimension_scores.get("heat", 0.0),
            "dimension_rotation": dimension_scores.get("rotation", 0.0),
            "dimension_market_context": dimension_scores.get("market_context", 0.0),
            # votes
            "agent_votes": result.get("agent_votes", {}),
            # conflict / veto
            "conflict_level": result.get("conflict_level", "none"),
            "conflict_summary": result.get("conflict_summary", ""),
            "veto_triggered": result.get("veto", {}).get("veto_triggered", False),
            "veto_reasons": result.get("veto_reasons", []),
            # pre/forward returns
            "pre_1d_return": pre_returns.get("pre_1d_return"),
            "pre_3d_return": pre_returns.get("pre_3d_return"),
            "pre_5d_return": pre_returns.get("pre_5d_return"),
            "pre_10d_return": pre_returns.get("pre_10d_return"),
            "pre_20d_return": pre_returns.get("pre_20d_return"),
            "forward_1d_return": forward_returns.get("forward_1d_return"),
            "forward_3d_return": forward_returns.get("forward_3d_return"),
            "forward_5d_return": forward_returns.get("forward_5d_return"),
            "forward_10d_return": forward_returns.get("forward_10d_return"),
            "forward_20d_return": forward_returns.get("forward_20d_return"),
            # technical indicators
            "max_drawdown_before_signal": max_dd,
            "rebound_from_recent_low": rebound,
        }

        return attribution

    def _compute_forward_returns(
        self, dated_records: List[Tuple[str, Dict]], signal_idx: int
    ) -> Dict[str, Optional[float]]:
        """计算 forward returns"""
        future = dated_records[signal_idx + 1:]
        if not future:
            return {f"forward_{n}d_return": None for n in [1, 3, 5, 10, 20]}

        # 计算每日收益率
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

    def _compute_pre_returns(
        self, dated_records: List[Tuple[str, Dict]], signal_idx: int
    ) -> Dict[str, Optional[float]]:
        """计算 pre returns (信号前的表现)"""
        past = dated_records[max(0, signal_idx - 20):signal_idx]
        if len(past) < 2:
            return {f"pre_{n}d_return": None for n in [1, 3, 5, 10, 20]}

        # 计算每日收益率
        returns = []
        prev_close = None
        for _, rec in past:
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
            # pre return 是 signal 前 n 天的累计收益
            if len(returns) >= n:
                return sum(returns[-n:])
            return None

        return {
            "pre_1d_return": calc(1),
            "pre_3d_return": calc(3),
            "pre_5d_return": calc(5),
            "pre_10d_return": calc(10),
            "pre_20d_return": calc(20) if len(returns) >= 20 else None,
        }

    def _compute_max_drawdown(
        self, dated_records: List[Tuple[str, Dict]], signal_idx: int, lookback: int = 20
    ) -> Optional[float]:
        """计算信号前最大回撤"""
        start = max(0, signal_idx - lookback)
        window = dated_records[start:signal_idx + 1]
        if len(window) < 2:
            return None

        closes = [self._get_close(r) for _, r in window]
        peak = closes[0]
        max_dd = 0.0
        for c in closes:
            if c > peak:
                peak = c
            dd = (peak - c) / peak * 100 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return round(max_dd, 2)

    def _compute_rebound_from_low(
        self, dated_records: List[Tuple[str, Dict]], signal_idx: int, lookback: int = 10
    ) -> Optional[float]:
        """计算从近期低点的反弹幅度"""
        start = max(0, signal_idx - lookback)
        window = dated_records[start:signal_idx + 1]
        if len(window) < 2:
            return None

        closes = [self._get_close(r) for _, r in window]
        recent_low = min(closes)
        current = closes[-1]

        if recent_low > 0:
            return round((current - recent_low) / recent_low * 100, 2)
        return None

    def _get_close(self, record: Dict) -> float:
        """从记录中获取收盘价"""
        for k, v in record.items():
            if isinstance(v, (int, float)) and v > 0:
                # 尝试识别收盘价字段
                pass
        # 使用第一个数值字段作为收盘价的近似
        for k, v in record.items():
            if isinstance(v, (int, float)) and v > 100:
                return float(v)
        return 0.0

    def _identify_missed_opportunity(
        self, samples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """识别 missed opportunity 样本"""
        missed = []
        for s in samples:
            label = s.get("consensus_label", "")
            fwd_5d = s.get("forward_5d_return")
            if (
                label in [
                    "weak_or_avoid",
                    "low_signal_noise",
                    "weak_continuation",
                    "defensive_stable_watch",
                    "data_limited_neutral",
                ]
                and fwd_5d is not None
                and fwd_5d > 3.0
            ):
                missed.append(s)
        return sorted(missed, key=lambda x: x.get("forward_5d_return", 0), reverse=True)

    def _identify_failed_rebound(
        self, samples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """识别 failed rebound 样本"""
        failed = []
        for s in samples:
            label = s.get("consensus_label", "")
            fwd_5d = s.get("forward_5d_return")
            if label == "oversold_rebound_candidate" and fwd_5d is not None and fwd_5d < 0:
                failed.append(s)
        return sorted(failed, key=lambda x: x.get("forward_5d_return", 0))

    def _cluster_missed_opportunity(
        self, missed: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """对 missed opportunity 进行聚类"""
        clusters = {
            "momentum_repair": [],
            "relative_strength_repair": [],
            "oversold_bounce": [],
            "data_quality_gap": [],
            "low_signal_noise": [],
        }

        for s in missed:
            pre_5d = s.get("pre_5d_return")
            pre_10d = s.get("pre_10d_return")
            rebound = s.get("rebound_from_recent_low")
            max_dd = s.get("max_drawdown_before_signal")
            data_quality = s.get("data_quality_label", "")
            heat_label = s.get("heat_label", "")
            technical_label = s.get("technical_label", "")

            if pre_5d is not None and pre_5d < -5 and rebound is not None and rebound > 3:
                clusters["oversold_bounce"].append(s)
            elif (
                pre_5d is not None
                and pre_5d > 0
                and heat_label in ["heat_moderate", "heat_active"]
            ):
                clusters["momentum_repair"].append(s)
            elif (
                s.get("dimension_market_context", 0) > 0.5
                and pre_5d is not None
                and pre_5d > -2
            ):
                clusters["relative_strength_repair"].append(s)
            elif data_quality in ["data_limited", "data_unreliable"]:
                clusters["data_quality_gap"].append(s)
            else:
                clusters["low_signal_noise"].append(s)

        # 统计
        result = {}
        for name, items in clusters.items():
            if items:
                fwd_5d_values = [
                    x["forward_5d_return"]
                    for x in items
                    if x.get("forward_5d_return") is not None
                ]
                avg_5d = sum(fwd_5d_values) / len(fwd_5d_values) if fwd_5d_values else None
                result[name] = {
                    "count": len(items),
                    "avg_forward_5d_return": round(avg_5d, 2) if avg_5d else None,
                    "samples": items[:5],
                }

        return result

    def _cluster_failed_rebound(
        self, failed: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """对 failed rebound 进行聚类"""
        clusters = {
            "no_momentum_repair": [],
            "persistent_weakness": [],
            "conflict_or_veto": [],
            "market_drag": [],
            "false_oversold": [],
        }

        for s in failed:
            pre_5d = s.get("pre_5d_return")
            heat_label = s.get("heat_label", "")
            technical_label = s.get("technical_label", "")
            veto = s.get("veto_triggered", False)
            conflict = s.get("conflict_level", "none")
            market_ctx = s.get("dimension_market_context", 0)

            if veto or conflict != "none":
                clusters["conflict_or_veto"].append(s)
            elif pre_5d is not None and pre_5d < -5 and heat_label in ["heat_weak", "heat_fading"]:
                clusters["no_momentum_repair"].append(s)
            elif pre_5d is not None and pre_5d < -3 and technical_label in ["trend_weak"]:
                clusters["persistent_weakness"].append(s)
            elif market_ctx < 0.3:
                clusters["market_drag"].append(s)
            else:
                clusters["false_oversold"].append(s)

        result = {}
        for name, items in clusters.items():
            if items:
                fwd_5d_values = [
                    x["forward_5d_return"]
                    for x in items
                    if x.get("forward_5d_return") is not None
                ]
                avg_5d = sum(fwd_5d_values) / len(fwd_5d_values) if fwd_5d_values else None
                result[name] = {
                    "count": len(items),
                    "avg_forward_5d_return": round(avg_5d, 2) if avg_5d else None,
                    "samples": items[:5],
                }

        return result

    def _aggregate_opportunity_buckets(
        self, samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """按 opportunity_score 分桶聚合"""
        buckets = {"high": [], "medium": [], "low": []}

        for s in samples:
            score = s.get("opportunity_score", 0.0)
            if score >= 0.65:
                buckets["high"].append(s)
            elif score >= 0.40:
                buckets["medium"].append(s)
            else:
                buckets["low"].append(s)

        result = {}
        for name, group in buckets.items():
            if group:
                fwd_5d = [
                    x["forward_5d_return"]
                    for x in group
                    if x.get("forward_5d_return") is not None
                ]
                fwd_10d = [
                    x["forward_10d_return"]
                    for x in group
                    if x.get("forward_10d_return") is not None
                ]
                avg_5d = sum(fwd_5d) / len(fwd_5d) if fwd_5d else None
                avg_10d = sum(fwd_10d) / len(fwd_10d) if fwd_10d else None
                pos_5d = sum(1 for r in fwd_5d if r > 0) / len(fwd_5d) if fwd_5d else None

                # 分数分布
                scores = [x.get("opportunity_score", 0) for x in group]
                result[name] = {
                    "sample_count": len(group),
                    "avg_forward_5d_return": round(avg_5d, 2) if avg_5d else None,
                    "avg_forward_10d_return": round(avg_10d, 2) if avg_10d else None,
                    "positive_rate_5d": round(pos_5d, 2) if pos_5d else None,
                    "score_min": round(min(scores), 2),
                    "score_max": round(max(scores), 2),
                    "score_avg": round(sum(scores) / len(scores), 2),
                }
            else:
                result[name] = {
                    "sample_count": 0,
                    "avg_forward_5d_return": None,
                    "avg_forward_10d_return": None,
                    "positive_rate_5d": None,
                    "score_min": None,
                    "score_max": None,
                    "score_avg": None,
                }

        return result

    def _diagnose_high_bucket(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """诊断 high 桶为空的原因"""
        high_scores = [s for s in samples if s.get("opportunity_score", 0) >= 0.65]
        near_high = [s for s in samples if 0.50 <= s.get("opportunity_score", 0) < 0.65]

        # 分析 opportunity_score 的组成
        # opportunity_score = technical*0.30 + heat*0.25 + rotation*0.20 + market*0.15 + narrative*0.10
        dim_stats = {"technical": [], "heat": [], "rotation": [], "market_context": []}
        for s in samples:
            dim_stats["technical"].append(s.get("dimension_technical", 0))
            dim_stats["heat"].append(s.get("dimension_heat", 0))
            dim_stats["rotation"].append(s.get("dimension_rotation", 0))
            dim_stats["market_context"].append(s.get("dimension_market_context", 0))

        dim_averages = {}
        for dim, values in dim_stats.items():
            if values:
                dim_averages[dim] = round(sum(values) / len(values), 2)
            else:
                dim_averages[dim] = None

        return {
            "high_bucket_count": len(high_scores),
            "near_high_count": len(near_high),
            "dimension_averages": dim_averages,
            "max_opportunity_score": round(
                max((s.get("opportunity_score", 0) for s in samples), default=0), 2
            ),
        }
