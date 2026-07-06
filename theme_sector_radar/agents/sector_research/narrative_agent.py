"""
产业叙事智能体

从产业叙事角度分析板块，输出叙事标签和摘要。
"""

from typing import Any, Dict, List


# 板块类型映射
SECTOR_NARRATIVE_MAP = {
    # 科技成长
    "半导体": "technology_growth",
    "芯片": "technology_growth",
    "人工智能": "technology_growth",
    "机器人": "technology_growth",
    "CPO": "technology_growth",
    "光模块": "technology_growth",
    "存储": "technology_growth",
    "消费电子": "technology_growth",

    # 医药防御修复
    "医疗服务": "healthcare_defensive_recovery",
    "生物制品": "healthcare_defensive_recovery",
    "化学制药": "healthcare_defensive_recovery",
    "中药": "healthcare_defensive_recovery",
    "医疗器械": "healthcare_defensive_recovery",
    "医药商业": "healthcare_defensive_recovery",
    "医药": "healthcare_defensive_recovery",

    # 金融稳定
    "保险": "financial_stability",
    "银行": "financial_stability",
    "证券": "financial_stability",
    "多元金融": "financial_stability",

    # 新能源周期
    "新能源汽车": "new_energy_cycle",
    "电池": "new_energy_cycle",
    "光伏": "new_energy_cycle",
    "锂电池": "new_energy_cycle",
    "风电": "new_energy_cycle",
    "储能": "new_energy_cycle",

    # 消费复苏
    "白酒": "consumption_recovery",
    "食品饮料": "consumption_recovery",
    "家电": "consumption_recovery",
    "白色家电": "consumption_recovery",
    "小家电": "consumption_recovery",
    "美容护理": "consumption_recovery",
}

# 叙事文本
NARRATIVE_TEXTS = {
    "technology_growth": "科技成长属性，关注行业周期、技术迭代、资本开支和风险偏好。",
    "healthcare_defensive_recovery": "防御修复属性，关注行业景气、政策边际变化和估值修复。",
    "financial_stability": "金融稳定属性，关注宏观经济、利率环境和资产质量。",
    "new_energy_cycle": "新能源周期属性，关注产能扩张、技术进步和需求变化。",
    "consumption_recovery": "消费复苏属性，关注消费信心、渠道库存和季节性因素。",
    "general_sector": "行业属性，关注基本面变化和行业趋势。",
}


class NarrativeAgent:
    """
    产业叙事智能体

    基于板块名称做简单映射，输出产业叙事标签和摘要。
    第一版为规则型，不联网，不接 LLM。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def analyze(
        self,
        sector_name: str,
        sector_type: str,
    ) -> Dict[str, Any]:
        """
        分析产业叙事

        Args:
            sector_name: 板块名称
            sector_type: 板块类型

        Returns:
            产业叙事分析结果
        """
        # 确定叙事标签
        narrative_label = self._determine_label(sector_name)

        # 生成叙事摘要
        narrative_summary = self._generate_summary(narrative_label)

        # 生成观察要点
        narrative_watch_points = self._generate_watch_points(narrative_label)

        # 当前版本没有外部事件数据，默认 neutral
        # low_information_agent 标记表示此 Agent 信息量有限
        vote = "neutral"

        return {
            "narrative_label": narrative_label,
            "narrative_summary": narrative_summary,
            "narrative_watch_points": narrative_watch_points,
            "vote": vote,
            "low_information_agent": True,
        }

    def _determine_label(self, sector_name: str) -> str:
        """确定叙事标签"""
        # 直接匹配
        if sector_name in SECTOR_NARRATIVE_MAP:
            return SECTOR_NARRATIVE_MAP[sector_name]

        # 模糊匹配
        for keyword, label in SECTOR_NARRATIVE_MAP.items():
            if keyword in sector_name:
                return label

        return "general_sector"

    def _generate_summary(self, narrative_label: str) -> str:
        """生成叙事摘要"""
        return NARRATIVE_TEXTS.get(narrative_label, "行业属性，关注基本面变化和行业趋势。")

    def _generate_watch_points(self, narrative_label: str) -> List[str]:
        """生成叙事观察要点"""
        points = []

        if narrative_label == "technology_growth":
            points.append("关注技术迭代和资本开支")
        elif narrative_label == "healthcare_defensive_recovery":
            points.append("关注政策边际变化和估值修复")
        elif narrative_label == "financial_stability":
            points.append("关注宏观经济和利率环境")
        elif narrative_label == "new_energy_cycle":
            points.append("关注产能扩张和需求变化")
        elif narrative_label == "consumption_recovery":
            points.append("关注消费信心和渠道库存")
        else:
            points.append("关注基本面变化和行业趋势")

        return points
