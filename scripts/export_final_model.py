"""Promote the selected manually edited tree to the final model (results/final/).

Default input: results/abstraction/manual_edits/selected/model.ptml (selected by
scripts/manual_edits_abstracted.py on the abstracted log). The final model before
event abstraction (results/before_abstraction/final/) came from
`--source results/manual_edits/selected/model.ptml --cache tmp/evaluation/projected_sequences.json
--out results/before_abstraction/final`.
Exports PTML, PNML and BPMN 2.0, verifies complete language equivalence of the
BPMN round trip with the tree's Petri net, counts the block structure
(process-tree operators and the BPMN gateways they become) and renders the BPMN.
The manifest records the sequence cache the model is evaluated on; decision
mining reads it to apply the same event abstraction to the raw events.
Quality metrics come from scripts/assess_model.py (results/assessment/final_model.json).
"""
import argparse
import json
import sys
from collections import Counter
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
import pm4py
from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.process_tree.obj import Operator
from pm4py.visualization.bpmn import visualizer
from src.model_assessment import ABSTRACTED_CACHE
from src.replay_coverage import ExactReplay

SOURCE = ROOT / "results/abstraction/manual_edits/selected/model.ptml"
OUT = ROOT / "results/final"
NAMES = {Operator.SEQUENCE: "sequence ->", Operator.XOR: "exclusive choice X", Operator.PARALLEL: "parallel +",
         Operator.LOOP: "loop *"}


def operators(tree, found=None):
    found = Counter() if found is None else found
    if tree.operator is None:
        found["tau leaf" if tree.label is None else "activity leaf"] += 1
    else:
        found[NAMES[tree.operator]] += 1
        for child in tree.children:
            operators(child, found)
    return found


def render(bpmn, path, rankdir):
    graph = visualizer.apply(bpmn, parameters={"rankdir": rankdir, "font_size": "13", "bgcolor": "white"})
    graph.attr("graph", nodesep=".15", ranksep=".25", pad=".15")
    for node in bpmn.get_nodes():
        if isinstance(node, BPMN.Task):
            graph.node(str(id(node)), style="rounded", margin=".07,.04")
    for extension in ("pdf", "svg", "png"):
        path.with_suffix(f".{extension}").write_bytes(graph.pipe(format=extension))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--cache", type=Path, default=ABSTRACTED_CACHE, help="Sequence cache the model is evaluated on.")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    source, cache, out = (p if p.is_absolute() else ROOT / p for p in (args.source, args.cache, args.out))
    cache_data = json.loads(cache.read_text(encoding="utf-8"))
    export(source, out, {"evaluation_cache": cache.relative_to(ROOT).as_posix(), "evaluation_cache_sha256": sha(cache),
                         "event_abstraction": "abstraction" in cache_data})


def export(SOURCE, OUT, evaluation):
    OUT.mkdir(parents=True, exist_ok=True)
    tree = pm4py.read_ptml(str(SOURCE))
    pm4py.write_ptml(tree, str(OUT / "final_model.ptml"))
    net, initial, final = pm4py.convert_to_petri_net(tree)
    pm4py.write_pnml(net, initial, final, str(OUT / "final_model.pnml"))
    net, initial, final = pm4py.read_pnml(str(OUT / "final_model.pnml"))
    machine = ExactReplay(net, initial, final)
    if not machine.sound:
        raise ValueError("Final net is not sound")
    bpmn = pm4py.convert_to_bpmn(tree)
    pm4py.write_bpmn(bpmn, str(OUT / "final_model.bpmn"), auto_layout=True)
    imported = pm4py.read_bpmn(str(OUT / "final_model.bpmn"))
    roundtrip = pm4py.convert_to_petri_net(imported)
    equivalence = machine.language_equivalent(ExactReplay(*roundtrip))
    if not equivalence["equivalent"]:
        raise ValueError(f"BPMN changed the model language: {equivalence}")
    pm4py.write_pnml(*roundtrip, str(OUT / "bpmn_roundtrip.pnml"))
    nodes = imported.get_nodes()
    gateways = Counter()
    for node in nodes:
        if isinstance(node, (BPMN.ExclusiveGateway, BPMN.ParallelGateway)):
            kind = "XOR" if isinstance(node, BPMN.ExclusiveGateway) else "AND"
            outgoing = sum(flow.get_source() is node for flow in imported.get_flows())
            gateways[f"{kind} {'split' if outgoing > 1 else 'merge'}"] += 1
    tasks = Counter(n.get_name() for n in nodes if isinstance(n, BPMN.Task))
    found = operators(tree)
    structure = {"tree": str(tree), "tree_operators": dict(sorted(found.items())),
                 "bpmn_tasks": sum(tasks.values()), "bpmn_distinct_task_labels": len(tasks),
                 "duplicated_task_labels": sorted(t for t, n in tasks.items() if n > 1),
                 "bpmn_gateways": dict(sorted(gateways.items())),
                 "mapping": {"sequence ->": "sequence flows, no gateway",
                             "exclusive choice X": "XOR split + XOR merge pair",
                             "loop *": "XOR merge (loop entry) + XOR split (exit or redo) pair",
                             "parallel +": "AND split + AND join pair",
                             "tau leaf": "no task; skip or redo path between gateways"},
                 "expected_xor_pairs": found["exclusive choice X"] + found["loop *"],
                 "expected_and_pairs": found["parallel +"]}
    write_json(OUT / "block_structure.json", structure)
    rows = ["\\begin{tabular}{llr}", "\\hline", "Process-tree block & BPMN construct & Count \\\\", "\\hline"]
    for name in ("sequence ->", "exclusive choice X", "loop *", "parallel +", "activity leaf", "tau leaf"):
        label = name.replace("->", "$\\rightarrow$").replace("*", "$\\circlearrowleft$").replace("+", "$\\wedge$").replace(" X", " $\\times$")
        rows.append(f"{label} & {structure['mapping'].get(name, 'task')} & {found[name]} \\\\")
    rows += ["\\hline", f"\\multicolumn{{2}}{{l}}{{BPMN: tasks / XOR split+merge / AND split+join}} & "
             f"{structure['bpmn_tasks']} / {gateways['XOR split']}+{gateways['XOR merge']} / {gateways['AND split']}+{gateways['AND merge']} \\\\",
             "\\hline", "\\end{tabular}"]
    (OUT / "block_structure.tex").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    render(imported, OUT / "final_bpmn", "TB")
    render(imported, OUT / "final_bpmn_lr", "LR")
    write_json(OUT / "manifest.json", {"source": SOURCE.relative_to(ROOT).as_posix(), "source_sha256": sha(SOURCE),
        "selection": (SOURCE.parent.parent / "screen.json").relative_to(ROOT).as_posix(), **evaluation,
        "pm4py": version("pm4py"),
        "states": machine.state_count, "sound": machine.sound, "bpmn_language_equivalence": equivalence,
        "artifacts": {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "manifest.json"},
        "implementation_sha256": {p: sha(ROOT / p) for p in ("scripts/export_final_model.py", "src/replay_coverage.py")}})
    print(json.dumps(structure, indent=2), flush=True)


if __name__ == "__main__":
    main()
