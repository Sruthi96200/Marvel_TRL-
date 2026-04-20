# run_trl_inference.py
# Runs TRL inference on all 6 scored subsystem files
# Input:  data/scored/{subsystem}_scored.json
# Output: data/trl/{subsystem}_trl.json
# Final:  data/trl/MARVEL_TRL_REPORT.json

import json
import os
from src.tools.trl_inferencer import TRLInferencer
from config.subsystems import MARVEL_SUBSYSTEMS


def run_inference():
    inferencer = TRLInferencer()

    os.makedirs("data/trl", exist_ok=True)

    print("MARVEL TRL Assessment - TRL Inference Engine")
    print("Using: Ollama llama3.2 (local)")
    print("="*60)

    all_trl_results = {}

    for key in MARVEL_SUBSYSTEMS.keys():
        scored_path = f"data/scored/{key}_scored.json"

        if not os.path.exists(scored_path):
            print(f"⚠️  Skipping {key} — no scored file found")
            continue

        # Load scored documents
        with open(scored_path) as f:
            data = json.load(f)

        subsystem_name = data["name"]
        documents = data.get("scored_documents", [])

        print(f"\n🔬 Inferring TRL: {subsystem_name}")
        print(f"   Using top {TRLInferencer.TOP_N_DOCS} of {len(documents)} scored documents")

        # Run TRL inference
        result = inferencer.estimate_trl(subsystem_name, documents)

        # Save individual result
        output_path = f"data/trl/{key}_trl.json"
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

        # Print result
        print(f"   ✅ TRL Range:      {result['trl_range']}")
        print(f"   ✅ Confidence:     {result['confidence']}")
        print(f"   ✅ Summary:        {result['summary'][:100]}...")
        print(f"   ✅ Limiting factor:{result['limiting_factor'][:80]}")
        print(f"   💾 Saved to:       {output_path}")

        all_trl_results[key] = result

    # Save combined report
    report_path = "data/trl/MARVEL_TRL_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(all_trl_results, f, indent=2)

    # Print final summary table
    print("\n" + "="*60)
    print("MARVEL TRL ASSESSMENT SUMMARY")
    print("="*60)
    print(f"{'Subsystem':<45} {'TRL':>6}  {'Confidence':>10}")
    print("-"*60)

    for key, result in all_trl_results.items():
        name = MARVEL_SUBSYSTEMS[key]["name"][:44]
        trl = result.get("trl_range", "N/A")
        conf = result.get("confidence", "N/A")
        print(f"{name:<45} {trl:>6}  {conf:>10}")

    print(f"\n💾 Full report saved to: {report_path}")
    print("\nNext step: Run run_dashboard.py to visualize results!")


if __name__ == "__main__":
    run_inference()