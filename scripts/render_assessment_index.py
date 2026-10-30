"""Write results/assessment/README.md: format note and one table row per <name>.json record.

Values are copied from each record's headline/soundness keys; nothing is recomputed.
Rows record the model_assessment.py hash they were produced with, because the
shared module may change between runs.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "results/assessment"
FORMAT = """# Model assessment records

Each `<name>.json` is written by `scripts/assess_model.py` for one saved Petri net
(PNML, or PTML converted to PNML), always evaluated on the same full completion
projection `tmp/evaluation/projected_sequences.json` (31,509 cases, 475,306 events,
5,623 variants, 24 activities). Provenance keys hold the model path and SHA-256 of
the model, input cache, raw log and every implementation file plus the PM4Py
version; `headline` is a flat row; `soundness` holds the PM4Py WF-net check, the
complete-state-space classical verdict or an unboundedness witness, easy/relaxed
soundness and safeness from a bounded exploration, and a PM4Py Woflan cross-check;
`simplicity` and `token` hold PM4Py arc degree, own size, Extended Cardoso and
ECyM, and PM4Py token fitness, ETC precision and generalization. Bounded nets with
a reachable final marking additionally get `exact_replay`, `alignment_fitness`
(exact finite-state alignments, PM4Py formula, A* cross-check) and
`align_et_precision`; otherwise `finite_state_metrics` states why they are missing.
`<name>_diagnostics/` (optional, `--diagnostics`) holds conformance CSVs.
Regenerate this file with `.\\.venv\\Scripts\\python.exe scripts/render_assessment_index.py`.

`n/c` = not computed (finite-state metric on an unbounded net, or no verdict).
"""
COLUMNS = ("Record", "Model file", "State space", "Sound", "Woflan", "Exact replay %", "Token fitness",
           "Alignment fitness", "Token precision", "Align-ET", "Generalization", "Arc degree", "Nodes",
           "Ext. Cardoso", "ECyM", "model_assessment.py")


def number(value, digits=4):
    if value is None:
        return "n/c"
    return f"{value:.{digits}f}" if isinstance(value, float) else f"{value:,}"


def row(record):
    h, s = record["headline"], record["soundness"]
    classical = s["classical"]
    space = {"ok": f"bounded, {classical.get('states_seen', 0):,} states",
             "unbounded": "unbounded (witness)"}.get(classical["status"], classical["status"])
    woflan = s.get("woflan", {})
    woflan = ({True: "sound", False: "unsound"}[woflan["sound"]] if woflan.get("status") == "ok"
              else woflan.get("status", "not run"))
    token_invalid = record.get("token", {}).get("valid") is False
    token = (lambda key: "invalid" if token_invalid else number(h.get(key)))
    sound = {True: "yes", False: "no", None: "n/c"}[h["sound"]]
    if h["sound"] is False and s.get("unsound_reason"):
        sound += f" ({s['unsound_reason']})"
    return (f"`{record['name']}`", f"`{record['model']}`", space, sound, woflan, number(h["exact_replay_pct"], 2),
            token("token_fitness"), number(h["alignment_fitness"]), token("token_precision"),
            number(h["align_et_precision"]), token("generalization"), number(h["arc_degree_simplicity"]),
            number(h["nodes"]), number(h["extended_cardoso"]), number(h["extended_cyclomatic"]),
            f"`{record['implementation_sha256']['src/model_assessment.py'][:8]}`")


def main():
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(FOLDER.glob("*.json"))]
    current = hashlib.sha256((ROOT / "src/model_assessment.py").read_bytes()).hexdigest()[:8]
    lines = [FORMAT, f"## Assessed models ({len(records)})", "",
             "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(row(r)) + " |" for r in sorted(records, key=lambda r: r["name"])]
    older = sorted(r["name"] for r in records if r["implementation_sha256"]["src/model_assessment.py"][:8] != current)
    lines += ["", f"Current `src/model_assessment.py`: `{current}`."
              + (f" Produced with an earlier version: {', '.join(f'`{n}`' for n in older)}." if older else "")]
    diagnostics = sorted(p.name for p in FOLDER.glob("*_diagnostics") if p.is_dir())
    if diagnostics:
        lines += [f"Diagnostics folders: {', '.join(f'`{d}/`' for d in diagnostics)}."]
    (FOLDER / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(records)} records", flush=True)


if __name__ == "__main__":
    main()
