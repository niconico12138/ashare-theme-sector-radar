"""Runner for the joint decision layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from theme_sector_radar.joint_decision.builder import build_joint_decision_summary
from theme_sector_radar.joint_decision.contract import validate_joint_decision_summary
from theme_sector_radar.joint_decision.loader import load_joint_decision_inputs
from theme_sector_radar.joint_decision.report import render_joint_decision_markdown


def run_joint_decision(
    as_of: str,
    project_root: str | Path,
    top_n: int = 10,
    output_root: str | Path | None = None,
) -> dict[str, Path]:
    root = Path(project_root)
    loaded = load_joint_decision_inputs(as_of, root)
    summary = build_joint_decision_summary(
        as_of=as_of,
        unified_report=loaded["unified_report"],
        sectors=loaded["sectors"],
        concepts=loaded["concepts"],
        top30=loaded["top30"],
        aihf_ranking=loaded["aihf_ranking"],
        v2_monitor=loaded["v2_monitor"],
        top_n=top_n,
        load_warnings=loaded["load_warnings"],
    )
    validation_errors = validate_joint_decision_summary(summary)
    summary.setdefault("audit", {})["contract_validation"] = {
        "status": "pass" if not validation_errors else "fail",
        "errors": validation_errors,
    }
    markdown = render_joint_decision_markdown(summary, top_n=top_n)

    out_dir = Path(output_root) if output_root else root / "reports" / "joint_decision" / as_of
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "joint_decision_summary.json"
    md_path = out_dir / "joint_decision_summary.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return {"json": json_path, "md": md_path}



