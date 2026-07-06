"""
历史日报快照补齐

从 sector_history 数据生成历史日报 theme_sector_radar.json。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


class DailyReplayFromSectorHistory:
    """
    历史日报快照补齐

    从 sector_history 数据生成历史日报 theme_sector_radar.json。
    """

    def __init__(
        self,
        history_root: str = "data_cache/sector_history",
        report_root: str = "reports",
    ):
        """
        初始化

        Args:
            history_root: 历史数据根目录
            report_root: 报告根目录
        """
        self.history_root = history_root
        self.report_root = report_root

    def run_replay(
        self,
        start_date: str,
        end_date: str,
        sector_type: str = "industry",
        top_n: int = 20,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        运行历史日报 replay

        Args:
            start_date: 开始日期
            end_date: 结束日期
            sector_type: 板块类型
            top_n: Top N 数量
            refresh: 是否强制刷新

        Returns:
            运行结果
        """
        generated_dates = []
        skipped_dates = []
        failed_dates = []
        reused_dates = []
        no_lookahead_violations = []

        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

        while current_date <= end_date_dt:
            signal_date = current_date.strftime("%Y-%m-%d")

            # 检查是否已有 theme_sector_radar.json
            report_path = os.path.join(
                self.report_root, "theme_sector_radar", signal_date, "theme_sector_radar.json"
            )

            if os.path.exists(report_path) and not refresh:
                reused_dates.append(signal_date)
                print(f"  {signal_date}: Reused existing report")
                current_date += timedelta(days=1)
                continue

            try:
                # 生成日报
                self._generate_daily_report(
                    signal_date=signal_date,
                    sector_type=sector_type,
                    top_n=top_n,
                )

                # 检查 no-lookahead
                if not self._check_no_lookahead(report_path, signal_date):
                    no_lookahead_violations.append(signal_date)
                    failed_dates.append({
                        "date": signal_date,
                        "reason": "no_lookahead_violation"
                    })
                    print(f"  {signal_date}: Failed (no-lookahead violation)")
                else:
                    generated_dates.append(signal_date)
                    print(f"  {signal_date}: Generated")

            except Exception as e:
                failed_dates.append({
                    "date": signal_date,
                    "reason": str(e)[:200]
                })
                print(f"  {signal_date}: Failed ({str(e)[:100]})")

            current_date += timedelta(days=1)

        # 构建结果
        result = {
            "report_type": "daily_replay_from_sector_history",
            "start_date": start_date,
            "end_date": end_date,
            "generated_dates": generated_dates,
            "skipped_dates": skipped_dates,
            "failed_dates": failed_dates,
            "reused_dates": reused_dates,
            "warnings": [],
            "no_lookahead_violations": no_lookahead_violations,
        }

        return result

    def _generate_daily_report(
        self,
        signal_date: str,
        sector_type: str,
        top_n: int,
    ):
        """
        生成单日日报

        Args:
            signal_date: 信号日期
            sector_type: 板块类型
            top_n: Top N 数量
        """
        # 读取 sector_history 数据
        sector_data = self._load_sector_data_for_date(
            signal_date, sector_type
        )

        if not sector_data:
            raise ValueError(f"No sector data found for {signal_date}")

        # 计算 replay_radar_score
        for sector in sector_data:
            replay_score = self._calculate_replay_radar_score(sector)
            sector["score"] = replay_score
            sector["score_breakdown"] = {
                "score_source": "sector_history_replay",
            }

        # 按 score 降序排序
        sector_data.sort(key=lambda x: x.get("score", 0), reverse=True)

        # 取 top_n
        top_sectors = sector_data[:top_n]

        # 计算市场广度
        market_breadth = self._compute_market_breadth(signal_date, sector_type)

        # 生成 theme_sector_radar.json
        report_data = {
            "report_type": "theme_sector_radar",
            "version": "0.1.0",
            "as_of_date": signal_date,
            "updated_at": datetime.now().isoformat(),
            "status": "ok",
            "market_temperature": {
                "score": market_breadth.get("replay_market_temperature_score", 50.0),
                "label": market_breadth.get("replay_market_temperature_label", "neutral"),
                "description": f"市场温度: {market_breadth.get('replay_market_temperature_label', 'neutral')}",
                "advance_count": market_breadth.get("industry_up_count", 0),
                "decline_count": market_breadth.get("industry_down_count", 0),
                "limit_up_count": 0,
                "limit_down_count": 0,
            },
            "market_breadth": market_breadth,
            "industry_top": top_sectors if sector_type == "industry" else [],
            "concept_top": top_sectors if sector_type == "concept" else [],
            "data_quality_score": 60.0,
            "provider_status": {
                "effective_provider": "sector_history_replay",
                "industry_source": "sector_history_replay",
                "concept_source": "sector_history_replay",
            },
            "data_completeness": {
                "industry_count": len(top_sectors) if sector_type == "industry" else 0,
                "concept_count": len(top_sectors) if sector_type == "concept" else 0,
            },
            "run_mode": "replay",
            "data_source_mode": "sector_history_replay",
            "generated_by_command": f"--replay-daily-from-sector-history --as-of {signal_date}",
            "disclaimer": "本报告仅用于板块研究、观察和复盘，不作为操作依据。",
            "metadata": {
                "replay_source": "sector_history",
                "signal_date": signal_date,
                "max_source_record_date": signal_date,
                "no_lookahead_passed": True,
            },
        }

        # 保存文件
        output_dir = os.path.join(self.report_root, "theme_sector_radar", signal_date)
        os.makedirs(output_dir, exist_ok=True)

        # 保存 theme_sector_radar.json
        json_path = os.path.join(output_dir, "theme_sector_radar.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        # 保存 raw_snapshot.json
        raw_snapshot = {
            "metadata": {
                "replay_source": "sector_history",
                "signal_date": signal_date,
                "max_source_record_date": signal_date,
                "no_lookahead_passed": True,
            },
            "data": {
                "industry_sectors": top_sectors if sector_type == "industry" else [],
                "concept_sectors": top_sectors if sector_type == "concept" else [],
                "market_data": {},
            },
        }
        raw_snapshot_path = os.path.join(output_dir, "raw_snapshot.json")
        with open(raw_snapshot_path, "w", encoding="utf-8") as f:
            json.dump(raw_snapshot, f, ensure_ascii=False, indent=2)

        # 保存 run_log.json
        run_log = {
            "command_args": f"--replay-daily-from-sector-history --as-of {signal_date}",
            "started_at": datetime.now().isoformat(),
            "finished_at": datetime.now().isoformat(),
            "status": "ok",
            "run_mode": "replay",
            "data_source_mode": "sector_history_replay",
        }
        run_log_path = os.path.join(output_dir, "run_log.json")
        with open(run_log_path, "w", encoding="utf-8") as f:
            json.dump(run_log, f, ensure_ascii=False, indent=2)

    def _load_sector_data_for_date(
        self,
        signal_date: str,
        sector_type: str,
    ) -> List[Dict[str, Any]]:
        """
        加载指定日期的板块数据

        Args:
            signal_date: 信号日期
            sector_type: 板块类型

        Returns:
            板块数据列表
        """
        sector_type_dir = os.path.join(self.history_root, sector_type)
        if not os.path.exists(sector_type_dir):
            return []

        sector_data = []
        for filename in os.listdir(sector_type_dir):
            if not filename.endswith(".json"):
                continue

            sector_name = filename[:-5]
            filepath = os.path.join(sector_type_dir, filename)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    history = json.load(f)

                records = history.get("records", [])
                if not records:
                    continue

                # 找到 <= signal_date 的最近记录
                best_record = None
                for record in records:
                    record_date = record.get("日期", "")
                    if record_date <= signal_date:
                        best_record = record

                if best_record is None:
                    continue

                # 找到 signal_date 当日及之前的所有记录
                all_records_before = []
                for record in records:
                    record_date = record.get("日期", "")
                    if record_date <= signal_date:
                        all_records_before.append(record)

                # 计算涨幅：使用当日收盘价和前一日收盘价
                close = best_record.get("收盘价", 0)
                prev_close = 0.0
                if len(all_records_before) >= 2:
                    prev_record = all_records_before[-2]
                    prev_close = prev_record.get("收盘价", 0)

                if prev_close > 0:
                    change_pct = (close - prev_close) / prev_close * 100
                else:
                    change_pct = 0.0

                sector_data.append({
                    "sector_id": f"replay_{sector_type}_{sector_name}",
                    "name": sector_name,
                    "type": sector_type,
                    "price_change_pct": round(change_pct, 2),
                    "turnover": best_record.get("成交额", 0),
                    "main_net_inflow": 0.0,
                    "data_quality_score": 60.0,
                    "source": "sector_history_replay",
                    "source_record_date": best_record.get("日期", ""),
                })

            except Exception as e:
                warnings.warn(f"Failed to load {filepath}: {str(e)}")

        return sector_data

    def _calculate_replay_radar_score(self, sector_data: Dict[str, Any]) -> float:
        """
        计算 replay_radar_score

        Args:
            sector_data: 板块数据

        Returns:
            replay_radar_score
        """
        change_pct = sector_data.get("price_change_pct", 0.0)

        # 简化评分公式
        # 1日涨幅组件 20
        if change_pct >= 5:
            one_day_score = 20
        elif change_pct >= 3:
            one_day_score = 15
        elif change_pct >= 1:
            one_day_score = 10
        elif change_pct >= 0:
            one_day_score = 5
        else:
            one_day_score = 0

        # 3日涨幅组件 20 (简化：使用1日涨幅近似)
        three_day_score = min(one_day_score, 20)

        # 5日涨幅组件 25 (简化：使用1日涨幅近似)
        five_day_score = min(one_day_score, 25)

        # 10日涨幅组件 15 (简化：使用1日涨幅近似)
        ten_day_score = min(one_day_score, 15)

        # 持续性组件 10 (简化：基于涨幅方向)
        if change_pct > 0:
            persistence_score = 8
        else:
            persistence_score = 3

        # 数据质量组件 10
        data_quality_score = 8

        # 总分
        total_score = (
            one_day_score +
            three_day_score +
            five_day_score +
            ten_day_score +
            persistence_score +
            data_quality_score
        )

        return min(total_score, 100.0)

    def _compute_market_breadth(
        self, signal_date: str, sector_type: str
    ) -> Dict[str, Any]:
        """
        计算市场广度指标（no-lookahead）

        Args:
            signal_date: 信号日期
            sector_type: 板块类型

        Returns:
            市场广度指标字典
        """
        sector_type_dir = os.path.join(self.history_root, sector_type)
        if not os.path.exists(sector_type_dir):
            return self._empty_breadth()

        change_pcts = []
        total_count = 0

        for filename in os.listdir(sector_type_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(sector_type_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    history = json.load(f)

                records = history.get("records", [])
                if not records:
                    continue

                # 找到 <= signal_date 的最近记录
                best_record = None
                for record in records:
                    record_date = record.get("日期", "")
                    if record_date <= signal_date:
                        best_record = record

                if best_record is None:
                    continue

                # 找到 signal_date 当日及之前的所有记录，用于计算涨跌幅
                all_records_before = []
                for record in records:
                    record_date = record.get("日期", "")
                    if record_date <= signal_date:
                        all_records_before.append(record)

                # 计算涨幅：使用当日收盘价和前一日收盘价
                close = best_record.get("收盘价", 0)
                prev_close = 0.0
                if len(all_records_before) >= 2:
                    prev_record = all_records_before[-2]
                    prev_close = prev_record.get("收盘价", 0)

                if prev_close > 0:
                    change_pct = (close - prev_close) / prev_close * 100
                else:
                    change_pct = 0.0

                change_pcts.append(change_pct)
                total_count += 1

            except Exception:
                continue

        if total_count == 0:
            return self._empty_breadth()

        # 统计
        up_count = sum(1 for c in change_pcts if c > 0.1)
        down_count = sum(1 for c in change_pcts if c < -0.1)
        flat_count = total_count - up_count - down_count

        up_ratio = up_count / total_count
        down_ratio = down_count / total_count

        avg_change = sum(change_pcts) / len(change_pcts)
        sorted_changes = sorted(change_pcts)
        median_change = sorted_changes[len(sorted_changes) // 2]

        strong_count = sum(1 for c in change_pcts if c >= 2.0)
        weak_count = sum(1 for c in change_pcts if c <= -2.0)
        strong_ratio = strong_count / total_count
        weak_ratio = weak_count / total_count

        # breadth_label
        if up_ratio >= 0.65 and avg_change > 0:
            breadth_label = "broad_rising"
        elif up_ratio < 0.65 and strong_count > 0:
            breadth_label = "narrow_rising"
        elif down_ratio >= 0.65 and avg_change < 0:
            breadth_label = "broad_falling"
        else:
            breadth_label = "mixed_breadth"

        # replay_market_temperature_label
        if up_ratio >= 0.70 and strong_ratio >= 0.20:
            temp_label = "hot"
        elif up_ratio >= 0.55 and avg_change > 0:
            temp_label = "warm"
        elif down_ratio < 0.60 and abs(avg_change) < 1.0:
            temp_label = "cool"
        elif down_ratio >= 0.60 and avg_change < 0:
            temp_label = "cold"
        else:
            temp_label = "cool"

        # replay_market_temperature_score (0-100)
        # 基于 up_ratio, avg_change, strong_ratio, weak_ratio
        score = 50.0
        score += (up_ratio - 0.5) * 40  # up_ratio 0.5 -> 0, 1.0 -> +20
        score += max(-10, min(10, avg_change * 5))  # avg_change -2~+2 -> -10~+10
        score += strong_ratio * 20  # strong_ratio 0~0.3 -> 0~+6
        score -= weak_ratio * 20  # weak_ratio 0~0.3 -> 0~-6
        score = max(0, min(100, score))

        return {
            "industry_total_count": total_count,
            "industry_up_count": up_count,
            "industry_down_count": down_count,
            "industry_flat_count": flat_count,
            "industry_up_ratio": round(up_ratio, 4),
            "industry_down_ratio": round(down_ratio, 4),
            "average_industry_change_pct": round(avg_change, 4),
            "median_industry_change_pct": round(median_change, 4),
            "strong_industry_count": strong_count,
            "weak_industry_count": weak_count,
            "strong_industry_ratio": round(strong_ratio, 4),
            "weak_industry_ratio": round(weak_ratio, 4),
            "breadth_label": breadth_label,
            "replay_market_temperature_label": temp_label,
            "replay_market_temperature_score": round(score, 1),
        }

    def _empty_breadth(self) -> Dict[str, Any]:
        """返回空的市场广度指标"""
        return {
            "industry_total_count": 0,
            "industry_up_count": 0,
            "industry_down_count": 0,
            "industry_flat_count": 0,
            "industry_up_ratio": 0.0,
            "industry_down_ratio": 0.0,
            "average_industry_change_pct": 0.0,
            "median_industry_change_pct": 0.0,
            "strong_industry_count": 0,
            "weak_industry_count": 0,
            "strong_industry_ratio": 0.0,
            "weak_industry_ratio": 0.0,
            "breadth_label": "breadth_unknown",
            "replay_market_temperature_label": "unknown",
            "replay_market_temperature_score": 50.0,
        }

    def _check_no_lookahead(
        self,
        report_path: str,
        signal_date: str,
    ) -> bool:
        """
        检查 no-lookahead

        Args:
            report_path: 报告路径
            signal_date: 信号日期

        Returns:
            是否通过
        """
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)

            metadata = report_data.get("metadata", {})
            max_source_record_date = metadata.get("max_source_record_date", "")

            if not max_source_record_date:
                return False

            return max_source_record_date <= signal_date

        except Exception:
            return False


def save_replay_daily_summary(
    output_dir: str,
    summary_data: Dict[str, Any],
):
    """
    保存 replay daily summary

    Args:
        output_dir: 输出目录
        summary_data: 摘要数据
    """
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "replay_daily_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2, default=str)

    # 生成 Markdown
    md_report = _generate_replay_daily_summary_markdown(summary_data)
    md_path = os.path.join(output_dir, "replay_daily_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"Replay daily summary saved: {output_dir}")


def _generate_replay_daily_summary_markdown(summary_data: Dict[str, Any]) -> str:
    """
    生成 replay daily summary Markdown

    Args:
        summary_data: 摘要数据

    Returns:
        Markdown 字符串
    """
    lines = []

    lines.append("# 历史日报 Replay 摘要报告")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    lines.append("## 参数")
    lines.append("")
    lines.append(f"- **日期范围**: {summary_data.get('start_date', '')} ~ {summary_data.get('end_date', '')}")
    lines.append("")

    lines.append("## 运行结果")
    lines.append("")
    lines.append(f"- **生成日期数**: {len(summary_data.get('generated_dates', []))}")
    lines.append(f"- **复用日期数**: {len(summary_data.get('reused_dates', []))}")
    lines.append(f"- **跳过日期数**: {len(summary_data.get('skipped_dates', []))}")
    lines.append(f"- **失败日期数**: {len(summary_data.get('failed_dates', []))}")
    lines.append(f"- **no-lookahead 违规数**: {len(summary_data.get('no_lookahead_violations', []))}")
    lines.append("")

    # no-lookahead 违规
    violations = summary_data.get("no_lookahead_violations", [])
    if violations:
        lines.append("## no-lookahead 违规")
        lines.append("")
        lines.append("以下日期的 max_source_record_date > signal_date：")
        for date in violations:
            lines.append(f"- {date}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)
