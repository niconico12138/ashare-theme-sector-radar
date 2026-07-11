"""Load existing artifacts for the joint decision layer."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path, warnings: list[str], rel_path: str) -> dict[str, Any]:
    if not path.exists():
        warnings.append(f"missing:{rel_path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        warnings.append(f"unreadable:{rel_path}:{exc}")
        return {}


def _read_concepts_csv(path: Path, warnings: list[str], rel_path: str) -> list[dict[str, Any]]:
    if not path.exists():
        warnings.append(f"missing:{rel_path}")
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        warnings.append(f"unreadable:{rel_path}:{exc}")
        return []


def load_joint_decision_inputs(
    as_of: str,
    project_root: str | Path,
) -> dict[str, Any]:
    """Load the artifacts produced by the existing three-project pipeline."""
    root = Path(project_root)
    warnings: list[str] = []

    unified_rel = f"reports/unified/{as_of}/unified_report.json"
    top30_rel = f"reports/agent_bridge/{as_of}/top30_candidates.json"
    ranking_rel = f"reports/agent_bridge/{as_of}/aihf_stock_ranking.json"
    sector_rel = f"reports/full90/sector_research/{as_of}/sector_research.json"
    concept_rel = f"reports/full_concept/unified_rank/{as_of}/concept_unified_rank.csv"
    v2_rel = "reports/factor_composite_shadow_score/v2_shadow_monitor.json"

    unified_report = _read_json(root / unified_rel, warnings, unified_rel)
    top30 = _read_json(root / top30_rel, warnings, top30_rel)
    aihf_ranking = _read_json(root / ranking_rel, warnings, ranking_rel)
    sector_research = _read_json(root / sector_rel, warnings, sector_rel)
    v2_monitor = _read_json(root / v2_rel, warnings, v2_rel)
    concepts = _read_concepts_csv(root / concept_rel, warnings, concept_rel)

    sectors = [
        item for item in sector_research.get("research_results", [])
        if isinstance(item, dict) and item.get("sector_type") == "industry"
    ]

    return {
        "unified_report": unified_report,
        "top30": top30,
        "aihf_ranking": aihf_ranking,
        "sectors": sectors,
        "concepts": concepts,
        "v2_monitor": v2_monitor,
        "load_warnings": warnings,
    }
