#!/usr/bin/env python3
"""Audit paper-only timing strategies for overfit risk."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_timing_combination_experiment import (  # noqa: E402
    CANDIDATE_FILE_NAMES,
    _candidate_rows,
    _discover_candidate_files,
    _float,
    _load_json,
    _load_selection_validation_returns,
)
from theme_sector_radar.factors.calculators import calculate_intraday_factors  # noqa: E402
from theme_sector_radar.timing.combination_experiment import (  # noqa: E402
    FactorCondition,
    StrategyVersion,
    build_default_strategy_versions,
    evaluate_strategy_stability,
    evaluate_strategy_versions,
)


FOCUS_VERSION_IDS = {
    "v27_position_watch_calm_recovery",
    "v28_operational_turnover_cashout_guard",
    "v29_operational_tradeability_turnover",
    "v30_operational_position_turnover_guard",
}


def run_overfit_audit(
    *,
    candidate_root_5m: Path,
    candidate_root_1m: Path | None,
    output_dir: Path,
    as_of: str,
    snapshot_label: str,
    start: str | None = None,
    end: str | None = None,
    selection_validation_root: Path | None = PROJECT_ROOT / "reports" / "selection_validation",
    coverage_roots: Sequence[Path] = (),
    min_selected: int = 20,
) -> dict[str, Any]:
    versions = _focus_versions()
    report = {
        "schema_version": "timing_strategy_overfit_audit.v1",
        "as_of": as_of,
        "snapshot_label": snapshot_label,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "parameters": {
            "start": start,
            "end": end,
            "min_selected": min_selected,
            "candidate_root_5m": str(candidate_root_5m),
            "candidate_root_1m": str(candidate_root_1m) if candidate_root_1m else None,
            "selection_validation_root": str(selection_validation_root) if selection_validation_root else None,
        },
        "coverage_audit": _coverage_audit(
            [candidate_root_5m] + ([candidate_root_1m] if candidate_root_1m else []) + list(coverage_roots),
            start,
            end,
        ),
        "datasets": {},
    }

    datasets: list[tuple[str, Path | None]] = [("5m", candidate_root_5m), ("1m", candidate_root_1m)]
    for label, root in datasets:
        if root is None:
            continue
        samples = _load_samples(root, start, end, selection_validation_root)
        dataset_report = _audit_dataset(samples, versions, min_selected=min_selected)
        dataset_report["source_root"] = str(root)
        report["datasets"][label] = dataset_report

    report["cross_frequency"] = _cross_frequency_summary(report["datasets"])
    report["v29_overfit_judgement"] = _judge_v29_overfit(report)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"v29_overfit_audit_{as_of}_{snapshot_label}.json"
    markdown_path = output_dir / f"v29_overfit_audit_{as_of}_{snapshot_label}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    return {"status": "ok", "json_path": json_path, "markdown_path": markdown_path, "report": report}


def _focus_versions() -> list[StrategyVersion]:
    versions = [item for item in build_default_strategy_versions() if item.version_id in FOCUS_VERSION_IDS]
    order = {version_id: index for index, version_id in enumerate(sorted(FOCUS_VERSION_IDS))}
    return sorted(versions, key=lambda item: order[item.version_id])


def _load_samples(
    candidate_root: Path,
    start: str | None,
    end: str | None,
    selection_validation_root: Path | None,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for path in _discover_candidate_files(candidate_root, start, end):
        date = path.parent.name
        dated_returns = _load_selection_validation_returns(selection_validation_root, date)
        for row in _candidate_rows(_load_json(path)):
            code = str(row.get("code") or "").strip()
            enriched = dict(row)
            enriched["_sample_date"] = date
            if enriched.get("forward_return_pct") is None and code in dated_returns:
                enriched["forward_return_pct"] = dated_returns[code]
            _backfill_intraday_factors_in_memory(enriched)
            samples.append(enriched)
    return samples


def _backfill_intraday_factors_in_memory(row: dict[str, Any]) -> None:
    if row.get("execution_tradeability_score") is not None:
        return
    bars = row.get("intraday_bars") or row.get("minute_bars") or row.get("ticks")
    if not isinstance(bars, list) or len(bars) < 3:
        return
    for key, value in calculate_intraday_factors(row).items():
        if row.get(key) is None:
            row[key] = value


def _audit_dataset(samples: list[dict[str, Any]], versions: list[StrategyVersion], *, min_selected: int) -> dict[str, Any]:
    threshold_versions = _v29_threshold_grid()
    return {
        "summary": _sample_summary(samples),
        "version_comparison": evaluate_strategy_versions(samples, versions, min_selected=min_selected),
        "stability_3_period": evaluate_strategy_stability(samples, versions, min_selected=min_selected, period_count=3),
        "stability_5_period": evaluate_strategy_stability(samples, versions, min_selected=min_selected, period_count=5),
        "threshold_perturbation": evaluate_strategy_versions(samples, threshold_versions, min_selected=max(5, min_selected // 2)),
        "walk_forward": _walk_forward(samples, threshold_versions, min_selected=max(5, min_selected // 2)),
        "market_regime": _market_regime_breakdown(samples, versions, min_selected=max(5, min_selected // 2)),
        "concentration": _selection_concentration(samples, versions),
    }


def _sample_summary(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(row.get("_sample_date")) for row in samples if row.get("_sample_date")})
    labeled = [row for row in samples if _float(row.get("forward_return_pct")) is not None]
    with_v29_fields = [
        row
        for row in samples
        if row.get("execution_tradeability_score") is not None and row.get("execution_turnover_depth_score") is not None
    ]
    return {
        "sample_count": len(samples),
        "labeled_sample_count": len(labeled),
        "date_count": len(dates),
        "start": dates[0] if dates else None,
        "end": dates[-1] if dates else None,
        "rows_with_v29_operational_fields": len(with_v29_fields),
        "v29_field_coverage_rate": round(len(with_v29_fields) / len(samples), 4) if samples else None,
    }


def _v29_threshold_grid() -> list[StrategyVersion]:
    base = next(item for item in build_default_strategy_versions() if item.version_id == "v29_operational_tradeability_turnover")
    versions: list[StrategyVersion] = []
    for tradeability in (55.0, 60.0, 65.0, 70.0):
        for turnover in (60.0, 70.0, 80.0):
            conditions = []
            for condition in base.conditions:
                if condition.factor_id == "execution_tradeability_score":
                    conditions.append(replace(condition, threshold=tradeability))
                elif condition.factor_id == "execution_turnover_depth_score":
                    conditions.append(replace(condition, threshold=turnover))
                else:
                    conditions.append(condition)
            versions.append(
                StrategyVersion(
                    f"v29_grid_trade_{int(tradeability)}_turnover_{int(turnover)}",
                    f"v29 threshold perturbation: tradeability >= {tradeability}, turnover >= {turnover}.",
                    tuple(conditions),
                )
            )
    return versions


def _walk_forward(samples: list[dict[str, Any]], versions: list[StrategyVersion], *, min_selected: int) -> dict[str, Any]:
    dates = sorted({str(row.get("_sample_date")) for row in samples if row.get("_sample_date")})
    periods = _date_periods(dates, 4)
    folds = []
    for index in range(1, len(periods)):
        train_dates = {date for period in periods[:index] for date in period}
        test_dates = set(periods[index])
        train_rows = [row for row in samples if str(row.get("_sample_date")) in train_dates]
        test_rows = [row for row in samples if str(row.get("_sample_date")) in test_dates]
        train_report = evaluate_strategy_versions(train_rows, versions, min_selected=min_selected)
        valid = [item for item in train_report["versions"] if item.get("is_valid")]
        chosen = valid[0] if valid else train_report["versions"][0] if train_report["versions"] else None
        chosen_version = next((version for version in versions if chosen and version.version_id == chosen.get("version_id")), None)
        test_report = evaluate_strategy_versions(test_rows, [chosen_version], min_selected=1) if chosen_version else None
        test_item = test_report["versions"][0] if test_report else None
        folds.append(
            {
                "fold_index": index,
                "train_start": min(train_dates) if train_dates else None,
                "train_end": max(train_dates) if train_dates else None,
                "test_start": min(test_dates) if test_dates else None,
                "test_end": max(test_dates) if test_dates else None,
                "chosen_version_id": chosen.get("version_id") if chosen else None,
                "train_selected_count": chosen.get("selected_count") if chosen else None,
                "train_avg_return_pct": chosen.get("selected_avg_return_pct") if chosen else None,
                "test_selected_count": test_item.get("selected_count") if test_item else None,
                "test_avg_return_pct": test_item.get("selected_avg_return_pct") if test_item else None,
                "test_win_rate": test_item.get("selected_win_rate") if test_item else None,
                "test_tail_loss_count": test_item.get("selected_tail_loss_count") if test_item else None,
            }
        )
    test_avgs = [item["test_avg_return_pct"] for item in folds if item["test_avg_return_pct"] is not None]
    active = [item for item in folds if (item.get("test_selected_count") or 0) > 0]
    positive = [value for value in test_avgs if value > 0]
    return {
        "schema_version": "timing_strategy_walk_forward.v1",
        "fold_count": len(folds),
        "active_fold_rate": round(len(active) / len(folds), 4) if folds else None,
        "positive_test_fold_rate": round(len(positive) / len(test_avgs), 4) if test_avgs else None,
        "avg_test_return_pct": round(sum(test_avgs) / len(test_avgs), 4) if test_avgs else None,
        "worst_test_return_pct": round(min(test_avgs), 4) if test_avgs else None,
        "folds": folds,
    }


def _market_regime_breakdown(samples: list[dict[str, Any]], versions: list[StrategyVersion], *, min_selected: int) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {"broad_up": [], "mixed": [], "broad_down": [], "missing": []}
    for row in samples:
        buckets[_market_regime_label(row)].append(row)
    reports = {}
    for label, rows in buckets.items():
        if not rows:
            continue
        reports[label] = evaluate_strategy_versions(rows, versions, min_selected=min_selected)
    return {
        "schema_version": "timing_strategy_market_regime_breakdown.v1",
        "bucket_sample_counts": {label: len(rows) for label, rows in buckets.items()},
        "buckets": reports,
    }


def _market_regime_label(row: Mapping[str, Any]) -> str:
    explicit = row.get("market_regime")
    if isinstance(explicit, str) and explicit:
        return explicit
    score = _float(row.get("market_regime_score"))
    if score is None:
        return "missing"
    if score >= 60.0:
        return "broad_up"
    if score <= 40.0:
        return "broad_down"
    return "mixed"


def _selection_concentration(samples: list[dict[str, Any]], versions: list[StrategyVersion]) -> dict[str, Any]:
    results = {}
    for version in versions:
        selected = [
            row
            for row in samples
            if _float(row.get("forward_return_pct")) is not None and all(condition.matches(row) for condition in version.conditions)
        ]
        results[version.version_id] = _concentration_stats(selected)
    return results


def _concentration_stats(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    dates: dict[str, int] = {}
    codes: dict[str, int] = {}
    boards: dict[str, int] = {}
    for row in rows:
        date = str(row.get("_sample_date") or "")
        code = str(row.get("code") or "")
        if date:
            dates[date] = dates.get(date, 0) + 1
        if code:
            codes[code] = codes.get(code, 0) + 1
        raw_boards = row.get("boards")
        if isinstance(raw_boards, list):
            for board in raw_boards:
                key = str(board)
                boards[key] = boards.get(key, 0) + 1
    count = len(rows)
    return {
        "selected_count": count,
        "max_single_date_share": _max_share(dates, count),
        "max_single_code_share": _max_share(codes, count),
        "max_single_board_share": _max_share(boards, count),
        "top_dates": _top_counts(dates),
        "top_codes": _top_counts(codes),
        "top_boards": _top_counts(boards),
    }


def _max_share(counts: Mapping[str, int], total: int) -> float | None:
    if not counts or total <= 0:
        return None
    return round(max(counts.values()) / total, 4)


def _top_counts(counts: Mapping[str, int], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {"key": key, "count": count}
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _coverage_audit(roots: Sequence[Path], start: str | None, end: str | None) -> list[dict[str, Any]]:
    result = []
    for root in roots:
        files = _discover_candidate_files(root, start, end)
        row_count = 0
        rows_with_bars = 0
        rows_with_v29_fields = 0
        dates = []
        for path in files:
            dates.append(path.parent.name)
            rows = _candidate_rows(_load_json(path))
            row_count += len(rows)
            for row in rows:
                bars = row.get("intraday_bars") or row.get("minute_bars") or row.get("ticks")
                if isinstance(bars, list) and len(bars) >= 3:
                    rows_with_bars += 1
                if row.get("execution_tradeability_score") is not None and row.get("execution_turnover_depth_score") is not None:
                    rows_with_v29_fields += 1
        result.append(
            {
                "root": str(root),
                "candidate_file_count": len(files),
                "row_count": row_count,
                "start": min(dates) if dates else None,
                "end": max(dates) if dates else None,
                "rows_with_intraday_bars": rows_with_bars,
                "intraday_bar_coverage_rate": round(rows_with_bars / row_count, 4) if row_count else None,
                "rows_with_v29_fields": rows_with_v29_fields,
                "v29_field_coverage_rate": round(rows_with_v29_fields / row_count, 4) if row_count else None,
                "candidate_file_names": list(CANDIDATE_FILE_NAMES),
            }
        )
    return result


def _cross_frequency_summary(datasets: Mapping[str, Any]) -> dict[str, Any]:
    summary = {}
    for version_id in FOCUS_VERSION_IDS:
        summary[version_id] = {}
        for label, dataset in datasets.items():
            versions = (dataset.get("version_comparison") or {}).get("versions") or []
            item = next((row for row in versions if row.get("version_id") == version_id), None)
            if item:
                summary[version_id][label] = {
                    "selected_count": item.get("selected_count"),
                    "avg_return_pct": item.get("selected_avg_return_pct"),
                    "win_rate": item.get("selected_win_rate"),
                    "tail_loss_count": item.get("selected_tail_loss_count"),
                    "min_return_pct": item.get("selected_min_return_pct"),
                }
    return summary


def _judge_v29_overfit(report: Mapping[str, Any]) -> dict[str, Any]:
    risk_points = []
    supporting_points = []
    for label, dataset in (report.get("datasets") or {}).items():
        comparison = (dataset.get("version_comparison") or {}).get("versions") or []
        v29 = next((item for item in comparison if item.get("version_id") == "v29_operational_tradeability_turnover"), None)
        if not v29:
            risk_points.append(f"{label}: v29 missing from comparison.")
            continue
        if (v29.get("selected_count") or 0) < 30:
            risk_points.append(f"{label}: selected_count {v29.get('selected_count')} is below 30.")
        else:
            supporting_points.append(f"{label}: selected_count reaches {v29.get('selected_count')}.")
        if (v29.get("selected_tail_loss_count") or 0) == 0:
            supporting_points.append(f"{label}: no tail loss in current sample.")
        stability = dataset.get("stability_5_period") or {}
        v29_stability = next(
            (item for item in stability.get("versions") or [] if item.get("version_id") == "v29_operational_tradeability_turnover"),
            None,
        )
        if v29_stability and (v29_stability.get("active_period_rate") or 0) < 0.8:
            risk_points.append(f"{label}: active_period_rate {v29_stability.get('active_period_rate')} is below 0.8.")
        if v29_stability and (v29_stability.get("min_period_selected_count") or 0) <= 1:
            risk_points.append(f"{label}: min_period_selected_count {v29_stability.get('min_period_selected_count')} is too thin.")
        walk = dataset.get("walk_forward") or {}
        if walk.get("active_fold_rate") is not None and walk.get("active_fold_rate") < 0.8:
            risk_points.append(f"{label}: walk-forward active_fold_rate {walk.get('active_fold_rate')} is below 0.8.")
        if walk.get("positive_test_fold_rate") is not None and walk.get("positive_test_fold_rate") < 0.75:
            risk_points.append(f"{label}: walk-forward positive_test_fold_rate {walk.get('positive_test_fold_rate')} is weak.")
        elif walk.get("positive_test_fold_rate") is not None:
            supporting_points.append(f"{label}: walk-forward positive_test_fold_rate {walk.get('positive_test_fold_rate')}.")
        concentration = ((dataset.get("concentration") or {}).get("v29_operational_tradeability_turnover") or {})
        board_share = concentration.get("max_single_board_share")
        if board_share is not None and board_share > 0.6:
            risk_points.append(f"{label}: max_single_board_share {board_share} is above 0.6.")
    coverage = report.get("coverage_audit") or []
    for item in coverage:
        if item.get("row_count") and item.get("intraday_bar_coverage_rate") == 0:
            risk_points.append(f"Coverage limit: {item.get('root')} has no intraday bars for v29 expansion validation.")
    risk_level = "high" if len(risk_points) >= 3 else "medium" if risk_points else "low"
    return {
        "risk_level": risk_level,
        "risk_points": risk_points,
        "supporting_points": supporting_points,
        "recommendation": "Keep v29 in paper trading and require broader intraday coverage plus walk-forward stability before promotion.",
    }


def _date_periods(dates: list[str], period_count: int) -> list[list[str]]:
    if not dates:
        return []
    count = max(1, min(period_count, len(dates)))
    return [dates[index * len(dates) // count : (index + 1) * len(dates) // count] for index in range(count)]


def _markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V29 Overfit Audit",
        "",
        f"As of: `{report.get('as_of')}`",
        f"Snapshot: `{report.get('snapshot_label')}`",
        "",
        "- Paper-only: `True`",
        "- No execution signals: `True`",
        "- Does not modify official scores: `True`",
        "",
        "## Judgement",
        "",
        f"- Risk level: `{(report.get('v29_overfit_judgement') or {}).get('risk_level')}`",
        f"- Recommendation: {(report.get('v29_overfit_judgement') or {}).get('recommendation')}",
        "",
        "### Risk Points",
        "",
    ]
    for item in (report.get("v29_overfit_judgement") or {}).get("risk_points") or []:
        lines.append(f"- {item}")
    lines.extend(["", "### Supporting Points", ""])
    for item in (report.get("v29_overfit_judgement") or {}).get("supporting_points") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Coverage Audit", "", "| Root | Files | Rows | Bars % | V29 fields % | Range |", "|---|---:|---:|---:|---:|---|"])
    for item in report.get("coverage_audit") or []:
        lines.append(
            f"| `{item.get('root')}` | {item.get('candidate_file_count')} | {item.get('row_count')} | "
            f"{item.get('intraday_bar_coverage_rate')} | {item.get('v29_field_coverage_rate')} | "
            f"{item.get('start')} to {item.get('end')} |"
        )
    for label, dataset in (report.get("datasets") or {}).items():
        lines.extend(["", f"## Dataset {label}", "", "### Focus Versions", ""])
        lines.extend(["| Version | Selected | Avg % | Win | Min % | Tail |", "|---|---:|---:|---:|---:|---:|"])
        for item in (dataset.get("version_comparison") or {}).get("versions") or []:
            lines.append(
                f"| `{item.get('version_id')}` | {item.get('selected_count')} | "
                f"{item.get('selected_avg_return_pct')} | {item.get('selected_win_rate')} | "
                f"{item.get('selected_min_return_pct')} | {item.get('selected_tail_loss_count')} |"
            )
        lines.extend(["", "### Walk Forward", ""])
        walk = dataset.get("walk_forward") or {}
        lines.append(
            f"- Active fold rate: `{walk.get('active_fold_rate')}`; positive test fold rate: "
            f"`{walk.get('positive_test_fold_rate')}`; avg test return: `{walk.get('avg_test_return_pct')}`; "
            f"worst test return: `{walk.get('worst_test_return_pct')}`"
        )
        lines.extend(["", "### Threshold Perturbation Top 5", ""])
        lines.extend(["| Version | Selected | Avg % | Win | Tail |", "|---|---:|---:|---:|---:|"])
        for item in ((dataset.get("threshold_perturbation") or {}).get("versions") or [])[:5]:
            lines.append(
                f"| `{item.get('version_id')}` | {item.get('selected_count')} | "
                f"{item.get('selected_avg_return_pct')} | {item.get('selected_win_rate')} | "
                f"{item.get('selected_tail_loss_count')} |"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit v29 overfit risk with paper-only timing samples")
    parser.add_argument("--candidate-root-5m", required=True)
    parser.add_argument("--candidate-root-1m")
    parser.add_argument("--coverage-root", action="append", default=[])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--selection-validation-root", default=str(PROJECT_ROOT / "reports" / "selection_validation"))
    parser.add_argument("--min-selected", type=int, default=20)
    args = parser.parse_args(argv)
    result = run_overfit_audit(
        candidate_root_5m=Path(args.candidate_root_5m),
        candidate_root_1m=Path(args.candidate_root_1m) if args.candidate_root_1m else None,
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        start=args.start,
        end=args.end,
        selection_validation_root=Path(args.selection_validation_root) if args.selection_validation_root else None,
        coverage_roots=[Path(item) for item in args.coverage_root],
        min_selected=args.min_selected,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
