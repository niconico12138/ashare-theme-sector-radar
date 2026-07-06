"""
Agent 可靠性评估

评估每个 Agent 的 vote 与后续表现是否一致。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..agents.sector_research.opinion import AGENT_SIGNAL_PROFILES, SIGNAL_PROFILE_DESCRIPTIONS


class AgentReliability:
    """
    Agent 可靠性评估

    评估每个 Agent 的 vote 与后续表现是否一致。
    """

    def __init__(
        self,
        history_root: str = "data_cache/sector_history",
    ):
        self.history_root = history_root

    def run_analysis(
        self,
        start_date: str,
        end_date: str,
        sector_type: str = "industry",
        report_root: str = "reports",
    ) -> Dict[str, Any]:
        """
        运行 Agent 可靠性分析

        Args:
            start_date: 开始日期
            end_date: 结束日期
            sector_type: 板块类型
            report_root: 报告根目录

        Returns:
            分析结果
        """
        # 收集所有样本
        samples = self._collect_samples(start_date, end_date, sector_type, report_root)

        if not samples:
            return {
                "report_type": "agent_reliability",
                "start_date": start_date,
                "end_date": end_date,
                "total_samples": 0,
                "agents": {},
                "warnings": ["No samples found"],
            }

        # 按 agent_id 聚合
        agent_stats = self._aggregate_by_agent(samples)

        # 计算可靠性评分
        for agent_id, stats in agent_stats.items():
            stats["reliability_score"] = self._compute_reliability_score(stats)
            stats["reliability_label"] = self._get_reliability_label(stats["reliability_score"], stats["sample_count"])
            stats["diagnosis"] = self._generate_diagnosis(stats)

        # 识别误判样本
        misidentifications = self._identify_misidentifications(samples)

        # 按 regime 分层
        regime_performance = self._aggregate_by_regime(samples)

        # 排序
        sorted_agents = dict(
            sorted(agent_stats.items(), key=lambda x: -x[1].get("reliability_score", 0))
        )

        result = {
            "report_type": "agent_reliability",
            "start_date": start_date,
            "end_date": end_date,
            "sector_type": sector_type,
            "total_samples": len(samples),
            "agents": sorted_agents,
            "misidentifications": misidentifications,
            "regime_performance": regime_performance,
            "warnings": [],
        }

        return result

    def _collect_samples(
        self,
        start_date: str,
        end_date: str,
        sector_type: str,
        report_root: str,
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

                    # 获取 regime
                    regime = "unknown_regime"
                    for result in data.get("research_results", []):
                        mr = result.get("market_regime", {})
                        if mr and mr.get("regime_composite_label"):
                            regime = mr["regime_composite_label"]
                            break

                    for result in data.get("research_results", []):
                        sector_name = result.get("sector_name", "")
                        if not sector_name:
                            continue

                        # 计算 forward returns
                        forward_returns = self._compute_forward_returns(
                            sector_name, date_str, end_date, sector_type
                        )

                        # 提取 agent opinions
                        agent_opinions = result.get("agent_opinions", [])

                        for opinion in agent_opinions:
                            agent_id = opinion.get("agent_id", "")
                            if not agent_id:
                                continue

                            sample = {
                                "signal_date": date_str,
                                "sector_name": sector_name,
                                "agent_id": agent_id,
                                "layer": opinion.get("layer", ""),
                                "vote": opinion.get("vote", "neutral"),
                                "confidence": opinion.get("confidence", 0.5),
                                "consensus_label": result.get("consensus_label", ""),
                                "ranking_score": result.get("ranking_score", 0),
                                "opportunity_score": result.get("opportunity_score", 0),
                                "confidence_score": result.get("confidence_score", 0),
                                "market_regime": regime,
                                "forward_returns": forward_returns,
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

    def _aggregate_by_agent(self, samples: List[Dict]) -> Dict[str, Dict]:
        """按 agent_id 聚合"""
        agent_stats = {}

        for sample in samples:
            agent_id = sample["agent_id"]
            if agent_id not in agent_stats:
                signal_profile = AGENT_SIGNAL_PROFILES.get(agent_id, "broad_signal")
                agent_stats[agent_id] = {
                    "agent_id": agent_id,
                    "layer": sample["layer"],
                    "signal_profile": signal_profile,
                    "signal_profile_description": SIGNAL_PROFILE_DESCRIPTIONS.get(signal_profile, ""),
                    "sample_count": 0,
                    "vote_distribution": {"positive": 0, "neutral": 0, "negative": 0},
                    "vote_performance": {},
                    "regime_performance": {},
                }

            stats = agent_stats[agent_id]
            stats["sample_count"] += 1

            vote = sample["vote"]
            stats["vote_distribution"][vote] = stats["vote_distribution"].get(vote, 0) + 1

            # 按 vote 聚合 forward returns
            if vote not in stats["vote_performance"]:
                stats["vote_performance"][vote] = {
                    "sample_count": 0,
                    "forward_1d": [],
                    "forward_3d": [],
                    "forward_5d": [],
                }

            vp = stats["vote_performance"][vote]
            vp["sample_count"] += 1

            fr = sample["forward_returns"]
            if fr.get("forward_1d_return") is not None:
                vp["forward_1d"].append(fr["forward_1d_return"])
            if fr.get("forward_3d_return") is not None:
                vp["forward_3d"].append(fr["forward_3d_return"])
            if fr.get("forward_5d_return") is not None:
                vp["forward_5d"].append(fr["forward_5d_return"])

            # 按 regime 聚合
            regime = sample["market_regime"]
            if regime not in stats["regime_performance"]:
                stats["regime_performance"][regime] = {
                    "sample_count": 0,
                    "forward_5d": [],
                }
            stats["regime_performance"][regime]["sample_count"] += 1
            if fr.get("forward_5d_return") is not None:
                stats["regime_performance"][regime]["forward_5d"].append(fr["forward_5d_return"])

        # 计算平均值
        for agent_id, stats in agent_stats.items():
            for vote, vp in stats["vote_performance"].items():
                if vp["forward_1d"]:
                    vp["forward_1d_avg"] = round(sum(vp["forward_1d"]) / len(vp["forward_1d"]), 2)
                if vp["forward_3d"]:
                    vp["forward_3d_avg"] = round(sum(vp["forward_3d"]) / len(vp["forward_3d"]), 2)
                if vp["forward_5d"]:
                    vp["forward_5d_avg"] = round(sum(vp["forward_5d"]) / len(vp["forward_5d"]), 2)
                    vp["forward_5d_positive_ratio"] = round(
                        sum(1 for r in vp["forward_5d"] if r > 0) / len(vp["forward_5d"]), 2
                    )
                # 清理原始数据
                del vp["forward_1d"]
                del vp["forward_3d"]
                del vp["forward_5d"]

            for regime, rp in stats["regime_performance"].items():
                if rp["forward_5d"]:
                    rp["forward_5d_avg"] = round(sum(rp["forward_5d"]) / len(rp["forward_5d"]), 2)
                    rp["forward_5d_positive_ratio"] = round(
                        sum(1 for r in rp["forward_5d"] if r > 0) / len(rp["forward_5d"]), 2
                    )
                del rp["forward_5d"]

        return agent_stats

    def _compute_reliability_score(self, stats: Dict) -> float:
        """计算可靠性评分 (0-1)"""
        vote_perf = stats.get("vote_performance", {})
        sample_count = stats.get("sample_count", 0)

        if sample_count < 10:
            return 0.0

        # 1. positive vote 是否优于 negative vote
        pos_5d = vote_perf.get("positive", {}).get("forward_5d_avg")
        neg_5d = vote_perf.get("negative", {}).get("forward_5d_avg")
        neu_5d = vote_perf.get("neutral", {}).get("forward_5d_avg")

        separation_score = 0.0
        if pos_5d is not None and neg_5d is not None:
            if pos_5d > neg_5d:
                separation_score = min(1.0, (pos_5d - neg_5d) / 5.0)
            else:
                separation_score = max(0.0, 0.5 - (neg_5d - pos_5d) / 5.0)

        # 2. vote 分布是否过于单一
        dist = stats.get("vote_distribution", {})
        total = sum(dist.values())
        if total > 0:
            max_ratio = max(dist.values()) / total
            diversity_score = 1.0 - max_ratio
        else:
            diversity_score = 0.0

        # 3. sample_count 加权
        sample_score = min(1.0, sample_count / 100)

        # 综合评分
        score = separation_score * 0.5 + diversity_score * 0.2 + sample_score * 0.3
        return round(max(0.0, min(1.0, score)), 2)

    def _get_reliability_label(self, score: float, sample_count: int) -> str:
        """获取可靠性标签"""
        if sample_count < 10:
            return "insufficient_samples"
        if score >= 0.6:
            return "high_reliability"
        elif score >= 0.4:
            return "moderate_reliability"
        else:
            return "low_reliability"

    def _generate_diagnosis(self, stats: Dict) -> str:
        """生成诊断说明"""
        vote_perf = stats.get("vote_performance", {})
        pos_5d = vote_perf.get("positive", {}).get("forward_5d_avg")
        neg_5d = vote_perf.get("negative", {}).get("forward_5d_avg")

        if pos_5d is not None and neg_5d is not None:
            if pos_5d > neg_5d:
                return f"positive vote has higher forward returns ({pos_5d:.2f}%) than negative ({neg_5d:.2f}%)"
            else:
                return f"negative vote has higher forward returns ({neg_5d:.2f}%) than positive ({pos_5d:.2f}%)"

        return "insufficient data for diagnosis"

    def _identify_misidentifications(self, samples: List[Dict]) -> Dict[str, List]:
        """识别误判样本"""
        result = {
            "positive_false_signal": [],
            "negative_missed_signal": [],
            "neutral_missed_move": [],
        }

        for s in samples:
            fr = s.get("forward_returns", {})
            fwd_5d = fr.get("forward_5d_return")
            if fwd_5d is None:
                continue

            vote = s.get("vote", "neutral")

            # positive_false_signal: vote=positive but forward_5d < -2%
            if vote == "positive" and fwd_5d < -2.0:
                result["positive_false_signal"].append({
                    "signal_date": s["signal_date"],
                    "sector_name": s["sector_name"],
                    "agent_id": s["agent_id"],
                    "forward_5d_return": round(fwd_5d, 2),
                })

            # negative_missed_signal: vote=negative but forward_5d > 3%
            if vote == "negative" and fwd_5d > 3.0:
                result["negative_missed_signal"].append({
                    "signal_date": s["signal_date"],
                    "sector_name": s["sector_name"],
                    "agent_id": s["agent_id"],
                    "forward_5d_return": round(fwd_5d, 2),
                })

            # neutral_missed_move: vote=neutral but |forward_5d| > 5%
            if vote == "neutral" and abs(fwd_5d) > 5.0:
                result["neutral_missed_move"].append({
                    "signal_date": s["signal_date"],
                    "sector_name": s["sector_name"],
                    "agent_id": s["agent_id"],
                    "forward_5d_return": round(fwd_5d, 2),
                })

        # 限制每个类别最多 20 个
        for key in result:
            result[key] = sorted(result[key], key=lambda x: abs(x["forward_5d_return"]), reverse=True)[:20]

        return result

    def _aggregate_by_regime(self, samples: List[Dict]) -> Dict[str, Dict]:
        """按 regime 聚合"""
        regime_stats = {}

        for s in samples:
            regime = s.get("market_regime", "unknown_regime")
            if regime not in regime_stats:
                regime_stats[regime] = {
                    "sample_count": 0,
                    "agents": {},
                }

            rs = regime_stats[regime]
            rs["sample_count"] += 1

            agent_id = s["agent_id"]
            if agent_id not in rs["agents"]:
                rs["agents"][agent_id] = {
                    "sample_count": 0,
                    "vote_distribution": {"positive": 0, "neutral": 0, "negative": 0},
                    "forward_5d": [],
                }

            agent_rs = rs["agents"][agent_id]
            agent_rs["sample_count"] += 1
            vote = s["vote"]
            agent_rs["vote_distribution"][vote] = agent_rs["vote_distribution"].get(vote, 0) + 1

            fwd_5d = s.get("forward_returns", {}).get("forward_5d_return")
            if fwd_5d is not None:
                agent_rs["forward_5d"].append(fwd_5d)

        # 计算平均值
        for regime, rs in regime_stats.items():
            for agent_id, agent_rs in rs["agents"].items():
                if agent_rs["forward_5d"]:
                    agent_rs["forward_5d_avg"] = round(
                        sum(agent_rs["forward_5d"]) / len(agent_rs["forward_5d"]), 2
                    )
                del agent_rs["forward_5d"]

        return regime_stats
