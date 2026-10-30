"""Step 1 of decision mining: branch probabilities at every XOR split, no rules.

Reads the aligned branch counts of results/decision_mining/decision_mining.json
(one optimal alignment per variant, all 31,509 cases) and the final BPMN. Writes
branch_probabilities.{pdf,svg,png,csv,tex}: every outgoing XOR flow labelled
'p% (n)'. Loop splits are counted per visit, so their probabilities are per
iteration (redo vs. exit), not per case.
"""
import argparse
import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.mine_decisions import MODEL
from src.decision_mining import NS

OUT = ROOT / "results/decision_mining"


def main():
    import graphviz
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=MODEL)
    args = parser.parse_args()
    data = json.loads((OUT / "decision_mining.json").read_text(encoding="utf-8"))
    process = ET.parse(args.model_dir / "final_model.bpmn").getroot().find("b:process", NS)
    nodes = {e.attrib.get("id"): e for e in process}
    flows = {e.attrib["id"]: e for e in process.findall("b:sequenceFlow", NS)}
    gateways = {g["bpmn_id"]: g for g in data["gateways"]}
    tag = lambda nid: nodes[nid].tag.split("}")[-1]

    def describe(nid):
        kind = tag(nid)
        if kind == "task":
            return nodes[nid].attrib.get("name", "")
        if nid in gateways:
            return gateways[nid]["id"]
        return {"endEvent": "end", "parallelGateway": "AND"}.get(kind, kind)

    rows, labels = [], {}
    for g in data["gateways"]:
        if g["kind"] != "split":
            continue
        total = sum(g["branch_counts"].values())
        for fid in g["outgoing"]:
            n = g["branch_counts"].get(fid, 0)
            rows.append({"split": g["id"], "branch": g["branches"][fid], "target": describe(flows[fid].attrib["targetRef"]),
                         "visits": total, "n": n, "probability": n / total})
            labels[fid] = f"{g['branches'][fid]}: {100 * n / total:.1f}%\n({n:,})"
    dot = graphviz.Digraph("branch_probabilities", graph_attr={"rankdir": "TB", "bgcolor": "white", "nodesep": ".35",
                                                               "ranksep": ".45", "splines": "polyline", "margin": "0"},
                           node_attr={"fontname": "Arial", "fontsize": "13"}, edge_attr={"fontname": "Arial", "fontsize": "10"})
    for nid in nodes:
        kind = tag(nid) if nid in nodes else None
        if kind == "task":
            dot.node(nid, nodes[nid].attrib.get("name", ""), shape="box", style="rounded,filled", fillcolor="#eef4f8")
        elif kind in ("startEvent", "endEvent"):
            dot.node(nid, "", shape="doublecircle" if kind == "endEvent" else "circle", width=".25")
        elif kind == "parallelGateway":
            dot.node(nid, "+", shape="diamond", width=".5", height=".5")
        elif kind == "exclusiveGateway":
            dot.node(nid, gateways[nid]["id"] + "\nX", shape="diamond", width=".7", height=".7",
                     style="filled", fillcolor="#fde9c8" if gateways[nid]["kind"] == "split" else "white")
    # Loop back edges (DFS from the start event) must not constrain ranks, else the
    # layout folds the main flow around the loops.
    successors = {}
    for fid, flow in flows.items():
        successors.setdefault(flow.attrib["sourceRef"], []).append(fid)
    back, state = set(), {}
    stack = [(nid, iter(successors.get(nid, ()))) for nid in nodes if tag(nid) == "startEvent"]
    for nid, _ in stack:
        state[nid] = "open"
    while stack:
        nid, pending = stack[-1]
        fid = next(pending, None)
        if fid is None:
            state[nid] = "done"
            stack.pop()
            continue
        target = flows[fid].attrib["targetRef"]
        if state.get(target) == "open":
            back.add(fid)
        elif target not in state:
            state[target] = "open"
            stack.append((target, iter(successors.get(target, ()))))
    for fid, flow in flows.items():
        options = {"constraint": "false"} if fid in back else {}
        if fid in labels:
            share = float(labels[fid].split(": ")[1].split("%")[0]) / 100
            dot.edge(flow.attrib["sourceRef"], flow.attrib["targetRef"], labels[fid], color="#b4560f",
                     fontcolor="#7a3a0a", penwidth=f"{0.6 + 3.4 * share:.2f}", **options)
        else:
            dot.edge(flow.attrib["sourceRef"], flow.attrib["targetRef"], **options)
    for fmt in ("pdf", "svg", "png"):
        dot.render(str(OUT / "branch_probabilities"), format=fmt, cleanup=True)
    with (OUT / "branch_probabilities.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows({**r, "probability": round(r["probability"], 6)} for r in rows)
    tex = [r"\begin{tabular}{llp{0.42\textwidth}rrr}", r"\hline",
           r"Split & Branch & Next element & Visits & $n$ & $p$ \\", r"\hline"]
    for r in rows:
        target = r["target"].replace("_", r"\_").replace("&", r"\&")
        tex.append(f"{r['split']} & {r['branch']} & {target} & {r['visits']:,} & {r['n']:,} & {r['probability']:.3f} \\\\")
    tex += [r"\hline", r"\end{tabular}"]
    (OUT / "branch_probabilities.tex").write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(rows)} XOR branches at {len({r['split'] for r in rows})} splits", flush=True)


if __name__ == "__main__":
    main()
