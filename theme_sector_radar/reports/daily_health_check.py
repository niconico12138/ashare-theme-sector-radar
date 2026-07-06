"""
每日健康检查

检查每日生产流程的完整性和数据质量。
"""

import json
import os
from typing import Any, Dict, List


class DailyHealthCheck:
    """
    每日健康检查

    检查每日生产流程的完整性和数据质量。
    """

    def __init__(self, report_root: str = "reports", cache_root: str = "data_cache"):
        self.report_root = report_root
        self.cache_root = cache_root

    def run_check(self, as_of_date: str) -> Dict[str, Any]:
        """
        运行健康检查

        Args:
            as_of_date: 检查日期

        Returns:
            健康检查结果
        """
        checks = {}

        # 1. Radar report
        checks["radar"] = self._check_radar(as_of_date)

        # 2. Sector score
        checks["sector_score"] = self._check_sector_score(as_of_date)

        # 3. Multi-window consensus
        checks["multi_window"] = self._check_multi_window(as_of_date)

        # 4. Sector research
        checks["sector_research"] = self._check_sector_research(as_of_date)

        # 5. Research index
        checks["research_index"] = self._check_research_index(as_of_date)

        # 6. Catalyst cache
        checks["catalyst_cache"] = self._check_catalyst_cache(as_of_date)

        # 7. Data source mode
        checks["data_source"] = self._check_data_source(as_of_date)

        # 计算总体状态
        overall_status = self._compute_overall_status(checks)

        # 生成摘要
        summary = {
            "as_of_date": as_of_date,
            "overall_status": overall_status,
            "data_source_mode": checks.get("data_source", {}).get("mode", "unknown"),
            "radar_status": checks.get("radar", {}).get("status", "unknown"),
            "research_status": checks.get("sector_research", {}).get("status", "unknown"),
            "catalyst_status": checks.get("catalyst_cache", {}).get("status", "unknown"),
            "checks": checks,
            "warnings": self._collect_warnings(checks),
            "key_outputs": self._collect_key_outputs(as_of_date),
        }

        return summary

    def _check_radar(self, as_of_date: str) -> Dict[str, Any]:
        """检查 Radar report"""
        radar_path = os.path.join(
            self.report_root, "theme_sector_radar", as_of_date, "theme_sector_radar.json"
        )
        run_log_path = os.path.join(
            self.report_root, "theme_sector_radar", as_of_date, "run_log.json"
        )

        result = {
            "exists": os.path.exists(radar_path),
            "run_log_exists": os.path.exists(run_log_path),
            "status": "missing",
        }

        if result["exists"]:
            try:
                with open(radar_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result["status"] = data.get("status", "unknown")
                result["data_quality_score"] = data.get("data_quality_score", 0)
                result["provider"] = data.get("provider_status", {}).get("effective_provider", "unknown")
                result["data_source_mode"] = data.get("data_source_mode", "unknown")
            except Exception:
                result["status"] = "error"

        return result

    def _check_sector_score(self, as_of_date: str) -> Dict[str, Any]:
        """检查 Sector score"""
        score_path = os.path.join(
            self.report_root, "sector_scores", as_of_date, "sector_scores.json"
        )

        result = {
            "exists": os.path.exists(score_path),
            "status": "missing",
        }

        if result["exists"]:
            try:
                with open(score_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                scores = data.get("scores", [])
                result["status"] = "ok"
                result["sector_count"] = len(scores)
            except Exception:
                result["status"] = "error"

        return result

    def _check_multi_window(self, as_of_date: str) -> Dict[str, Any]:
        """检查 Multi-window consensus"""
        mw_path = os.path.join(
            self.report_root, "sector_consensus", as_of_date, "multi_window_consensus.json"
        )

        result = {
            "exists": os.path.exists(mw_path),
            "status": "missing",
        }

        if result["exists"]:
            result["status"] = "ok"

        return result

    def _check_sector_research(self, as_of_date: str) -> Dict[str, Any]:
        """检查 Sector research"""
        research_path = os.path.join(
            self.report_root, "sector_research", as_of_date, "sector_research.json"
        )
        md_path = os.path.join(
            self.report_root, "sector_research", as_of_date, "sector_research.md"
        )

        result = {
            "exists": os.path.exists(research_path),
            "md_exists": os.path.exists(md_path),
            "status": "missing",
        }

        if result["exists"]:
            try:
                with open(research_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                results_list = data.get("research_results", [])
                result["status"] = "ok"
                result["sector_count"] = len(results_list)
                result["has_daily_summary"] = "daily_summary" in data
                result["has_agent_opinions"] = all(
                    "agent_opinions" in r for r in results_list
                ) if results_list else False
            except Exception:
                result["status"] = "error"

        return result

    def _check_research_index(self, as_of_date: str) -> Dict[str, Any]:
        """检查 Research index"""
        index_path = os.path.join(
            self.report_root, "sector_research", "index", "research_index.json"
        )

        result = {
            "exists": os.path.exists(index_path),
            "status": "missing",
        }

        if result["exists"]:
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                dates = data.get("dates", [])
                result["status"] = "ok"
                result["total_days"] = data.get("total_days", 0)
                result["has_current_date"] = as_of_date in dates
            except Exception:
                result["status"] = "error"

        return result

    def _check_catalyst_cache(self, as_of_date: str) -> Dict[str, Any]:
        """检查 Catalyst cache"""
        cache_path = os.path.join(
            self.cache_root, "catalyst_events", as_of_date, "events.json"
        )
        status_path = os.path.join(
            self.cache_root, "catalyst_events", as_of_date, "source_status.json"
        )

        result = {
            "exists": os.path.exists(cache_path),
            "status_exists": os.path.exists(status_path),
            "status": "missing",
        }

        if result["exists"]:
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                events = data.get("events", [])
                result["status"] = "ok"
                result["event_count"] = len(events)
                result["real_count"] = sum(1 for e in events if e.get("source") != "fixture")
                result["fixture_count"] = sum(1 for e in events if e.get("source") == "fixture")
            except Exception:
                result["status"] = "error"

        return result

    def _check_data_source(self, as_of_date: str) -> Dict[str, Any]:
        """检查数据来源模式"""
        radar_path = os.path.join(
            self.report_root, "theme_sector_radar", as_of_date, "theme_sector_radar.json"
        )

        result = {"mode": "unknown"}

        if os.path.exists(radar_path):
            try:
                with open(radar_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result["mode"] = data.get("data_source_mode", "unknown")
            except Exception:
                pass

        return result

    def _compute_overall_status(self, checks: Dict[str, Any]) -> str:
        """计算总体状态"""
        radar_status = checks.get("radar", {}).get("status", "missing")
        research_status = checks.get("sector_research", {}).get("status", "missing")
        data_source = checks.get("data_source", {}).get("mode", "unknown")

        # 检查 fixture/replay 混入
        if data_source in ["fixture", "replay"]:
            return "audit_required"

        # 核心报告缺失
        if radar_status == "missing" or research_status == "missing":
            return "failed"

        # 部分降级
        if radar_status == "degraded" or research_status == "degraded":
            return "degraded"

        return "ok"

    def _collect_warnings(self, checks: Dict[str, Any]) -> List[str]:
        """收集警告"""
        warnings = []

        data_source = checks.get("data_source", {}).get("mode", "unknown")
        if data_source in ["fixture", "replay"]:
            warnings.append(f"检测到 {data_source} 数据混入 real daily")

        catalyst_status = checks.get("catalyst_cache", {}).get("status", "missing")
        if catalyst_status == "missing":
            warnings.append("catalyst cache 缺失")

        return warnings

    def _collect_key_outputs(self, as_of_date: str) -> Dict[str, str]:
        """收集关键输出路径"""
        return {
            "radar_report": os.path.join(self.report_root, "theme_sector_radar", as_of_date),
            "sector_research": os.path.join(self.report_root, "sector_research", as_of_date),
            "research_index": os.path.join(self.report_root, "sector_research", "index"),
            "health_report": os.path.join(self.report_root, "daily_health", as_of_date),
        }


def save_daily_health_check(output_dir: str, check_data: Dict[str, Any]):
    """保存健康检查结果"""
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "daily_health_check.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(check_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON saved: {json_path}")

    md_report = generate_daily_health_check_md(check_data)
    md_path = os.path.join(output_dir, "daily_health_check.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown saved: {md_path}")


def generate_daily_health_check_md(check_data: Dict[str, Any]) -> str:
    """生成健康检查 Markdown 报告"""
    lines = []

    lines.append("# 每日健康检查报告")
    lines.append("")

    as_of_date = check_data.get("as_of_date", "")
    overall = check_data.get("overall_status", "unknown")

    # 状态指示
    status_emoji = {"ok": "✅", "degraded": "⚠️", "failed": "❌", "audit_required": "🔍"}.get(overall, "❓")
    lines.append(f"## {status_emoji} 总体状态: {overall}")
    lines.append("")
    lines.append(f"- **日期**: {as_of_date}")
    lines.append(f"- **数据来源模式**: {check_data.get('data_source_mode', 'unknown')}")
    lines.append("")

    # 各项检查
    checks = check_data.get("checks", {})

    for check_name, check_data_item in checks.items():
        status = check_data_item.get("status", "unknown")
        status_icon = {"ok": "✅", "degraded": "⚠️", "missing": "❌", "error": "❌"}.get(status, "❓")
        lines.append(f"### {status_icon} {check_name}")
        lines.append("")
        for k, v in check_data_item.items():
            if k != "status":
                lines.append(f"- **{k}**: {v}")
        lines.append("")

    # 警告
    warnings = check_data.get("warnings", [])
    if warnings:
        lines.append("## 警告")
        lines.append("")
        for w in warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    # 关键输出
    key_outputs = check_data.get("key_outputs", {})
    if key_outputs:
        lines.append("## 关键输出路径")
        lines.append("")
        for k, v in key_outputs.items():
            lines.append(f"- **{k}**: `{v}`")
        lines.append("")

    lines.append("---")
    lines.append("*本报告由 Theme Sector Radar 自动生成。*")

    return "\n".join(lines)
