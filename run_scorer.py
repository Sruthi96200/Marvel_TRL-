# run_scorer.py
# Runs the Evidence Quality Scorer on all 6 scraped subsystem files
# Input:  data/raw/{subsystem}_results.json
# Output: data/scored/{subsystem}_scored.json

from src.tools.evidence_scorer import EvidenceQualityScorer
from config.subsystems import MARVEL_SUBSYSTEMS
import os

def run_scoring():
    scorer = EvidenceQualityScorer()

    os.makedirs("data/scored", exist_ok=True)

    print("MARVEL TRL Assessment - Evidence Quality Scorer")
    print("="*60)

    all_stats = {}

    for key in MARVEL_SUBSYSTEMS.keys():
        input_path  = f"data/raw/{key}_results.json"
        output_path = f"data/scored/{key}_scored.json"

        # Skip if raw file doesn't exist yet
        if not os.path.exists(input_path):
            print(f"⚠️  Skipping {key} — no raw file found at {input_path}")
            continue

        print(f"\n📊 Scoring: {MARVEL_SUBSYSTEMS[key]['name']}")
        stats = scorer.score_subsystem_file(input_path, output_path)
        all_stats[key] = stats

        print(f"   Total docs:    {stats['total_documents']}")
        print(f"   Avg score:     {stats['avg_quality_score']}")
        print(f"   HIGH quality:  {stats['high_quality']} docs")
        print(f"   MEDIUM quality:{stats['medium_quality']} docs")
        print(f"   LOW quality:   {stats['low_quality']} docs")
        print(f"   Top document:  {stats['top_document'][:70]}")
        print(f"   💾 Saved to:   {output_path}")

    # Final summary table
    print("\n" + "="*60)
    print("OVERALL SUMMARY")
    print("="*60)
    print(f"{'Subsystem':<45} {'Avg':>5}  {'HIGH':>5}  {'MED':>5}  {'LOW':>5}")
    print("-"*60)

    total_docs = 0
    total_high = 0
    for key, stats in all_stats.items():
        name = MARVEL_SUBSYSTEMS[key]["name"][:44]
        total_docs += stats["total_documents"]
        total_high += stats["high_quality"]
        print(f"{name:<45} {stats['avg_quality_score']:>5}  {stats['high_quality']:>5}  {stats['medium_quality']:>5}  {stats['low_quality']:>5}")

    print("-"*60)
    print(f"{'TOTAL':<45} {'':>5}  {total_high:>5}  {'':>5}  {'':>5}")
    print(f"\nTotal documents scored: {total_docs}")
    print(f"High quality evidence:  {total_high} docs ready for TRL inference")

if __name__ == "__main__":
    run_scoring()