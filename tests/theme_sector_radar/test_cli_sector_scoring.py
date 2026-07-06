"""
CLI 板块综合评分测试

测试 CLI 的 --score-sectors 命令。
"""

import json
import os
import sys
import tempfile

import pytest

from theme_sector_radar.cli import main


class TestCLISectorScoring:
    """测试 CLI 板块综合评分"""

    def test_score_sectors_help(self):
        """测试 --score-sectors 帮助"""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["cli", "--score-sectors", "--help"]
            main()
        assert exc_info.value.code == 0

    def test_score_sectors_missing_report(self):
        """测试缺少日报报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SystemExit) as exc_info:
                sys.argv = [
                    "cli",
                    "--score-sectors",
                    "--as-of", "2026-01-01",
                    "--report-root", tmpdir,
                    "--score-output", os.path.join(tmpdir, "output"),
                ]
                main()
            assert exc_info.value.code == 1

    def test_score_sectors_with_report(self):
        """测试有日报报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟日报报告
            report_dir = os.path.join(tmpdir, "2026-06-29")
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

            # 运行评分
            output_dir = os.path.join(tmpdir, "output")
            sys.argv = [
                "cli",
                "--score-sectors",
                "--as-of", "2026-06-29",
                "--report-root", tmpdir,
                "--score-output", output_dir,
                "--sector-type", "industry",
                "--top-n", "10",
            ]
            main()

            # 验证输出文件
            assert os.path.exists(os.path.join(output_dir, "2026-06-29", "sector_scores.json"))
            assert os.path.exists(os.path.join(output_dir, "2026-06-29", "sector_scores.md"))

            # 验证 JSON 内容
            with open(os.path.join(output_dir, "2026-06-29", "sector_scores.json"), "r", encoding="utf-8") as f:
                score_report = json.load(f)
            assert score_report["report_type"] == "sector_scores"
            assert len(score_report["scores"]) == 1
            assert score_report["scores"][0]["sector_name"] == "测试板块1"

    def test_score_sectors_markdown_content(self):
        """测试 Markdown 报告内容"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟日报报告
            report_dir = os.path.join(tmpdir, "2026-06-29")
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

            # 运行评分
            output_dir = os.path.join(tmpdir, "output")
            sys.argv = [
                "cli",
                "--score-sectors",
                "--as-of", "2026-06-29",
                "--report-root", tmpdir,
                "--score-output", output_dir,
                "--sector-type", "industry",
                "--top-n", "10",
            ]
            main()

            # 验证 Markdown 内容
            md_path = os.path.join(output_dir, "2026-06-29", "sector_scores.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "板块综合评分" in content
            assert "评分权重" in content
            assert "等级规则" in content
            assert "免责声明" in content
            assert "buy" not in content.lower()
            assert "sell" not in content.lower()
            assert "hold" not in content.lower()

    def test_score_sectors_with_raw_snapshot_fallback(self):
        """测试 raw_snapshot fallback"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用唯一的目录名避免与其他测试冲突
            test_id = "raw_snapshot_fallback_test"

            # 创建模拟日报报告
            report_dir = os.path.join(tmpdir, test_id, "2026-06-29")
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

            # 创建模拟 raw_snapshot (no sector_history)
            cache_dir = os.path.join(tmpdir, test_id, "data_cache", "2026-06-28")
            os.makedirs(cache_dir)
            raw_snapshot = {
                "metadata": {
                    "as_of_date": "2026-06-28",
                    "provider": "akshare",
                },
                "data": {
                    "industry_sectors": [
                        {
                            "name": "测试板块1",
                            "type": "industry",
                            "price_change_pct": 2.0,
                            "turnover": 0.0,
                            "main_net_inflow": 0.0,
                            "data_quality_score": 60.0,
                            "price_change_available": True,
                            "data_sources": ["akshare/ths_industry"],
                        }
                    ],
                    "concept_sectors": [],
                },
            }
            with open(os.path.join(cache_dir, "raw_snapshot.json"), "w") as f:
                json.dump(raw_snapshot, f)

            # 运行评分
            output_dir = os.path.join(tmpdir, test_id, "output")
            sys.argv = [
                "cli",
                "--score-sectors",
                "--as-of", "2026-06-29",
                "--report-root", os.path.join(tmpdir, test_id),
                "--score-output", output_dir,
                "--history-root", os.path.join(tmpdir, test_id, "data_cache", "sector_history"),
                "--cache-root", os.path.join(tmpdir, test_id, "data_cache"),
                "--sector-type", "industry",
                "--history-start-date", "2026-06-28",
                "--history-end-date", "2026-06-29",
                "--top-n", "10",
            ]
            main()

            # 验证 JSON 内容
            with open(os.path.join(output_dir, "2026-06-29", "sector_scores.json"), "r", encoding="utf-8") as f:
                score_report = json.load(f)

            # 验证 history_source
            assert score_report["metadata"]["history_source"] == "raw_snapshot_fallback"

            # 验证 score_data 包含 history_source 和 history_days
            score = score_report["scores"][0]
            assert score["history_source"] == "raw_snapshot_fallback"
            assert score["history_days"] >= 1

    def test_score_sectors_markdown_raw_snapshot_explanation(self):
        """测试 Markdown 报告包含 raw_snapshot_fallback 说明"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用唯一的目录名避免与其他测试冲突
            test_id = "markdown_raw_snapshot_test"

            # 创建模拟日报报告
            report_dir = os.path.join(tmpdir, test_id, "2026-06-29")
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

            # 创建模拟 raw_snapshot (no sector_history)
            cache_dir = os.path.join(tmpdir, test_id, "data_cache", "2026-06-28")
            os.makedirs(cache_dir)
            raw_snapshot = {
                "metadata": {
                    "as_of_date": "2026-06-28",
                    "provider": "akshare",
                },
                "data": {
                    "industry_sectors": [
                        {
                            "name": "测试板块1",
                            "type": "industry",
                            "price_change_pct": 2.0,
                            "turnover": 0.0,
                            "main_net_inflow": 0.0,
                            "data_quality_score": 60.0,
                            "price_change_available": True,
                            "data_sources": ["akshare/ths_industry"],
                        }
                    ],
                    "concept_sectors": [],
                },
            }
            with open(os.path.join(cache_dir, "raw_snapshot.json"), "w") as f:
                json.dump(raw_snapshot, f)

            # 运行评分
            output_dir = os.path.join(tmpdir, test_id, "output")
            sys.argv = [
                "cli",
                "--score-sectors",
                "--as-of", "2026-06-29",
                "--report-root", os.path.join(tmpdir, test_id),
                "--score-output", output_dir,
                "--history-root", os.path.join(tmpdir, test_id, "data_cache", "sector_history"),
                "--cache-root", os.path.join(tmpdir, test_id, "data_cache"),
                "--sector-type", "industry",
                "--history-start-date", "2026-06-28",
                "--history-end-date", "2026-06-29",
                "--top-n", "10",
            ]
            main()

            # 验证 Markdown 内容
            md_path = os.path.join(output_dir, "2026-06-29", "sector_scores.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "raw_snapshot_fallback" in content
            assert "日报快照历史" in content
            assert "不等同完整板块指数历史" in content

    def test_score_sectors_sector_history_priority(self):
        """测试 sector_history_cache 优先于 raw_snapshot_fallback"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟日报报告
            report_dir = os.path.join(tmpdir, "2026-06-29")
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

            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "data_cache", "sector_history", "industry")
            os.makedirs(history_dir)
            sector_history = {
                "sector_name": "测试板块1",
                "sector_type": "industry",
                "records": [
                    {"日期": "2026-06-28", "收盘价": 100.0, "开盘价": 98.0},
                    {"日期": "2026-06-29", "收盘价": 102.0, "开盘价": 100.0},
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(sector_history, f)

            # 创建模拟 raw_snapshot
            cache_dir = os.path.join(tmpdir, "data_cache", "2026-06-28")
            os.makedirs(cache_dir)
            raw_snapshot = {
                "metadata": {
                    "as_of_date": "2026-06-28",
                    "provider": "akshare",
                },
                "data": {
                    "industry_sectors": [
                        {
                            "name": "测试板块1",
                            "type": "industry",
                            "price_change_pct": 2.0,
                            "turnover": 0.0,
                            "main_net_inflow": 0.0,
                            "data_quality_score": 60.0,
                            "price_change_available": True,
                            "data_sources": ["akshare/ths_industry"],
                        }
                    ],
                    "concept_sectors": [],
                },
            }
            with open(os.path.join(cache_dir, "raw_snapshot.json"), "w") as f:
                json.dump(raw_snapshot, f)

            # 运行评分
            output_dir = os.path.join(tmpdir, "output")
            sys.argv = [
                "cli",
                "--score-sectors",
                "--as-of", "2026-06-29",
                "--report-root", tmpdir,
                "--score-output", output_dir,
                "--history-root", os.path.join(tmpdir, "data_cache", "sector_history"),
                "--cache-root", os.path.join(tmpdir, "data_cache"),
                "--sector-type", "industry",
                "--history-start-date", "2026-06-28",
                "--history-end-date", "2026-06-29",
                "--top-n", "10",
            ]
            main()

            # 验证 JSON 内容
            with open(os.path.join(output_dir, "2026-06-29", "sector_scores.json"), "r", encoding="utf-8") as f:
                score_report = json.load(f)

            # 验证 history_source 是 sector_history_cache
            assert score_report["metadata"]["history_source"] == "sector_history_cache"

            # 验证 history_days > 0
            score = score_report["scores"][0]
            assert score["history_days"] > 0

    def test_score_sectors_history_days_increased(self):
        """测试 history_days 增加后不会被错误标记为 raw_snapshot_fallback"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟日报报告
            report_dir = os.path.join(tmpdir, "2026-06-29")
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

            # 创建模拟 sector_history with multiple days
            history_dir = os.path.join(tmpdir, "data_cache", "sector_history", "industry")
            os.makedirs(history_dir)
            sector_history = {
                "sector_name": "测试板块1",
                "sector_type": "industry",
                "records": [
                    {"日期": "2026-06-25", "收盘价": 95.0, "开盘价": 94.0},
                    {"日期": "2026-06-26", "收盘价": 97.0, "开盘价": 95.0},
                    {"日期": "2026-06-27", "收盘价": 99.0, "开盘价": 97.0},
                    {"日期": "2026-06-28", "收盘价": 100.0, "开盘价": 99.0},
                    {"日期": "2026-06-29", "收盘价": 102.0, "开盘价": 100.0},
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(sector_history, f)

            # 运行评分
            output_dir = os.path.join(tmpdir, "output")
            sys.argv = [
                "cli",
                "--score-sectors",
                "--as-of", "2026-06-29",
                "--report-root", tmpdir,
                "--score-output", output_dir,
                "--history-root", os.path.join(tmpdir, "data_cache", "sector_history"),
                "--sector-type", "industry",
                "--history-start-date", "2026-06-25",
                "--history-end-date", "2026-06-29",
                "--top-n", "10",
            ]
            main()

            # 验证 JSON 内容
            with open(os.path.join(output_dir, "2026-06-29", "sector_scores.json"), "r", encoding="utf-8") as f:
                score_report = json.load(f)

            # 验证 history_days >= 5
            score = score_report["scores"][0]
            assert score["history_days"] >= 5

            # 验证 history_source 是 sector_history_cache
            assert score["history_source"] == "sector_history_cache"

    def test_score_sectors_insufficient_data_no_crash(self):
        """测试历史数据不足时输出 insufficient_data，不崩溃"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用唯一的目录名避免与其他测试冲突
            test_id = "insufficient_data_test"

            # 创建模拟日报报告
            report_dir = os.path.join(tmpdir, test_id, "2026-06-29")
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

            # 运行评分 without any history data
            # 使用不存在的日期范围确保没有 raw_snapshot 数据
            output_dir = os.path.join(tmpdir, test_id, "output")
            sys.argv = [
                "cli",
                "--score-sectors",
                "--as-of", "2026-06-29",
                "--report-root", os.path.join(tmpdir, test_id),
                "--score-output", output_dir,
                "--history-root", os.path.join(tmpdir, test_id, "data_cache", "sector_history"),
                "--cache-root", os.path.join(tmpdir, test_id, "data_cache"),
                "--sector-type", "industry",
                "--history-start-date", "2026-01-01",
                "--history-end-date", "2026-01-05",
                "--top-n", "10",
            ]
            main()

            # 验证 JSON 内容
            with open(os.path.join(output_dir, "2026-06-29", "sector_scores.json"), "r", encoding="utf-8") as f:
                score_report = json.load(f)

            # 验证 history_source 是 none
            assert score_report["metadata"]["history_source"] == "none"

            # 验证 history_days 是 0
            score = score_report["scores"][0]
            assert score["history_days"] == 0

            # 验证 selection_level 不是 strong_watch (因为 history_days=0)
            assert score["selection_level"] != "strong_watch"

    def test_score_sectors_metadata_records_run_parameters_and_paths(self):
        """评分报告 metadata 应记录完整运行参数和输入路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_dir = os.path.join(tmpdir, "2026-06-29")
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
            input_report_path = os.path.join(report_dir, "theme_sector_radar.json")
            with open(input_report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False)

            history_root = os.path.join(tmpdir, "data_cache", "sector_history")
            cache_root = os.path.join(tmpdir, "data_cache")
            output_dir = os.path.join(tmpdir, "output")

            sys.argv = [
                "cli",
                "--score-sectors",
                "--as-of", "2026-06-29",
                "--report-root", tmpdir,
                "--score-output", output_dir,
                "--history-root", history_root,
                "--cache-root", cache_root,
                "--sector-type", "industry",
                "--history-start-date", "2026-05-20",
                "--history-end-date", "2026-06-29",
                "--top-n", "7",
                "--trend-window", "20",
                "--trend-weight-profile", "trend_confirmation",
                "--benchmark", "none",
            ]
            main()

            with open(os.path.join(output_dir, "2026-06-29", "sector_scores.json"), "r", encoding="utf-8") as f:
                score_report = json.load(f)

            metadata = score_report["metadata"]
            assert metadata["input_report_path"] == os.path.abspath(input_report_path)
            assert metadata["report_root"] == tmpdir
            assert metadata["score_output"] == output_dir
            assert metadata["history_root"] == history_root
            assert metadata["cache_root"] == cache_root

            run_parameters = metadata["run_parameters"]
            assert run_parameters["as_of"] == "2026-06-29"
            assert run_parameters["sector_type"] == "industry"
            assert run_parameters["top_n"] == 7
            assert run_parameters["trend_window"] == 20
            assert run_parameters["trend_weight_profile"] == "trend_confirmation"
            assert run_parameters["benchmark"] == "none"
            assert run_parameters["history_start_date"] == "2026-05-20"
            assert run_parameters["history_end_date"] == "2026-06-29"
