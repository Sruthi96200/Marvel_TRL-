#!/usr/bin/env python3
# run_gap_analysis.py — Evidence gap analysis (proposal: GAP ANALYZER agent)
# Input:  data/scored/{subsystem}_scored.json, data/trl/MARVEL_TRL_REPORT.json
# Output: data/gaps/MARVEL_GAP_REPORT.json

import json
import os

from config.subsystems import MARVEL_SUBSYSTEMS
from src.tools.gap_analyzer import build_gap_report


def main() -> None:
    repo = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo)

    out_dir = "data/gaps"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "MARVEL_GAP_REPORT.json")

    keys = list(MARVEL_SUBSYSTEMS.keys())
    names = {k: MARVEL_SUBSYSTEMS[k]["name"] for k in keys}

    report = build_gap_report(
        keys,
        names,
        "data/scored",
        "data/trl/MARVEL_TRL_REPORT.json",
    )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("MARVEL Gap Analyzer")
    print("=" * 60)
    print(f"Peer median documents: {report['peer_median_document_count']}")
    print(f"Top gap pressure: {report['summary']['highest_gap_pressure_subsystems']}")
    print()
    for key in keys:
        s = report["subsystems"].get(key, {})
        print(
            f"  {s.get('name', key)[:42]:<42}  "
            f"index {s.get('gap_index', 0):>3}  {s.get('coverage_label', '?')}"
        )
    print()
    print(f"Wrote {out_path}")
    print("Next: python3 generate_dashboard.py")


if __name__ == "__main__":
    main()
