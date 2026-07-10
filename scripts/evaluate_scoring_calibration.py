#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluate whether score layers have useful forward-return separation.

This is an offline calibration helper: it does not fetch market data and does
not change any production scoring formula. Pass a candidate pool plus a JSON
mapping of code -> horizon -> return percentage.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGENT_BRIDGE_DIR = PROJECT_ROOT / "reports" / "agent_bridge"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "scoring_calibration"
DEFAULT_HORIZONS = ("1d", "3d", "5d")

SCORE_LAYERS = {
    "final_score": ("v3_final_score", "final_score"),
    "quant_score": ("quant_score",),
    "agent_score": ("agent_score", "risk_adjusted_score", "ranking_score"),
    "trend_score": ("trend_score", "sector_trend_score"),
    "burst_score": ("burst_score", "sector_burst_score"),
    "relevance_score": ("relevance_score",),
}

BUCKET_ORDER = ("80+", "60-80", "40-60", "<40", "missing")


def _coerce_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_numeric(item: dict, keys: Iterable[str]) -> float | None:
    for key in keys:
        value = _coerce_float(item.get(key))
        if value is not None:
            return value
    return None


def assign_score_bucket(score) -> str:
    value = _coerce_float(score)
    if value is None:
        return "missing"
    if value >= 80:
        return "80+"
    if value >= 60:
        return "60-80"
    if value >= 40:
        return "40-60"
    return "<40"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_candidates(path: Path) -> list[dict]:
    data = load_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        candidates = data.get("candidates", [])
        return candidates if isinstance(candidates, list) else []
    return []


def load_forward_returns(path: Path) -> dict:
    data = load_json(path)
    if isinstance(data, dict) and isinstance(data.get("forward_returns"), dict):
        return data["forward_returns"]
    return data if isinstance(data, dict) else {}


def _empty_horizon_stats(horizons: Iterable[str]) -> dict:
    return {
        horizon: {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}
        for horizon in horizons
    }


def _summarize_returns(values: list[float]) -> dict:
    if not values:
        return {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}
    return {
        "sample_count": len(values),
        "avg_return_pct": round(sum(values) / len(values), 4),
        "hit_rate": round(sum(1 for value in values if value > 0) / len(values), 4),
    }


def evaluate_score_layers(
    candidates: list[dict],
    forward_returns: dict,
    horizons: Iterable[str] = DEFAULT_HORIZONS,
    as_of: str | None = None,
) -> dict:
    horizons = tuple(horizons)
    candidate_codes = [str(item.get("code", "")).strip() for item in candidates if item.get("code")]
    covered_codes = []
    for code in candidate_codes:
        code_returns = forward_returns.get(code)
        if not isinstance(code_returns, dict):
            continue
        if any(_coerce_float(code_returns.get(horizon)) is not None for horizon in horizons):
            covered_codes.append(code)
    candidate_count = len(candidates)

    result = {
        "schema_version": "1.0",
        "analysis_date": datetime.now().isoformat(),
        "as_of": as_of,
        "horizons": list(horizons),
        "coverage": {
            "candidate_count": candidate_count,
            "forward_return_count": len(set(covered_codes)),
            "missing_forward_return_count": max(candidate_count - len(set(covered_codes)), 0),
            "coverage_ratio": round(len(set(covered_codes)) / candidate_count, 4) if candidate_count else 0,
        },
        "layers": {},
    }

    for layer_name, keys in SCORE_LAYERS.items():
        bucket_values: dict[str, dict[str, list[float]]] = {
            bucket: defaultdict(list) for bucket in BUCKET_ORDER
        }
        bucket_counts = {bucket: 0 for bucket in BUCKET_ORDER}

        for item in candidates:
            score = _first_numeric(item, keys)
            bucket = assign_score_bucket(score)
            bucket_counts[bucket] += 1
            code = str(item.get("code", "")).strip()
            code_returns = forward_returns.get(code, {})
            if not isinstance(code_returns, dict):
                continue
            for horizon in horizons:
                ret = _coerce_float(code_returns.get(horizon))
                if ret is not None:
                    bucket_values[bucket][horizon].append(ret)

        result["layers"][layer_name] = {
            "source_fields": list(keys),
            "buckets": {
                bucket: {
                    "candidate_count": bucket_counts[bucket],
                    "horizons": {
                        horizon: _summarize_returns(bucket_values[bucket].get(horizon, []))
                        for horizon in horizons
                    },
                }
                for bucket in BUCKET_ORDER
            },
        }

        for bucket in BUCKET_ORDER:
            result["layers"][layer_name]["buckets"][bucket]["horizons"].update(
                {
                    horizon: result["layers"][layer_name]["buckets"][bucket]["horizons"].get(
                        horizon,
                        _empty_horizon_stats((horizon,))[horizon],
                    )
                    for horizon in horizons
                }
            )

    return result


