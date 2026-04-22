# run_trl_inference.py
# Runs TRL inference on all 6 scored subsystem files
# Input:  data/scored/{subsystem}_scored.json
# Output: data/trl/{subsystem}_trl.json
# Final:  data/trl/MARVEL_TRL_REPORT.json
#
# Fail-safe: if Ollama returns an error (missing model, connection, etc.), we do NOT
# overwrite existing valid TRL JSON for that subsystem; we keep the previous file and
# optionally log the failed response under data/trl/failed_runs/.

import json
import os
from datetime import datetime, timezone

from config.subsystems import MARVEL_SUBSYSTEMS
from src.tools.trl_inferencer import TRLInferencer, _ollama_model, trl_result_is_valid


def _load_json(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _resolve_result(key: str, new_result: dict, failed_dir: str) -> tuple[dict, str]:
    """
    Return (result_to_use, status) where status is 'new_ok', 'kept_file', 'kept_report', or 'wrote_error'.
    """
    if trl_result_is_valid(new_result):
        return new_result, "new_ok"

    # Snapshot failed LLM output for debugging
    os.makedirs(failed_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fail_path = os.path.join(failed_dir, f"{key}_{ts}.json")
    try:
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(new_result, f, indent=2)
    except OSError:
        fail_path = "(could not write)"

    per_path = f"data/trl/{key}_trl.json"
    prev_file = _load_json(per_path)
    if prev_file and trl_result_is_valid(prev_file):
        print(
            f"   ⚠️  Ollama output invalid — keeping existing {per_path} "
            f"(failure log: {fail_path})"
        )
        return prev_file, "kept_file"

    report_path = "data/trl/MARVEL_TRL_REPORT.json"
    prev_report = _load_json(report_path)
    if prev_report and isinstance(prev_report.get(key), dict):
        ent = prev_report[key]
        if trl_result_is_valid(ent):
            print(
                f"   ⚠️  Ollama output invalid — restored {key} from {report_path} "
                f"(failure log: {fail_path})"
            )
            return ent, "kept_report"

    print(
        f"   ⚠️  Ollama output invalid and no prior TRL — writing error to {per_path} "
        f"(failure log: {fail_path})"
    )
    return new_result, "wrote_error"


def run_inference():
    inferencer = TRLInferencer()

    os.makedirs("data/trl", exist_ok=True)
    failed_dir = "data/trl/failed_runs"

    print("MARVEL TRL Assessment - TRL Inference Engine")
    print(f"Using: Ollama model `{_ollama_model()}` (local)")
    print("=" * 60)

    all_trl_results = {}

    for key in MARVEL_SUBSYSTEMS.keys():
        scored_path = f"data/scored/{key}_scored.json"

        if not os.path.exists(scored_path):
            print(f"⚠️  Skipping {key} — no scored file found")
            continue

        # Load scored documents
        with open(scored_path, encoding="utf-8") as f:
            data = json.load(f)

        subsystem_name = data["name"]
        documents = data.get("scored_documents", [])

        print(f"\n🔬 Inferring TRL: {subsystem_name}")
        print(f"   Using top {TRLInferencer.TOP_N_DOCS} of {len(documents)} scored documents")

        new_result = inferencer.estimate_trl(subsystem_name, documents)
        result, status = _resolve_result(key, new_result, failed_dir)

        output_path = f"data/trl/{key}_trl.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        lim = (result.get("limiting_factor") or "")[:80]
        summ = (result.get("summary") or "")[:100]
        print(f"   ✅ TRL Range:      {result.get('trl_range')}")
        print(f"   ✅ Confidence:     {result.get('confidence')}")
        print(f"   ✅ Summary:        {summ}...")
        print(f"   ✅ Limiting factor:{lim}")
        print(f"   💾 Using:          {output_path} ({status})")

        all_trl_results[key] = result

    # Save combined report
    report_path = "data/trl/MARVEL_TRL_REPORT.json"
    with open(report_path, "w", encoding="utf-8") as f:
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
    print("\nNext step: Open MARVEL_TRL_Dashboard.html in a browser to visualize results.")


if __name__ == "__main__":
    run_inference()