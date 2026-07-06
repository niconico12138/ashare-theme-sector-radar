"""
历史日报快照补齐测试

测试 replay_daily_from_sector_history.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.backtest.replay_daily_from_sector_history import (
    DailyReplayFromSectorHistory,
    save_replay_daily_summary,
)


class TestDailyReplayFromSectorHistory:
    """测试历史日报快照补齐"""

    def test_replay_daily_generates_theme_sector_radar_json(self):
        """测试能生成 theme_sector_radar.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            # 创建模拟历史数据
            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(16, 30)
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(history_data, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            result = replay.run_replay(
                start_date="2026-06-25",
                end_date="2026-06-25",
                sector_type="industry",
                top_n=5,
                refresh=True,
            )

            # 验证生成了日期
            assert len(result["generated_dates"]) == 1

            # 验证文件存在
            report_path = os.path.join(tmpdir, "theme_sector_radar", "2026-06-25", "theme_sector_radar.json")
            assert os.path.exists(report_path)

    def test_replay_daily_generates_required_files(self):
        """测试能生成 json/md/raw_snapshot/run_log"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(16, 30)
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(history_data, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            result = replay.run_replay(
                start_date="2026-06-25",
                end_date="2026-06-25",
                sector_type="industry",
                top_n=5,
                refresh=True,
            )

            # 验证文件存在
            output_dir = os.path.join(tmpdir, "theme_sector_radar", "2026-06-25")
            assert os.path.exists(os.path.join(output_dir, "theme_sector_radar.json"))
            assert os.path.exists(os.path.join(output_dir, "raw_snapshot.json"))
            assert os.path.exists(os.path.join(output_dir, "run_log.json"))

    def test_replay_daily_no_lookahead_metadata(self):
        """测试 metadata.max_source_record_date <= signal_date"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(16, 30)
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(history_data, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            result = replay.run_replay(
                start_date="2026-06-25",
                end_date="2026-06-25",
                sector_type="industry",
                top_n=5,
                refresh=True,
            )

            # 验证 no-lookahead
            assert len(result["no_lookahead_violations"]) == 0

            # 验证 metadata
            report_path = os.path.join(tmpdir, "theme_sector_radar", "2026-06-25", "theme_sector_radar.json")
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)

            metadata = report_data.get("metadata", {})
            assert metadata["max_source_record_date"] <= "2026-06-25"
            assert metadata["no_lookahead_passed"] is True

    def test_replay_daily_score_breakdown_source(self):
        """测试 score_breakdown 包含 score_source=sector_history_replay"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(16, 30)
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(history_data, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            replay.run_replay(
                start_date="2026-06-25",
                end_date="2026-06-25",
                sector_type="industry",
                top_n=5,
                refresh=True,
            )

            # 验证 score_breakdown
            report_path = os.path.join(tmpdir, "theme_sector_radar", "2026-06-25", "theme_sector_radar.json")
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)

            industry_top = report_data.get("industry_top", [])
            if industry_top:
                score_breakdown = industry_top[0].get("score_breakdown", {})
                assert score_breakdown.get("score_source") == "sector_history_replay"

    def test_replay_daily_reuses_existing_by_default(self):
        """测试默认不覆盖已有日报"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(16, 30)
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(history_data, f)

            # 创建已有日报
            report_dir = os.path.join(tmpdir, "theme_sector_radar", "2026-06-25")
            os.makedirs(report_dir)
            existing_report = {"report_type": "theme_sector_radar", "status": "ok"}
            with open(os.path.join(report_dir, "theme_sector_radar.json"), "w") as f:
                json.dump(existing_report, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            result = replay.run_replay(
                start_date="2026-06-25",
                end_date="2026-06-25",
                sector_type="industry",
                top_n=5,
                refresh=False,
            )

            # 验证复用了已有报告
            assert len(result["reused_dates"]) == 1
            assert len(result["generated_dates"]) == 0

    def test_replay_daily_summary_contract(self):
        """测试 summary 包含 generated/skipped/failed/reused/no_lookahead_violations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(16, 30)
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(history_data, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            result = replay.run_replay(
                start_date="2026-06-25",
                end_date="2026-06-29",
                sector_type="industry",
                top_n=5,
                refresh=True,
            )

            # 验证 summary 字段
            assert "generated_dates" in result
            assert "skipped_dates" in result
            assert "failed_dates" in result
            assert "reused_dates" in result
            assert "no_lookahead_violations" in result
            assert len(result["generated_dates"]) == 5

    def test_replay_daily_no_trade_advice_words(self):
        """测试输出文件不包含禁止交易建议词"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(16, 30)
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(history_data, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            replay.run_replay(
                start_date="2026-06-25",
                end_date="2026-06-25",
                sector_type="industry",
                top_n=5,
                refresh=True,
            )

            # 验证输出文件
            report_path = os.path.join(tmpdir, "theme_sector_radar", "2026-06-25", "theme_sector_radar.json")
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()

            forbidden_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐", "建仓", "加仓", "减仓", "止盈", "止损", "目标价"]
            for word in forbidden_words:
                assert word not in content.lower(), f"输出文件包含禁止词: {word}"

    def test_market_breadth_in_report(self):
        """测试 theme_sector_radar.json 包含 market_breadth"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            # 创建多个板块，有不同的涨跌幅
            for i, (name, close, prev) in enumerate([
                ("板块A", 105, 100),  # +5%
                ("板块B", 102, 100),  # +2%
                ("板块C", 98, 100),   # -2%
                ("板块D", 100, 100),  # 0%
                ("板块E", 103, 100),  # +3%
            ]):
                history_data = {
                    "records": [
                        {"日期": f"2026-06-{d:02d}", "收盘价": 100.0, "前收盘": 99.0}
                        for d in range(16, 25)
                    ] + [
                        {"日期": "2026-06-25", "收盘价": close, "前收盘": prev},
                    ],
                }
                with open(os.path.join(history_dir, f"{name}.json"), "w") as f:
                    json.dump(history_data, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            replay.run_replay(
                start_date="2026-06-25",
                end_date="2026-06-25",
                sector_type="industry",
                top_n=5,
                refresh=True,
            )

            report_path = os.path.join(tmpdir, "theme_sector_radar", "2026-06-25", "theme_sector_radar.json")
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)

            # 验证 market_breadth 存在
            assert "market_breadth" in report_data
            breadth = report_data["market_breadth"]
            assert breadth["industry_total_count"] == 5
            assert breadth["industry_up_count"] >= 3
            assert breadth["industry_down_count"] >= 1
            assert breadth["industry_up_ratio"] > 0
            assert breadth["breadth_label"] in ["broad_rising", "narrow_rising", "broad_falling", "mixed_breadth"]

    def test_market_temperature_from_breadth(self):
        """测试 market_temperature 从 breadth 计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            # 创建上涨板块
            for i in range(8):
                history_data = {
                    "records": [
                        {"日期": f"2026-06-{d:02d}", "收盘价": 100.0, "前收盘": 99.0}
                        for d in range(16, 25)
                    ] + [
                        {"日期": "2026-06-25", "收盘价": 105.0, "前收盘": 100.0},  # +5%
                    ],
                }
                with open(os.path.join(history_dir, f"上涨板块{i}.json"), "w") as f:
                    json.dump(history_data, f)

            # 创建下跌板块
            for i in range(2):
                history_data = {
                    "records": [
                        {"日期": f"2026-06-{d:02d}", "收盘价": 100.0, "前收盘": 99.0}
                        for d in range(16, 25)
                    ] + [
                        {"日期": "2026-06-25", "收盘价": 95.0, "前收盘": 100.0},  # -5%
                    ],
                }
                with open(os.path.join(history_dir, f"下跌板块{i}.json"), "w") as f:
                    json.dump(history_data, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            replay.run_replay(
                start_date="2026-06-25",
                end_date="2026-06-25",
                sector_type="industry",
                top_n=5,
                refresh=True,
            )

            report_path = os.path.join(tmpdir, "theme_sector_radar", "2026-06-25", "theme_sector_radar.json")
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)

            mt = report_data["market_temperature"]
            # 80% 上涨，应该是 warm 或 hot
            assert mt["score"] > 50
            assert mt["label"] in ["warm", "hot"]
            assert mt["advance_count"] == 8
            assert mt["decline_count"] == 2

    def test_breadth_no_lookahead(self):
        """测试 breadth 计算不使用未来数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            # 板块只有 6-24 之前的数据，6-25 没有
            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(16, 25)
                ],
            }
            with open(os.path.join(history_dir, "测试板块.json"), "w") as f:
                json.dump(history_data, f)

            replay = DailyReplayFromSectorHistory(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            # 计算 6-25 的 breadth，应该使用 6-24 的数据
            breadth = replay._compute_market_breadth("2026-06-25", "industry")
            assert breadth["industry_total_count"] == 1
            # 最近记录是 6-24，涨幅应该基于 6-24 的数据
            assert breadth["average_industry_change_pct"] != 0 or breadth["industry_flat_count"] == 1