def generate_markdown_report(result: dict) -> str:
    lines = [
        "# Scoring Calibration Report",
        "",
        f"**Analysis Date**: {result.get('analysis_date', '')}",
        f"**As Of**: {result.get('as_of') or '-'}",
        "",
        "## Forward Return Coverage",
        "",
    ]
    coverage = result.get("coverage", {})
    lines.extend(
        [
            f"- **Candidates**: {coverage.get('candidate_count', 0)}",
            f"- **With Forward Returns**: {coverage.get('forward_return_count', 0)}",
            f"- **Missing Forward Returns**: {coverage.get('missing_forward_return_count', 0)}",
            f"- **Coverage Ratio**: {coverage.get('coverage_ratio', 0):.1%}",
            "",
        ]
    )

    horizons = result.get("horizons", [])
    for layer_name, layer in result.get("layers", {}).items():
        lines.append(f"## {layer_name}")
        lines.append("")
        header = "| Bucket | Candidates | " + " | ".join(f"{h} Avg | {h} Hit | {h} N" for h in horizons) + " |"
        separator = "|--------|------------|" + "|".join(["---------|--------|------" for _ in horizons]) + "|"
        lines.append(header)
        lines.append(separator)
        for bucket in BUCKET_ORDER:
            bucket_data = layer.get("buckets", {}).get(bucket, {})
            cells = [bucket, str(bucket_data.get("candidate_count", 0))]
            for horizon in horizons:
                stats = bucket_data.get("horizons", {}).get(horizon, {})
                avg = stats.get("avg_return_pct")
                hit = stats.get("hit_rate")
                cells.append("-" if avg is None else f"{avg:.2f}%")
                cells.append("-" if hit is None else f"{hit:.1%}")
                cells.append(str(stats.get("sample_count", 0)))
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate score layer forward-return calibration")
    parser.add_argument("--as-of", required=True, help="Candidate pool date, YYYY-MM-DD")
    parser.add_argument("--candidate-path", default=None, help="Path to top30_candidates.json")
    parser.add_argument("--returns-json", required=True, help="Path to forward returns JSON")
    parser.add_argument("--horizons", default="1d,3d,5d", help="Comma-separated horizons in returns JSON")
    parser.add_argument("--output-dir", default=None, help="Base output directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candidate_path = Path(args.candidate_path) if args.candidate_path else DEFAULT_AGENT_BRIDGE_DIR / args.as_of / "top30_candidates.json"
    returns_path = Path(args.returns_json)
    output_base = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    output_dir = output_base / args.as_of
    horizons = tuple(h.strip() for h in args.horizons.split(",") if h.strip())

    if not candidate_path.exists():
        print(f"ERROR: candidate file not found: {candidate_path}", file=sys.stderr)
        return 2
    if not returns_path.exists():
        print(f"ERROR: returns file not found: {returns_path}", file=sys.stderr)
        return 2

    candidates = load_candidates(candidate_path)
    forward_returns = load_forward_returns(returns_path)
    result = evaluate_score_layers(candidates, forward_returns, horizons=horizons, as_of=args.as_of)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "scoring_calibration.json"
    md_path = output_dir / "scoring_calibration.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(generate_markdown_report(result), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print(
        "Coverage: "
        f"{result['coverage']['forward_return_count']}/{result['coverage']['candidate_count']} "
        f"({result['coverage']['coverage_ratio']:.1%})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
