"""
分层 Agent 回测

验证分层 Agent 组中每一层、每个 Agent、每类投票、每类 veto、每类 conflict 是否真的有后验解释力。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class AgentLayerBacktest:
    """
    分层 Agent 回测

    验证分层 Agent 组中每一层、每个 Agent、每类投票、每类 veto、每类 conflict 是否真的有后验解释力。
    """

    def __init__(self, history_root: str = "data_cache/sector_history"):
        """
        初始化回测模块

        Args:
            history_root: 历史数据根目录
        """
        self.history_root = history_root

    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        sector_type: str = "industry",
        report_root: str = "reports",
    ) -> Dict[str, Any]:
        """
        运行回测

        Args:
            start_date: 开始日期
            end_date: 结束日期
            sector_type: 板块类型
            report_root: 报告根目录

        Returns:
            回测结果字典
        """
        # 收集多日 sector_research.json
        research_reports = []
        skipped_dates = []

        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

        while current_date <= end_date_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            research_path = os.path.join(report_root, "sector_research", date_str, "sector_research.json")

            if os.path.exists(research_path):
                try:
                    with open(research_path, "r", encoding="utf-8") as f:
                        research_data = json.load(f)
                    research_reports.append({
                        "date": date_str,
                        "data": research_data,
                    })
                except Exception as e:
                    skipped_dates.append({"date": date_str, "reason": f"Failed to load: {str(e)[:100]}"})
            else:
                skipped_dates.append({"date": date_str, "reason": "Missing sector_research.json"})

            current_date += timedelta(days=1)

        # 提取所有样本
        samples = []
        for report in research_reports:
            date_str = report["date"]
            research_data = report["data"]

            for result in research_data.get("research_results", []):
                sector_name = result.get("sector_name", "")
                if not sector_name:
                    continue

                # 计算后续表现
                forward_returns = self._compute_forward_returns(
                    sector_name, date_str, end_date, sector_type
                )

                sample = {
                    "date": date_str,
                    "sector_name": sector_name,
                    "sector_type": result.get("sector_type", sector_type),
                    "consensus_label": result.get("consensus_label", ""),
                    "evidence_score": result.get("evidence_score", 0.0),
                    "opportunity_score": result.get("opportunity_score", 0.0),
                    "risk_control_score": result.get("risk_control_score", 0.0),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "calibrated_confidence_score": result.get("calibrated_confidence_score", 0.0),
                    "ranking_score": result.get("ranking_score", 0.0),
                    "agent_votes": result.get("agent_votes", {}),
                    "agent_opinions": result.get("agent_opinions", []),
                    "conflicts": result.get("conflicts", []),
                    "conflict_summary": result.get("conflict_summary", ""),
                    "conflict_level": result.get("conflict_level", "none"),
                    "veto": result.get("veto", {}),
                    "veto_reasons": result.get("veto_reasons", []),
                    "confidence_calibration": result.get("confidence_calibration", {}),
                    "decision_path": result.get("decision_path", []),
                    "data_coverage_detail": result.get("data_coverage_detail", {}),
                    "forward_returns": forward_returns,
                }
                samples.append(sample)

        # 统计分析
        layer_performance = self._compute_layer_performance(samples)
        agent_performance = self._compute_agent_performance(samples)
        vote_performance = self._compute_vote_performance(samples)
        agent_vote_performance = self._compute_agent_vote_performance(samples)
        conflict_performance = self._compute_conflict_performance(samples)
        conflict_level_performance = self._compute_conflict_level_performance(samples)
        veto_performance = self._compute_veto_performance(samples)
        confidence_calibration_performance = self._compute_confidence_calibration_performance(samples)
        opportunity_confidence_matrix = self._compute_opportunity_confidence_matrix(samples)
        false_positive_by_agent = self._find_false_positive_by_agent(samples)
        missed_opportunity_by_agent = self._find_missed_opportunity_by_agent(samples)

        # 构建结果
        result = {
            "report_type": "agent_layer_backtest",
            "start_date": start_date,
            "end_date": end_date,
            "sector_type": sector_type,
            "input_summary": {
                "research_report_count": len(research_reports),
                "sample_count": len(samples),
                "skipped_dates": skipped_dates,
            },
            "layer_performance": layer_performance,
            "agent_performance": agent_performance,
            "vote_performance": vote_performance,
            "agent_vote_performance": agent_vote_performance,
            "conflict_performance": conflict_performance,
            "conflict_level_performance": conflict_level_performance,
            "veto_performance": veto_performance,
            "confidence_calibration_performance": confidence_calibration_performance,
            "opportunity_confidence_matrix": opportunity_confidence_matrix,
            "false_positive_by_agent": false_positive_by_agent[:10],
            "missed_opportunity_by_agent": missed_opportunity_by_agent[:10],
            "warnings": [],
            "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
        }

        return result

    def _compute_forward_returns(
        self,
        sector_name: str,
        signal_date: str,
        end_date: str,
        sector_type: str,
    ) -> Dict[str, Optional[float]]:
        """
        计算后续表现

        Args:
            sector_name: 板块名称
            signal_date: 信号日期
            end_date: 结束日期
            sector_type: 板块类型

        Returns:
            后续表现字典
        """
        # 读取板块历史数据
        history_path = os.path.join(self.history_root, sector_type, f"{sector_name}.json")

        if not os.path.exists(history_path):
            return {
                "forward_1d_return": None,
                "forward_3d_return": None,
                "forward_5d_return": None,
                "forward_10d_return": None,
                "forward_20d_return": None,
            }

        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            records = history_data.get("records", [])

            # 找到 signal_date 之后的记录
            future_records = []
            for record in records:
                record_date = record.get("日期", "")
                if record_date > signal_date:
                    future_records.append(record)

            if not future_records:
                return {
                    "forward_1d_return": None,
                    "forward_3d_return": None,
                    "forward_5d_return": None,
                    "forward_10d_return": None,
                    "forward_20d_return": None,
                }

            # 计算收益率
            returns = []
            prev_close = None
            for record in future_records:
                close = record.get("收盘价", 0)
                record_prev_close = record.get("前收盘", 0)
                if record_prev_close > 0:
                    prev_close = record_prev_close
                elif prev_close is None:
                    prev_close = close

                if prev_close > 0:
                    ret = (close - prev_close) / prev_close * 100
                else:
                    ret = 0.0
                returns.append(ret)
                prev_close = close

            # 计算 forward returns
            def calc_forward(n):
                if len(returns) >= n:
                    return sum(returns[:n])
                return None

            return {
                "forward_1d_return": calc_forward(1),
                "forward_3d_return": calc_forward(3),
                "forward_5d_return": calc_forward(5),
                "forward_10d_return": calc_forward(10),
                "forward_20d_return": calc_forward(20),
            }

        except Exception:
            return {
                "forward_1d_return": None,
                "forward_3d_return": None,
                "forward_5d_return": None,
                "forward_10d_return": None,
                "forward_20d_return": None,
            }

    def _compute_layer_performance(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算层级表现"""
        # 按层级分组
        layer_groups = {
            "L1_data_evidence": [],
            "L2_specialized": [],
            "L3_conflict_consistency": [],
            "L4_decision": [],
        }

        for sample in samples:
            agent_opinions = sample.get("agent_opinions", [])
            for opinion in agent_opinions:
                layer = opinion.get("layer", "L4_decision")
                if layer in layer_groups:
                    layer_groups[layer].append(sample)

        # 如果没有 agent_opinions，所有样本归入 L4
        if not any(len(v) > 0 for v in layer_groups.values()):
            layer_groups["L4_decision"] = samples

        result = {}
        for layer_name, layer_samples in layer_groups.items():
            if layer_samples:
                result[layer_name] = self._compute_group_stats(layer_samples)

        return result

    def _compute_agent_performance(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算 Agent 表现"""
        # 按 agent_id 分组（从 agent_opinions 中提取）
        agent_groups = {}

        for sample in samples:
            agent_opinions = sample.get("agent_opinions", [])
            if agent_opinions:
                for opinion in agent_opinions:
                    agent_id = opinion.get("agent_id", "")
                    if agent_id:
                        if agent_id not in agent_groups:
                            agent_groups[agent_id] = []
                        agent_groups[agent_id].append(sample)
            else:
                # Fallback: 使用 consensus_label 作为 agent_id
                label = sample.get("consensus_label", "unknown")
                if label not in agent_groups:
                    agent_groups[label] = []
                agent_groups[label].append(sample)

        result = {}
        for agent_id, group in agent_groups.items():
            result[agent_id] = self._compute_group_stats(group)

        return result

    def _compute_vote_performance(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算投票表现"""
        vote_groups = {"positive": [], "neutral": [], "negative": [], "veto": []}

        for sample in samples:
            # 优先使用 agent_opinions 中的投票信息
            agent_opinions = sample.get("agent_opinions", [])
            if agent_opinions:
                # 统计所有 Agent 的投票
                total_positive = sum(1 for op in agent_opinions if op.get("vote") == "positive")
                total_negative = sum(1 for op in agent_opinions if op.get("vote") == "negative")
                total_neutral = sum(1 for op in agent_opinions if op.get("vote") == "neutral")
                total_veto = sum(1 for op in agent_opinions if op.get("veto", False))

                if total_positive > total_negative:
                    vote_groups["positive"].append(sample)
                elif total_negative > total_positive:
                    vote_groups["negative"].append(sample)
                else:
                    vote_groups["neutral"].append(sample)

                if total_veto > 0:
                    vote_groups["veto"].append(sample)
            else:
                # Fallback: 使用 agent_votes
                agent_votes = sample.get("agent_votes", {})
                positive = agent_votes.get("positive_votes", 0)
                negative = agent_votes.get("negative_votes", 0)
                veto = agent_votes.get("veto_votes", 0)

                if positive > negative:
                    vote_groups["positive"].append(sample)
                elif negative > positive:
                    vote_groups["negative"].append(sample)
                else:
                    vote_groups["neutral"].append(sample)

                if veto > 0:
                    vote_groups["veto"].append(sample)

        result = {}
        for vote_type, group in vote_groups.items():
            result[vote_type] = self._compute_group_stats(group)

        return result

    def _compute_agent_vote_performance(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算 Agent 投票表现"""
        # 简化处理：按 consensus_label + vote 组合
        agent_vote_groups = {}

        for sample in samples:
            label = sample.get("consensus_label", "")
            agent_votes = sample.get("agent_votes", {})
            positive = agent_votes.get("positive_votes", 0)
            negative = agent_votes.get("negative_votes", 0)

            if positive > negative:
                vote = "positive"
            elif negative > positive:
                vote = "negative"
            else:
                vote = "neutral"

            key = f"{label}:{vote}"
            if key not in agent_vote_groups:
                agent_vote_groups[key] = []
            agent_vote_groups[key].append(sample)

        result = {}
        for key, group in agent_vote_groups.items():
            result[key] = self._compute_group_stats(group)

        return result

    def _compute_conflict_performance(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算冲突表现"""
        conflict_groups = {}

        for sample in samples:
            conflict_level = sample.get("conflict_level", "none")
            conflicts = sample.get("conflicts", [])
            if conflict_level != "none" or len(conflicts) > 0:
                conflict_type = "has_conflict"
            else:
                conflict_type = "no_conflict"

            if conflict_type not in conflict_groups:
                conflict_groups[conflict_type] = []
            conflict_groups[conflict_type].append(sample)

        result = {}
        for conflict_type, group in conflict_groups.items():
            result[conflict_type] = self._compute_group_stats(group)

        return result

    def _compute_conflict_level_performance(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算冲突等级表现"""
        # 简化处理：按 confidence_score 分桶
        level_groups = {"high": [], "medium": [], "low": []}

        for sample in samples:
            confidence = sample.get("confidence_score", 0.0)
            if confidence >= 0.7:
                level_groups["high"].append(sample)
            elif confidence >= 0.4:
                level_groups["medium"].append(sample)
            else:
                level_groups["low"].append(sample)

        result = {}
        for level, group in level_groups.items():
            result[level] = self._compute_group_stats(group)

        return result

    def _compute_veto_performance(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算 veto 表现"""
        veto_groups = {"veto_true": [], "veto_false": []}

        for sample in samples:
            veto_reasons = sample.get("veto_reasons", [])
            if veto_reasons:
                veto_groups["veto_true"].append(sample)
            else:
                veto_groups["veto_false"].append(sample)

        result = {}
        for veto_type, group in veto_groups.items():
            result[veto_type] = self._compute_group_stats(group)

        return result

    def _compute_confidence_calibration_performance(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算置信度校准表现"""
        bucket_groups = {"high": [], "medium": [], "low": []}

        for sample in samples:
            confidence = sample.get("confidence_score", 0.0)
            if confidence >= 0.7:
                bucket_groups["high"].append(sample)
            elif confidence >= 0.4:
                bucket_groups["medium"].append(sample)
            else:
                bucket_groups["low"].append(sample)

        result = {}
        for bucket, group in bucket_groups.items():
            result[bucket] = self._compute_group_stats(group)

        return result

    def _compute_opportunity_confidence_matrix(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算 opportunity vs confidence 矩阵"""
        matrix = {}

        for sample in samples:
            opp = sample.get("opportunity_score", 0.0)
            conf = sample.get("confidence_score", 0.0)

            opp_bucket = "high" if opp >= 0.6 else "medium" if opp >= 0.3 else "low"
            conf_bucket = "high" if conf >= 0.7 else "medium" if conf >= 0.4 else "low"

            key = f"{opp_bucket}:{conf_bucket}"
            if key not in matrix:
                matrix[key] = []
            matrix[key].append(sample)

        result = {}
        for key, group in matrix.items():
            result[key] = self._compute_group_stats(group)

        return result

    def _find_false_positive_by_agent(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """查找误判样本"""
        false_positives = []

        for sample in samples:
            forward_5d = sample.get("forward_returns", {}).get("forward_5d_return")
            if forward_5d is not None and forward_5d < 0:
                # positive vote 但后续为负
                agent_votes = sample.get("agent_votes", {})
                if agent_votes.get("positive_votes", 0) > 0:
                    false_positives.append({
                        "signal_date": sample.get("date", ""),
                        "sector_name": sample.get("sector_name", ""),
                        "consensus_label": sample.get("consensus_label", ""),
                        "ranking_score": sample.get("ranking_score", 0.0),
                        "forward_5d_return": forward_5d,
                    })

        # 按 forward_5d_return 排序
        false_positives.sort(key=lambda x: x["forward_5d_return"])
        return false_positives

    def _find_missed_opportunity_by_agent(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """查找漏判样本"""
        missed = []

        for sample in samples:
            forward_5d = sample.get("forward_returns", {}).get("forward_5d_return")
            if forward_5d is not None and forward_5d > 3:
                # negative vote 或 weak label 但后续为正
                label = sample.get("consensus_label", "")
                if label in ["weak_or_avoid", "low_signal_noise", "conflicted"]:
                    missed.append({
                        "signal_date": sample.get("date", ""),
                        "sector_name": sample.get("sector_name", ""),
                        "consensus_label": label,
                        "ranking_score": sample.get("ranking_score", 0.0),
                        "forward_5d_return": forward_5d,
                    })

        # 按 forward_5d_return 降序排序
        missed.sort(key=lambda x: x["forward_5d_return"], reverse=True)
        return missed

    def _compute_group_stats(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算分组统计"""
        if not group:
            return {
                "sample_count": 0,
                "avg_forward_1d_return": None,
                "avg_forward_3d_return": None,
                "avg_forward_5d_return": None,
                "avg_forward_10d_return": None,
                "positive_rate_5d": None,
            }

        # 收集 forward returns
        forward_1d = [s["forward_returns"]["forward_1d_return"] for s in group if s["forward_returns"]["forward_1d_return"] is not None]
        forward_3d = [s["forward_returns"]["forward_3d_return"] for s in group if s["forward_returns"]["forward_3d_return"] is not None]
        forward_5d = [s["forward_returns"]["forward_5d_return"] for s in group if s["forward_returns"]["forward_5d_return"] is not None]

        # 计算平均值
        avg_1d = sum(forward_1d) / len(forward_1d) if forward_1d else None
        avg_3d = sum(forward_3d) / len(forward_3d) if forward_3d else None
        avg_5d = sum(forward_5d) / len(forward_5d) if forward_5d else None

        # 计算正收益占比
        positive_5d = sum(1 for r in forward_5d if r > 0) / len(forward_5d) if forward_5d else None

        return {
            "sample_count": len(group),
            "avg_forward_1d_return": round(avg_1d, 4) if avg_1d is not None else None,
            "avg_forward_3d_return": round(avg_3d, 4) if avg_3d is not None else None,
            "avg_forward_5d_return": round(avg_5d, 4) if avg_5d is not None else None,
            "positive_rate_5d": round(positive_5d, 4) if positive_5d is not None else None,
        }
