"""
Sector Research Index 测试

测试多日研究索引模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.reports.sector_research_index import (
    SectorResearchIndex,
    generate_research_index_markdown,
    save_research_index,
)


class TestSectorResearchIndex:
    """测试 SectorResearchIndex"""

    def _create_mock_daily_data(self, tmpdir: str):
        """创建模拟每日数据"""
        # 创建 3 天的 sector_research.json
        dates = ["2026-06-24", "2026-06-25", "2026-06-26"]

        for i, date in enumerate(dates):
            report_dir = os.path.join(tmpdir, "sector_research", date)
            os.makedirs(report_dir)

            data = {
                "as_of_date": date,
                "sector_type": "industry",
                "daily_summary": {
                    "as_of_date": date,
                    "market_regime": "choppy_market" if i < 2 else "risk_off",
                    "total_count": 10,
                    "focus_count": 5,
                    "top_watch_names": ["半导体", "电子化学品", "医疗服务"],
                },
                "research_results": [
                    {
                        "sector_name": "半导体",
                        "consensus_label": "rotation_candidate" if i == 0 else "trend_confirmed",
                        "ranking_score": 0.65 + i * 0.05,
                        "opportunity_score": 0.50 + i * 0.03,
                        "confidence_score": 0.70,
                        "veto": {"veto_triggered": False},
                        "conflict_level": "none",
                        "market_regime": {"regime_composite_label": "choppy_market"},
                    },
                    {
                        "sector_name": "电子化学品",
                        "consensus_label": "trend_confirmed",
                        "ranking_score": 0.60,
                        "opportunity_score": 0.45,
                        "confidence_score": 0.80,
                        "veto": {"veto_triggered": i == 2},
                        "conflict_level": "none" if i < 2 else "medium",
                        "market_regime": {"regime_composite_label": "choppy_market"},
                    },
                    {
                        "sector_name": "医疗服务",
                        "consensus_label": "weak_or_avoid",
                        "ranking_score": 0.30,
                        "opportunity_score": 0.25,
                        "confidence_score": 0.60,
                        "veto": {"veto_triggered": False},
                        "conflict_level": "none",
                        "market_regime": {"regime_composite_label": "choppy_market"},
                    },
                ],
            }

            with open(os.path.join(report_dir, "sector_research.json"), "w") as f:
                json.dump(data, f)

        return dates

    def test_build_index_basic(self):
        """测试基本索引构建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_daily_data(tmpdir)

            indexer = SectorResearchIndex(report_root=tmpdir)
            result = indexer.build_index("2026-06-24", "2026-06-26")

            assert result["total_days"] == 3
            assert len(result["sector_frequency"]) > 0
            assert len(result["label_changes"]) > 0
            assert len(result["score_trends"]) > 0

    def test_sector_frequency(self):
        """测试板块出现频率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_daily_data(tmpdir)

            indexer = SectorResearchIndex(report_root=tmpdir)
            result = indexer.build_index("2026-06-24", "2026-06-26")

            freq = result["sector_frequency"]
            assert "半导体" in freq
            assert freq["半导体"]["count"] >= 2

    def test_label_changes(self):
        """测试标签变化检测"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_daily_data(tmpdir)

            indexer = SectorResearchIndex(report_root=tmpdir)
            result = indexer.build_index("2026-06-24", "2026-06-26")

            changes = result["label_changes"]
            # 半导体从 rotation_candidate 变为 trend_confirmed
            assert any(c["sector_name"] == "半导体" for c in changes)

    def test_risk_signals(self):
        """测试风险信号检测"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_daily_data(tmpdir)

            indexer = SectorResearchIndex(report_root=tmpdir)
            result = indexer.build_index("2026-06-24", "2026-06-26")

            signals = result["risk_signals"]
            # 电子化学品在 6-26 触发 veto 和 conflict
            assert any(s["sector_name"] == "电子化学品" for s in signals)

    def test_review_template(self):
        """测试复盘模板"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_daily_data(tmpdir)

            indexer = SectorResearchIndex(report_root=tmpdir)
            result = indexer.build_index("2026-06-24", "2026-06-26")

            template = result["review_template"]
            assert "sections" in template
            assert len(template["sections"]) > 0

    def test_markdown_generation(self):
        """测试 Markdown 生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_daily_data(tmpdir)

            indexer = SectorResearchIndex(report_root=tmpdir)
            result = indexer.build_index("2026-06-24", "2026-06-26")

            md = generate_research_index_markdown(result)
            assert "多日研究索引" in md
            assert "板块出现频率" in md
            assert "标签变化" in md
            assert "风险信号" in md

    def test_save_index(self):
        """测试保存索引"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_daily_data(tmpdir)

            indexer = SectorResearchIndex(report_root=tmpdir)
            result = indexer.build_index("2026-06-24", "2026-06-26")

            output_dir = os.path.join(tmpdir, "index")
            save_research_index(output_dir, result)

            assert os.path.exists(os.path.join(output_dir, "research_index.json"))
            assert os.path.exists(os.path.join(output_dir, "research_index.md"))

    def test_no_trade_advice_words(self):
        """测试不包含交易建议词"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_daily_data(tmpdir)

            indexer = SectorResearchIndex(report_root=tmpdir)
            result = indexer.build_index("2026-06-24", "2026-06-26")

            md = generate_research_index_markdown(result)
            trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
            for word in trade_words:
                assert word not in md.lower(), f"索引包含交易建议词: {word}"

    def test_empty_date_range(self):
        """测试空日期范围"""
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = SectorResearchIndex(report_root=tmpdir)
            result = indexer.build_index("2026-06-24", "2026-06-26")

            assert result["total_days"] == 0
            assert result["sector_frequency"] == {}
