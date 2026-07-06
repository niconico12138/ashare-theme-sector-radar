"""
Agent 组复盘评估

验证 Agent 组输出的标签、分数和排序是否有复盘价值。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


class SectorResearchBacktest:
    """
    Agent 组复盘评估

    验证 Agent 组输出的标签、分数和排序是否有复盘价值。
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
                    "confirm_level": result.get("confirm_level", ""),
                    "evidence_score": result.get("evidence_score", 0.0),
                    "opportunity_score": result.get("opportunity_score", 0.0),
                    "risk_control_score": result.get("risk_control_score", 0.0),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "ranking_score": result.get("ranking_score", 0.0),
                    "forward_returns": forward_returns,
                }
                samples.append(sample)

        # 聚合分析
        label_performance = self._aggregate_by_label(samples)
        ranking_bucket_performance = self._aggregate_by_bucket(samples, "ranking_score")
        opportunity_bucket_performance = self._aggregate_by_bucket(samples, "opportunity_score")
        confidence_bucket_performance = self._aggregate_by_bucket(samples, "confidence_score")

        # 样本分析
        sample_analysis = self._analyze_samples(samples)

        # 构建结果
        result = {
            "report_type": "sector_research_backtest",
            "start_date": start_date,
            "end_date": end_date,
            "sector_type": sector_type,
            "input_summary": {
                "research_report_count": len(research_reports),
                "sample_count": len(samples),
                "skipped_dates": skipped_dates,
            },
            "label_performance": label_performance,
            "ranking_score_bucket_performance": ranking_bucket_performance,
            "opportunity_score_bucket_performance": opportunity_bucket_performance,
            "confidence_score_bucket_performance": confidence_bucket_performance,
            "sample_analysis": sample_analysis,
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
                # 尝试获取前一日收盘价
                record_prev_close = record.get("前收盘", 0)
                if record_prev_close > 0:
                    prev_close = record_prev_close
                elif prev_close is None:
                    # 如果没有前一日收盘价，使用当前收盘价（第一天）
                    prev_close = close

                if prev_close > 0:
                    ret = (close - prev_close) / prev_close * 100
                else:
                    ret = 0.0
                returns.append(ret)
                prev_close = close  # 更新为当前收盘价

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

        except Exception as e:
            return {
                "forward_1d_return": None,
                "forward_3d_return": None,
                "forward_5d_return": None,
                "forward_10d_return": None,
                "forward_20d_return": None,
            }

    def _aggregate_by_label(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按 consensus_label 聚合

        Args:
            samples: 样本列表

        Returns:
            按标签聚合的结果
        """
        label_groups = {}
        for sample in samples:
            label = sample.get("consensus_label", "")
            if label not in label_groups:
                label_groups[label] = []
            label_groups[label].append(sample)

        result = {}
        for label, group in label_groups.items():
            result[label] = self._compute_group_stats(group)

        return result

    def _aggregate_by_bucket(
        self,
        samples: List[Dict[str, Any]],
        score_field: str,
    ) -> Dict[str, Any]:
        """
        按分数分桶聚合

        Args:
            samples: 样本列表
            score_field: 分数字段名

        Returns:
            按分桶聚合的结果
        """
        buckets = {"high": [], "medium": [], "low": []}

        for sample in samples:
            score = sample.get(score_field, 0.0)
            if score >= 0.65:
                buckets["high"].append(sample)
            elif score >= 0.45:
                buckets["medium"].append(sample)
            else:
                buckets["low"].append(sample)

        result = {}
        for bucket_name, group in buckets.items():
            result[bucket_name] = self._compute_group_stats(group)

        return result

    def _compute_group_stats(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算分组统计

        Args:
            group: 样本列表

        Returns:
            统计结果
        """
        if not group:
            return {
                "sample_count": 0,
                "avg_forward_1d_return": None,
                "avg_forward_3d_return": None,
                "avg_forward_5d_return": None,
                "avg_forward_10d_return": None,
                "avg_forward_20d_return": None,
                "positive_rate_5d": None,
                "positive_rate_10d": None,
            }

        # 收集 forward returns
        forward_1d = [s["forward_returns"]["forward_1d_return"] for s in group if s["forward_returns"]["forward_1d_return"] is not None]
        forward_3d = [s["forward_returns"]["forward_3d_return"] for s in group if s["forward_returns"]["forward_3d_return"] is not None]
        forward_5d = [s["forward_returns"]["forward_5d_return"] for s in group if s["forward_returns"]["forward_5d_return"] is not None]
        forward_10d = [s["forward_returns"]["forward_10d_return"] for s in group if s["forward_returns"]["forward_10d_return"] is not None]
        forward_20d = [s["forward_returns"]["forward_20d_return"] for s in group if s["forward_returns"]["forward_20d_return"] is not None]

        # 计算平均值
        avg_1d = sum(forward_1d) / len(forward_1d) if forward_1d else None
        avg_3d = sum(forward_3d) / len(forward_3d) if forward_3d else None
        avg_5d = sum(forward_5d) / len(forward_5d) if forward_5d else None
        avg_10d = sum(forward_10d) / len(forward_10d) if forward_10d else None
        avg_20d = sum(forward_20d) / len(forward_20d) if forward_20d else None

        # 计算正收益占比
        positive_5d = sum(1 for r in forward_5d if r > 0) / len(forward_5d) if forward_5d else None
        positive_10d = sum(1 for r in forward_10d if r > 0) / len(forward_10d) if forward_10d else None

        return {
            "sample_count": len(group),
            "avg_forward_1d_return": round(avg_1d, 4) if avg_1d is not None else None,
            "avg_forward_3d_return": round(avg_3d, 4) if avg_3d is not None else None,
            "avg_forward_5d_return": round(avg_5d, 4) if avg_5d is not None else None,
            "avg_forward_10d_return": round(avg_10d, 4) if avg_10d is not None else None,
            "avg_forward_20d_return": round(avg_20d, 4) if avg_20d is not None else None,
            "positive_rate_5d": round(positive_5d, 4) if positive_5d is not None else None,
            "positive_rate_10d": round(positive_10d, 4) if positive_10d is not None else None,
        }

    def _analyze_samples(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析样本

        Args:
            samples: 样本列表

        Returns:
            样本分析结果
        """
        # 后续表现较强样本
        best_follow_through = sorted(
            [s for s in samples if s["forward_returns"]["forward_5d_return"] is not None],
            key=lambda x: x["forward_returns"]["forward_5d_return"],
            reverse=True
        )[:5]

        # 后续表现较弱样本
        worst_follow_through = sorted(
            [s for s in samples if s["forward_returns"]["forward_5d_return"] is not None],
            key=lambda x: x["forward_returns"]["forward_5d_return"]
        )[:5]

        # 可能误判样本 (strong/rotation 但后续为负)
        false_positive_candidates = [
            s for s in samples
            if s.get("consensus_label") in ["strong_consensus", "trend_confirmed", "rotation_candidate"]
            and s["forward_returns"]["forward_5d_return"] is not None
            and s["forward_returns"]["forward_5d_return"] < 0
        ]

        # 可能漏判样本 (weak/conflicted 但后续较强)
        missed_opportunity_candidates = [
            s for s in samples
            if s.get("consensus_label") in ["weak_or_avoid", "conflicted"]
            and s["forward_returns"]["forward_5d_return"] is not None
            and s["forward_returns"]["forward_5d_return"] > 3
        ]

        # 高标签可信度样本检查
        high_confidence_samples = [
            s for s in samples
            if s.get("confidence_score", 0) >= 0.75
        ]

        return {
            "best_follow_through": best_follow_through[:5],
            "worst_follow_through": worst_follow_through[:5],
            "false_positive_candidates": false_positive_candidates[:5],
            "missed_opportunity_candidates": missed_opportunity_candidates[:5],
            "high_confidence_label_checks": high_confidence_samples[:5],
        }
