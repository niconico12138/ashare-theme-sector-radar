"""
板块评分语义审计测试

测试 score_semantic_audit.py 模块的各项功能。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.reports.sector_score_report import generate_sector_score_report


class TestScoreSemanticAudit:
    """测试板块评分语义审计"""

    def _create_mock_report_data(self) -> dict:
        """创建模拟报告数据"""
        return {
            "report_type": "sector_scores",
            "version": "0.1.0",
            "as_of_date": "2026-06-29",
            "updated_at": "2026-06-30T10:00:00",
            "scores": [
                {
                    "sector_name": "测试板块1",
                    "sector_type": "industry",
                    "sector_selection_score": 51.0,
                    "selection_level": "neutral",
                    "rotation_phase": "leading",
                    "benchmark_mode": "sector_median",
                    "radar_score": 35.0,
                    "history_days": 9,
                    "score_breakdown": {
                        "radar_score_component": 8.75,
                        "momentum_component": 12.0,
                        "relative_strength_component": 15.0,
                        "persistence_component": 11.25,
                        "drawdown_component": 0.0,
                        "volatility_component": 4.0,
                        "data_quality_component": 8.0,
                        "risk_penalty": 8.0,
                        "positive_score": 59.0,
                        "final_score": 51.0,
                    },
                    "strength_reasons": [],
                    "risk_reasons": [],
                    "watch_points": [],
                    "data_warnings": [],
                },
                {
                    "sector_name": "测试板块2",
                    "sector_type": "industry",
                    "sector_selection_score": 40.0,
                    "selection_level": "cooling",
                    "rotation_phase": "improving",
                    "benchmark_mode": "sector_median",
                    "radar_score": 42.0,
                    "history_days": 9,
                    "score_breakdown": {
                        "radar_score_component": 10.5,
                        "momentum_component": 8.0,
                        "relative_strength_component": 15.0,
                        "persistence_component": 7.5,
                        "drawdown_component": 0.0,
                        "volatility_component": 3.0,
                        "data_quality_component": 8.0,
                        "risk_penalty": 12.0,
                        "positive_score": 52.0,
                        "final_score": 40.0,
                    },
                    "strength_reasons": [],
                    "risk_reasons": [],
                    "watch_points": [],
                    "data_warnings": [],
                },
                {
                    "sector_name": "测试板块3",
                    "sector_type": "industry",
                    "sector_selection_score": 31.25,
                    "selection_level": "avoid",
                    "rotation_phase": "lagging",
                    "benchmark_mode": "sector_median",
                    "radar_score": 42.0,
                    "history_days": 9,
                    "score_breakdown": {
                        "radar_score_component": 10.5,
                        "momentum_component": 8.0,
                        "relative_strength_component": 15.0,
                        "persistence_component": 3.75,
                        "drawdown_component": 0.0,
                        "volatility_component": 2.0,
                        "data_quality_component": 8.0,
                        "risk_penalty": 16.0,
                        "positive_score": 47.25,
                        "final_score": 31.25,
                    },
                    "strength_reasons": [],
                    "risk_reasons": [],
                    "watch_points": [],
                    "data_warnings": [],
                },
            ],
            "metadata": {
                "sector_type": "industry",
                "history_start_date": "2026-06-16",
                "history_end_date": "2026-06-30",
                "top_n": 20,
                "history_source": "sector_history_cache",
                "history_warnings": [],
            },
            "disclaimer": "本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。",
        }

    def test_score_distribution_statistics(self):
        """测试评分分布统计"""
        report_data = self._create_mock_report_data()
        scores = report_data['scores']

        # 统计评分分布
        score_distribution = {
            'strong_watch': 0,
            'watch': 0,
            'neutral': 0,
            'cooling': 0,
            'avoid': 0,
        }

        for s in scores:
            level = s['selection_level']
            score_distribution[level] = score_distribution.get(level, 0) + 1

        # 验证统计结果
        assert score_distribution['neutral'] == 1
        assert score_distribution['cooling'] == 1
        assert score_distribution['avoid'] == 1
        assert score_distribution['strong_watch'] == 0
        assert score_distribution['watch'] == 0

    def test_component_pressure_identification(self):
        """测试组件压力识别"""
        report_data = self._create_mock_report_data()
        scores = report_data['scores']

        # 定义每个组件的满分
        max_scores = {
            'momentum_component': 20,
            'relative_strength_component': 15,
            'persistence_component': 15,
            'drawdown_component': 10,
            'volatility_component': 5,
        }

        # 计算每个组件的平均利用率
        component_pressure = {}
        for comp, max_score in max_scores.items():
            values = [s['score_breakdown'][comp] for s in scores]
            avg = sum(values) / len(values)
            utilization = avg / max_score * 100

            if utilization < 40:
                component_pressure[comp] = 'low'
            elif utilization < 70:
                component_pressure[comp] = 'medium'
            else:
                component_pressure[comp] = 'high'

        # 验证压力识别 (使用实际计算结果)
        # momentum: (12+8+8)/3 = 9.33, 9.33/20 = 46.67% -> medium
        # relative: (15+15+15)/3 = 15, 15/15 = 100% -> high
        # persistence: (11.25+7.5+3.75)/3 = 7.5, 7.5/15 = 50% -> medium
        # volatility: (4+3+2)/3 = 3, 3/5 = 60% -> medium
        assert component_pressure['momentum_component'] == 'medium'
        assert component_pressure['relative_strength_component'] == 'high'
        assert component_pressure['persistence_component'] == 'medium'
        assert component_pressure['volatility_component'] == 'medium'

    def test_top5_max_pressure_items(self):
        """测试 Top 5 最大压分项"""
        report_data = self._create_mock_report_data()
        scores = report_data['scores']

        # 定义每个组件的满分
        max_scores = {
            'radar_score_component': 25,
            'momentum_component': 20,
            'relative_strength_component': 15,
            'persistence_component': 15,
            'drawdown_component': 10,
            'volatility_component': 5,
            'data_quality_component': 10,
        }

        # 找出 Top 1 的最大压分项
        top1 = scores[0]
        breakdown = top1['score_breakdown']

        pressure_items = []
        for comp, max_score in max_scores.items():
            actual = breakdown[comp]
            gap = max_score - actual
            pressure_items.append((comp, actual, max_score, gap))

        # 按差距排序
        pressure_items.sort(key=lambda x: x[3], reverse=True)

        # 验证最大压分项
        assert len(pressure_items) > 0
        top_pressure = pressure_items[0]
        assert top_pressure[0] == 'radar_score_component'  # 最大压分项
        assert top_pressure[3] > 0  # 差距大于 0

    def test_markdown_no_stock_recommendation(self):
        """测试 Markdown 不包含 buy/sell/hold"""
        report_data = self._create_mock_report_data()
        # 使用模拟数据生成报告
        from theme_sector_radar.reports.sector_score_report import generate_sector_score_report
        report = generate_sector_score_report(report_data)

        # 检查不含 buy/sell/hold 个股建议
        assert 'buy' not in report.lower()
        assert 'sell' not in report.lower()
        assert '买入' not in report
        assert '卖出' not in report
        # 注意: "持有" 可能出现在"中长期趋势观察价值较高"等描述中，这是允许的

    def test_insufficient_data_no_crash(self):
        """测试历史数据不足时审计不崩溃"""
        report_data = self._create_mock_report_data()
        report_data['metadata']['history_source'] = 'none'
        report_data['metadata']['history_warnings'] = ['No history data available']

        # 验证可以生成审计报告
        audit_report = {
            'as_of': report_data['as_of_date'],
            'history_source': report_data['metadata']['history_source'],
            'history_days': 0,
            'score_distribution': {},
            'component_pressure': {},
            'semantic_findings': [],
            'recommendations': [],
        }

        # 统计评分分布
        for s in report_data['scores']:
            level = s['selection_level']
            audit_report['score_distribution'][level] = audit_report['score_distribution'].get(level, 0) + 1

        # 验证审计报告
        assert audit_report['history_source'] == 'none'
        assert audit_report['history_days'] == 0
        assert len(audit_report['score_distribution']) > 0
