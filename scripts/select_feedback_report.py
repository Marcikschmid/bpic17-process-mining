"""Explicitly select the factual assets of the tutor-feedback round for report/.

Copies tables and figures (no prose) and records source and SHA-256 of every copy
in docs/feedback_report_manifest.json. Run after the producing scripts, then
report/build.ps1.
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPIES = {
    "results/comparison/model_comparison.tex": "tables/model_comparison.tex",
    "results/comparison/soundness_summary.tex": "tables/soundness_summary.tex",
    "results/comparison/holdout_check.tex": "tables/holdout_check.tex",
    "results/manual_edits/conformance_to_edits.tex": "tables/conformance_to_edits.tex",
    "results/manual_edits/single_edits.tex": "tables/single_edits.tex",
    "results/manual_edits/guard_stage.tex": "tables/guard_stage.tex",
    "results/final/block_structure.tex": "tables/block_structure.tex",
    "results/comparison/final_quality.tex": "tables/final_quality.tex",
    "results/comparison/metric_methods.tex": "tables/metric_methods.tex",
    "results/decision_mining/feature_stages.tex": "tables/feature_stages.tex",
    "results/decision_mining/branch_probabilities.tex": "tables/branch_probabilities.tex",
    "results/final/final_bpmn.pdf": "figures/final_edited_bpmn.pdf",
    "results/decision_mining/branch_probabilities.pdf": "figures/branch_probabilities.pdf",
    "results/alpha/alpha_miner.pdf": "figures/alpha_miner.pdf",
    "results/heuristics/native/heuristics_net.pdf": "figures/heuristics_net.pdf",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = {}
    for source, target in COPIES.items():
        source_path, target_path = ROOT / source, ROOT / "report" / target
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target_path)
        assert sha(source_path) == sha(target_path), target
        manifest[target] = {"source": source, "sha256": sha(target_path)}
    path = ROOT / "docs/feedback_report_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Selected {len(manifest)} factual report assets", flush=True)


if __name__ == "__main__":
    main()
