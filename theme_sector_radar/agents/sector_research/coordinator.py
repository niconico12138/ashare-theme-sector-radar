"""
板块综合研判协调器

协调多个 Agent 完成板块综合研判。
支持 L1-L4 分层架构。
"""

import json
import os
from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_DATA_EVIDENCE, LAYER_SPECIALIZED, LAYER_CONFLICT_CONSISTENCY, LAYER_DECISION
from .technical_trend_agent import TechnicalTrendAgent
from .short_term_heat_agent import ShortTermHeatAgent
from .rotation_analysis_agent import RotationAnalysisAgent
from .risk_control_agent import RiskControlAgent
from .data_quality_agent import DataQualityAgent
from .market_context_agent import MarketContextAgent
from .narrative_agent import NarrativeAgent
from .agent_vote_aggregator import AgentVoteAggregator
from .conflict_detection_agent import ConflictDetectionAgent
from .veto_rule_agent import VetoRuleAgent
from .confidence_calibration_agent import ConfidenceCalibrationAgent
from .consensus_decision_agent import ConsensusDecisionAgent
from .market_regime_context import MarketRegimeContext
from .persistence_strength_agent import PersistenceStrengthAgent
from .catalyst_event_agent import CatalystEventAgent


class SectorResearchCoordinator:
    """
    板块综合研判协调器

    协调多个 Agent 完成板块综合研判。
    支持 L1-L4 分层架构。
    """

    def __init__(self):
        """初始化协调器"""
        # L2 专项分析层
        self.technical_agent = TechnicalTrendAgent()
        self.heat_agent = ShortTermHeatAgent()
        self.rotation_agent = RotationAnalysisAgent()
        self.risk_agent = RiskControlAgent()
        self.data_quality_agent = DataQualityAgent()
        self.market_context_agent = MarketContextAgent()
        self.narrative_agent = NarrativeAgent()
        self.persistence_agent = PersistenceStrengthAgent()
        self.catalyst_agent = CatalystEventAgent()

        # L3 分歧与一致性层
        self.vote_aggregator = AgentVoteAggregator()
        self.conflict_detection_agent = ConflictDetectionAgent()
        self.veto_rule_agent = VetoRuleAgent()
        self.confidence_calibration_agent = ConfidenceCalibrationAgent()

        # L4 最终决策层
        self.consensus_agent = ConsensusDecisionAgent()

    def _build_decision_path(
        self,
        data_quality_view: Dict[str, Any],
        technical_view: Dict[str, Any],
        heat_view: Dict[str, Any],
        rotation_view: Dict[str, Any],
        conflict_opinion: AgentOpinion,
        veto_opinion: AgentOpinion,
        consensus_result: Dict[str, Any],
    ) -> List[str]:
        """
        构建决策路径

        Args:
            data_quality_view: 数据质量视图
            technical_view: 技术面视图
            heat_view: 短线热度视图
            rotation_view: 轮动视图
            conflict_opinion: 冲突检测结果
            veto_opinion: Veto 结果
            consensus_result: 共识结果

        Returns:
            决策路径列表
        """
        path = []

        # 数据质量
        data_label = data_quality_view.get("data_quality_label", "")
        if data_label in ["data_reliable", "data_ok"]:
            path.append("数据可用")
        elif data_label in ["data_usable", "data_partial"]:
            path.append("数据部分可用")
        else:
            path.append("数据不足或不可靠")

        # 专项 Agent 分析
        technical_label = technical_view.get("technical_label", "")
        heat_label = heat_view.get("heat_label", "")
        rotation_label = rotation_view.get("rotation_label", "")

        if technical_label in ["trend_confirmed", "trend_forming"]:
            path.append("技术面趋势确认")
        elif technical_label in ["trend_weak", "trend_unreliable"]:
            path.append("技术面趋势偏弱")

        if heat_label in ["heat_active", "heat_moderate"]:
            path.append("短线热度活跃")
        elif heat_label in ["heat_fading", "heat_weak"]:
            path.append("短线热度偏弱")

        if rotation_label in ["rotation_rising", "rotation_improving"]:
            path.append("轮动升温")
        elif rotation_label in ["rotation_weakening", "rotation_lagging"]:
            path.append("轮动降温")

        # 冲突检测
        conflict_level = conflict_opinion.metadata.get("conflict_level", "none")
        if conflict_level != "none":
            path.append(f"检测到冲突 (level={conflict_level})")

        # Veto
        veto_triggered = veto_opinion.metadata.get("veto_triggered", False)
        if veto_triggered:
            path.append("Veto 触发，降权处理")

        # 最终决策
        consensus_label = consensus_result.get("consensus_label", "")
        path.append(f"输出标签: {consensus_label}")

        return path

    def _build_data_coverage_detail(self, data_quality_view: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建数据覆盖详情

        Args:
            data_quality_view: 数据质量视图

        Returns:
            数据覆盖详情字典
        """
        return {
            "data_quality_label": data_quality_view.get("data_quality_label", ""),
            "data_quality_score": data_quality_view.get("data_quality_score", 0.0),
            "history_coverage": data_quality_view.get("history_coverage", 0.0),
            "history_days": data_quality_view.get("history_days", 0),
            "data_reliability_summary": data_quality_view.get("data_reliability_summary", ""),
        }

    def _convert_to_opinions(
        self,
        agent_views: List[tuple],
    ) -> List[AgentOpinion]:
        """
        将 Agent 字典视图转换为 AgentOpinion 对象列表

        Args:
            agent_views: Agent 视图列表 [(agent_id, view_dict), ...]
        Returns:
            AgentOpinion 对象列表
        """
        from .opinion import AGENT_SIGNAL_PROFILES

        opinions = []

        for agent_id, view_dict in agent_views:
            if not isinstance(view_dict, dict):
                continue

            # 确定层级
            layer = LAYER_SPECIALIZED
            if "data" in agent_id or "evidence" in agent_id:
                layer = LAYER_DATA_EVIDENCE

            # 确定标签
            label = view_dict.get(
                f"{agent_id.replace('_', '_')}_label",
                view_dict.get("label", "unknown")
            )

            # 确定分数
            score = view_dict.get(
                f"{agent_id.replace('_', '_')}_score",
                view_dict.get("score", 0.5)
            )

            # 确定投票
            vote = view_dict.get("vote", "neutral")

            # Phase B: 从 view_dict 提取完整元数据
            evidence = view_dict.get("evidence", [])
            warnings = view_dict.get("warnings", [])
            veto = view_dict.get("veto", False)
            veto_reason = view_dict.get("veto_reason", "")
            metadata = view_dict.get("metadata", {})

            # Phase B: 根据 signal_profile 确定 decision_impact
            signal_profile = AGENT_SIGNAL_PROFILES.get(agent_id, "")
            decision_impact = "participates"
            if signal_profile == "low_information":
                decision_impact = "excluded"

            # Phase B: confidence 从 view_dict 取，不再硬编码
            # 低信息 Agent 默认低 confidence
            default_confidence = 0.3 if signal_profile == "low_information" else 0.7
            confidence = view_dict.get("confidence", default_confidence)
            if not isinstance(confidence, (int, float)):
                confidence = default_confidence

            opinion = AgentOpinion(
                agent_id=agent_id,
                layer=layer,
                label=str(label),
                score=float(score) if isinstance(score, (int, float)) else 0.5,
                confidence=float(confidence),
                evidence=evidence if isinstance(evidence, list) else [],
                warnings=warnings if isinstance(warnings, list) else [],
                vote=vote if vote in ["positive", "neutral", "negative"] else "neutral",
                veto=bool(veto),
                veto_reason=str(veto_reason),
                metadata=metadata if isinstance(metadata, dict) else {},
                signal_profile=signal_profile,
                decision_impact=decision_impact,
            )

            opinions.append(opinion)

        return opinions

    def research_sectors(
        self,
        sector_scores: Dict[str, Any],
        multi_window_consensus: Dict[str, Any],
        market_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        综合研判板块

        Args:
            sector_scores: sector_scores 数据
            multi_window_consensus: 多窗口共识数据
            market_data: 市场数据

        Returns:
            研判结果列表
        """
        results = []

        # 获取 10 日窗口的 sector_scores
        scores_by_sector = {}
        for score in sector_scores.get("scores", []):
            sector_name = score.get("sector_name", "")
            if sector_name:
                scores_by_sector[sector_name] = score

        # 获取多窗口共识
        consensus_by_sector = {}
        for item in multi_window_consensus.get("consensus", []):
            sector_name = item.get("sector_name", "")
            if sector_name:
                consensus_by_sector[sector_name] = item

        # 加载 regime 信息（从 theme_sector_radar.json）
        signal_date = sector_scores.get("as_of_date", "")
        radar_data = self._load_radar_data(signal_date) if signal_date else None
        regime_context = {}
        if radar_data:
            breadth = radar_data.get("market_breadth", {})
            regime_context = {
                "regime_composite_label": self._infer_composite_regime(breadth),
                "breadth_regime": breadth.get("breadth_label", "breadth_unknown"),
                "market_temperature_regime": self._infer_temp_regime(breadth),
            }

        # 加载 research_index（用于 persistence agent）
        research_index = self._load_research_index()

        # 对每个板块进行综合研判
        for sector_name, score_data in scores_by_sector.items():
            try:
                sector_type = score_data.get("sector_type", "industry")
                consensus_data = consensus_by_sector.get(sector_name, {})

                # 合并 market_data with regime info
                enriched_market_data = {**(market_data or {}), **regime_context}

                # 调用各个 Agent
                technical_view = self.technical_agent.analyze(
                    sector_name, sector_type, score_data, consensus_data
                )

                heat_view = self.heat_agent.analyze(
                    sector_name, sector_type, score_data
                )

                rotation_view = self.rotation_agent.analyze(
                    sector_name, sector_type, score_data, consensus_data
                )

                risk_view = self.risk_agent.analyze(
                    sector_name, sector_type, score_data
                )

                data_quality_view = self.data_quality_agent.analyze(
                    sector_name, sector_type, score_data
                )

                market_context_view = self.market_context_agent.analyze(
                    sector_name, sector_type, score_data, enriched_market_data
                )

                narrative_view = self.narrative_agent.analyze(
                    sector_name, sector_type
                )

                # PersistenceStrengthAgent（基于多日 timeline）
                sector_timeline = self._build_sector_timeline(
                    sector_name, research_index, signal_date
                )
                # Phase B: 修复 — 传入空 dict 而非过期的 result 变量
                persistence_opinion = self.persistence_agent.analyze(
                    sector_name, sector_type, {},
                    sector_timeline, daily_summary=None, research_index=research_index,
                )

                # CatalystEventAgent（report-only，读取事件缓存）
                catalyst_events = self._load_catalyst_events(signal_date)
                catalyst_opinion = self.catalyst_agent.analyze(
                    sector_name, sector_type, signal_date,
                    {}, catalyst_events, None,
                )

                # L3 分歧与一致性层
                # 将字典转换为 AgentOpinion 对象
                all_opinions = self._convert_to_opinions([
                    ("technical_trend", technical_view),
                    ("short_term_heat", heat_view),
                    ("rotation_analysis", rotation_view),
                    ("risk_control", risk_view),
                    ("data_quality", data_quality_view),
                    ("market_context", market_context_view),
                    ("narrative", narrative_view),
                ])
                # 添加 persistence_strength opinion
                all_opinions.append(persistence_opinion)
                # 添加 catalyst_event opinion (report-only)
                all_opinions.append(catalyst_opinion)

                # 投票聚合
                vote_opinion = self.vote_aggregator.aggregate(all_opinions)

                # 冲突检测
                conflict_opinion = self.conflict_detection_agent.detect(all_opinions)

                # Veto 规则
                veto_opinion = self.veto_rule_agent.apply_veto(
                    all_opinions, score_data, conflict_opinion.metadata.get("conflict_level", "none")
                )

                # 置信度校准
                confidence_opinion = self.confidence_calibration_agent.calibrate(
                    score_data, vote_opinion, conflict_opinion, veto_opinion
                )

                # 最终共识
                consensus_result = self.consensus_agent.analyze(
                    sector_name,
                    sector_type,
                    technical_view,
                    heat_view,
                    rotation_view,
                    risk_view,
                    data_quality_view,
                    market_context_view,
                    narrative_view,
                )

                # 组合结果
                result = {
                    "sector_name": sector_name,
                    "sector_type": sector_type,
                    "consensus_label": consensus_result["consensus_label"],
                    "confirm_level": consensus_result["confirm_level"],
                    "evidence_score": consensus_result["evidence_score"],
                    "opportunity_score": consensus_result["opportunity_score"],
                    "risk_control_score": consensus_result["risk_control_score"],
                    "confidence_score": consensus_result["confidence_score"],
                    "calibrated_confidence_score": confidence_opinion.metadata.get("calibrated_confidence_score", 0.0),
                    "ranking_score": consensus_result["ranking_score"],
                    "dimension_scores": consensus_result["dimension_scores"],
                    "views": {
                        "technical": technical_view,
                        "heat": heat_view,
                        "rotation": rotation_view,
                        "risk": risk_view,
                        "data_quality": data_quality_view,
                        "market_context": market_context_view,
                        "narrative": narrative_view,
                    },
                    "main_reasons": consensus_result["main_reasons"],
                    "conflict_points": consensus_result["conflict_points"],
                    "watch_points": consensus_result["watch_points"],
                    "data_warnings": consensus_result["data_warnings"],
                    # 新增层级信息
                    "agent_votes": vote_opinion.metadata,
                    "agent_opinions": [op.to_dict() for op in all_opinions],
                    "conflicts": conflict_opinion.metadata.get("conflicts", []),
                    "conflict_summary": conflict_opinion.metadata.get("conflict_summary", ""),
                    "conflict_level": conflict_opinion.metadata.get("conflict_level", "none"),
                    "veto": veto_opinion.metadata,
                    "veto_reasons": veto_opinion.metadata.get("veto_reasons", []),
                    "confidence_calibration": confidence_opinion.metadata,
                    "calibrated_confidence_factors": confidence_opinion.metadata.get("confidence_factors", {}),
                    "decision_path": self._build_decision_path(
                        data_quality_view, technical_view, heat_view, rotation_view,
                        conflict_opinion, veto_opinion, consensus_result
                    ),
                    "data_coverage_detail": self._build_data_coverage_detail(data_quality_view),
                }

                results.append(result)

            except Exception as e:
                # 单板块失败不影响其他板块
                results.append({
                    "sector_name": sector_name,
                    "sector_type": score_data.get("sector_type", "industry"),
                    "consensus_label": "insufficient_data",
                    "confirm_level": "very_low",
                    "confidence_score": 0.0,
                    "dimension_scores": {},
                    "views": {},
                    "main_reasons": [],
                    "conflict_points": [f"分析失败: {str(e)[:100]}"],
                    "watch_points": [],
                    "data_warnings": [f"分析失败: {str(e)[:100]}"],
                })

        # 按 ranking_score 排序，insufficient_data 排后面
        def sort_key(item):
            if item.get("consensus_label") == "insufficient_data":
                return (0, 0.0, 0.0)
            return (1, item.get("ranking_score", 0.0), item.get("opportunity_score", 0.0))

        results.sort(key=sort_key, reverse=True)

        # 注入 Market Regime 解释层（不参与决策）
        signal_date = sector_scores.get("as_of_date", "")
        if signal_date:
            self._inject_market_regime_context(results, signal_date)

        return results

    def _inject_market_regime_context(
        self,
        results: List[Dict[str, Any]],
        signal_date: str,
    ):
        """
        注入 Market Regime 解释层（不参与 vote/veto/scoring）

        Args:
            results: 研判结果列表
            signal_date: 信号日期
        """
        # 尝试加载 theme_sector_radar.json
        radar_data = self._load_radar_data(signal_date)

        regime_context_gen = MarketRegimeContext()
        regime_context = regime_context_gen.generate_regime_context(
            signal_date, radar_data
        )

        for result in results:
            if result.get("consensus_label") == "insufficient_data":
                result["market_regime"] = regime_context_gen._empty_context()
                result["regime_interpretation"] = {
                    "summary": "数据不足，无法生成市场状态解释。",
                    "label_context": "",
                    "watch_points": [],
                    "warnings": ["数据不足"],
                }
                continue

            # 生成 regime 解释
            interpretation = regime_context_gen.generate_regime_interpretation(
                regime_context, result.get("consensus_label", "")
            )

            result["market_regime"] = regime_context
            result["regime_interpretation"] = interpretation

    def _load_radar_data(self, signal_date: str) -> Optional[Dict[str, Any]]:
        """
        加载 theme_sector_radar.json

        Args:
            signal_date: 信号日期

        Returns:
            theme_sector_radar.json 数据，如果找不到返回 None
        """
        # 尝试多个可能的路径
        possible_paths = [
            os.path.join("reports", "theme_sector_radar", signal_date, "theme_sector_radar.json"),
            os.path.join(self.report_root, "theme_sector_radar", signal_date, "theme_sector_radar.json") if hasattr(self, 'report_root') else None,
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    continue

        return None

    def _infer_composite_regime(self, breadth: Dict[str, Any]) -> str:
        """从 breadth 推断 composite regime"""
        avg_change = breadth.get("average_industry_change_pct", 0)
        up_ratio = breadth.get("industry_up_ratio", 0)

        if up_ratio >= 0.6 and avg_change > 0.5:
            return "risk_on"
        elif up_ratio <= 0.3 and avg_change < -0.5:
            return "risk_off"
        elif breadth.get("breadth_label") == "mixed_breadth":
            return "choppy_market"
        elif breadth.get("breadth_label") == "broad_falling":
            return "risk_off"
        elif breadth.get("breadth_label") == "broad_rising":
            return "risk_on"
        else:
            return "choppy_market"

    def _infer_temp_regime(self, breadth: Dict[str, Any]) -> str:
        """从 breadth 推断 temperature regime"""
        avg_change = breadth.get("average_industry_change_pct", 0)
        up_ratio = breadth.get("industry_up_ratio", 0)

        if up_ratio >= 0.7 and avg_change > 1.0:
            return "market_hot"
        elif up_ratio >= 0.55 and avg_change > 0:
            return "market_warm"
        elif up_ratio <= 0.3 and avg_change < -1.0:
            return "market_cold"
        else:
            return "market_cool"

    def _load_research_index(self) -> Optional[Dict[str, Any]]:
        """加载 research_index.json"""
        possible_paths = [
            os.path.join("reports", "sector_research", "index", "research_index.json"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    continue

        return None

    def _load_catalyst_events(self, signal_date: str) -> List[Dict[str, Any]]:
        """加载催化事件缓存"""
        cache_path = os.path.join("data_cache", "catalyst_events", signal_date, "events.json")
        if not os.path.exists(cache_path):
            return []

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("events", [])
        except Exception:
            return []

    def _build_sector_timeline(
        self,
        sector_name: str,
        research_index: Optional[Dict[str, Any]],
        current_date: str,
    ) -> List[Dict[str, Any]]:
        """构建板块 timeline"""
        if not research_index:
            return []

        score_trends = research_index.get("score_trends", {})
        sector_trends = score_trends.get(sector_name, {})

        if not sector_trends:
            return []

        # 获取 ranking_score 历史
        ranking_history = sector_trends.get("ranking_score", [])
        opportunity_history = sector_trends.get("opportunity_score", [])

        # 构建 timeline
        timeline = []
        for entry in ranking_history:
            date = entry.get("date", "")
            if date > current_date:
                continue

            # 查找对应的 opportunity_score
            opp_score = 0.0
            for opp in opportunity_history:
                if opp.get("date") == date:
                    opp_score = opp.get("value", 0.0)
                    break

            # 查找当日是否在 top_watch_names 中
            is_top_watch = False
            # 从 research_index 的 sector_frequency 中获取
            freq = research_index.get("sector_frequency", {})
            if sector_name in freq:
                if date in freq[sector_name].get("dates", []):
                    is_top_watch = True

            timeline.append({
                "date": date,
                "ranking_score": entry.get("value", 0.0),
                "opportunity_score": opp_score,
                "confidence_score": 0.6,  # 默认值
                "is_top_watch": is_top_watch,
                "consensus_label": "",  # 需要从 sector_research.json 获取
                "conflict_level": "none",
                "veto_triggered": False,
                "risk_control_score": 1.0,
                "market_regime": {},
            })

        return timeline
