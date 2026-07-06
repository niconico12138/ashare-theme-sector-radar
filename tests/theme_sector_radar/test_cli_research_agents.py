"""
CLI 板块综合研判测试

测试 --research-agents 命令。
"""

import json
import os
import sys
import tempfile

import pytest

from theme_sector_radar.cli import main


class TestCLIResearchAgents:
    """测试 CLI 板块综合研判"""

    def test_research_agents_help(self):
        """测试 --research-agents 帮助"""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["cli", "--research-agents", "--help"]
            main()
        assert exc_info.value.code == 0

    def test_research_agents_generates_report(self):
        """测试 CLI 能生成 sector_research.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟日报
            report_root = os.path.join(tmpdir, "reports")
            report_dir = os.path.join(report_root, "2026-06-29")
            os.makedirs(report_dir)
            report_data = {
                "report_type": "theme_sector_radar",
                "as_of_date": "2026-06-29",
                "industry_top": [
                    {
                        "sector_id": "test_1",
                        "name": "测试板块1",
                        "type": "industry",
                        "score": 70.0,
                        "positive_score": 75.0,
                        "risk_penalty": 5.0,
                        "data_quality_score": 60.0,
                    }
                ],
                "concept_top": [],
                "provider_status": {},
                "data_completeness": {},
                "cache_fallback": {},
                "fund_flow_coverage": {},
                "constituent_coverage": {},
                "rotation_summary": {},
                "comparison": {},
            }
            with open(os.path.join(report_dir, "theme_sector_radar.json"), "w") as f:
                json.dump(report_data, f)

            # 运行 research agents
            output_dir = os.path.join(tmpdir, "output")
            sys.argv = [
                "cli",
                "--research-agents",
                "--as-of", "2026-06-29",
                "--sector-type", "industry",
                "--report-root", report_root,
                "--score-output", output_dir,
                "--history-root", os.path.join(tmpdir, "data_cache", "sector_history"),
                "--history-start-date", "2026-06-25",
                "--history-end-date", "2026-06-29",
                "--top-n", "10",
                "--score-mode", "dual",
                "--benchmark", "none",
                "--trend-weight-profile", "baseline",
            ]
            main()

            # 验证输出文件
            research_dir = os.path.join(output_dir, "..", "sector_research", "2026-06-29")
            assert os.path.exists(os.path.join(research_dir, "sector_research.json"))

            # 验证 JSON 内容
            with open(os.path.join(research_dir, "sector_research.json"), "r", encoding="utf-8") as f:
                research_data = json.load(f)
            assert research_data["report_type"] == "sector_research"
            assert "research_results" in research_data
