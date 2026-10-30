"""BPMN 2.0 files of the final model for import into SAP Signavio Process Manager.

Writes results/signavio/:
- bpic17_final_probabilities.bpmn: final control flow (PM4Py BPMN with its own
  diagram layout); XOR gateways named D01../M01.., every outgoing XOR flow named
  with its branch probability and aligned count (decision mining step 1).
- bpic17_final_rules.bpmn: the decision model of render_decisions.py (learned
  conditions as conditionExpression, rule blocks as text annotations).
Both files are checked: every flow node has a shape, every flow an edge with
>= 2 waypoints, unique ids, and the control-flow language equals the final PNML.
"""
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
from scripts.mine_decisions import MODEL
from src.decision_mining import NS, BPMN
from src.replay_coverage import ExactReplay

OUT = ROOT / "results/signavio"
MINED = ROOT / "results/decision_mining"
NODES = ("task", "startEvent", "endEvent", "exclusiveGateway", "parallelGateway")


def check(path, reference):
    import pm4py
    root = ET.parse(path).getroot()
    ids = [e.attrib["id"] for e in root.iter() if "id" in e.attrib]
    process = root.find("b:process", NS)
    nodes = {e.attrib["id"] for e in process if e.tag.split("}")[-1] in NODES}
    flows = {e.attrib["id"] for e in process.findall("b:sequenceFlow", NS)}
    shapes = {e.attrib["bpmnElement"] for e in root.iter(f"{{{NS['di']}}}BPMNShape")}
    edges = {e.attrib["bpmnElement"]: len(e.findall("edge:waypoint", NS)) for e in root.iter(f"{{{NS['di']}}}BPMNEdge")}
    problems = {"duplicate_ids": len(ids) - len(set(ids)), "nodes_without_shape": sorted(nodes - shapes),
                "flows_without_edge": sorted(flows - set(edges)), "edges_below_two_waypoints": sorted(k for k, n in edges.items() if n < 2)}
    equivalence = reference.language_equivalent(ExactReplay(*pm4py.convert_to_petri_net(pm4py.read_bpmn(str(path)))))
    ok = not any(problems.values()) and equivalence["equivalent"]
    return {"file": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "tasks": sum(1 for e in process if e.tag.endswith("}task")),
            "sequence_flows": len(flows), "diagram": problems, "language_equivalent_to_final_pnml": equivalence["equivalent"], "ok": ok}


def main():
    import pm4py
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads((MINED / "decision_mining.json").read_text(encoding="utf-8"))
    if data["identity"]["bpmn_sha256"] != sha(MODEL / "final_model.bpmn"):
        raise ValueError("Decision mining was run on a different final BPMN")
    for prefix, uri in (("bpmn", BPMN), ("bpmndi", NS["di"]), ("omgdc", NS["dc"]), ("omgdi", NS["edge"]),
                        ("xsi", "http://www.w3.org/2001/XMLSchema-instance"), ("xsd", "http://www.w3.org/2001/XMLSchema")):
        ET.register_namespace(prefix, uri)
    tree = ET.parse(MODEL / "final_model.bpmn")
    process = tree.getroot().find("b:process", NS)
    process.set("name", "BPIC-17 loan application (final model, branch probabilities)")
    nodes = {e.attrib.get("id"): e for e in process}
    for g in data["gateways"]:
        nodes[g["bpmn_id"]].set("name", g["id"])
        if g["kind"] != "split":
            continue
        total = sum(g["branch_counts"].values())
        for fid in g["outgoing"]:
            n = g["branch_counts"].get(fid, 0)
            nodes[fid].set("name", f"{g['branches'][fid]}: {100 * n / total:.1f}% (n={n:,})")
    probabilities = OUT / "bpic17_final_probabilities.bpmn"
    tree.write(probabilities, encoding="utf-8", xml_declaration=True)
    rules = OUT / "bpic17_final_rules.bpmn"
    shutil.copyfile(MINED / "decision_model.bpmn", rules)
    reference = ExactReplay(*pm4py.read_pnml(str(MODEL / "final_model.pnml")))
    report = {"source_bpmn": (MODEL / "final_model.bpmn").relative_to(ROOT).as_posix(),
              "decision_mining_sha256": sha(MINED / "decision_mining.json"),
              "files": [check(probabilities, reference), check(rules, reference)],
              "implementation_sha256": sha(Path(__file__))}
    write_json(OUT / "manifest.json", report)
    if not all(f["ok"] for f in report["files"]):
        raise ValueError(f"Signavio export check failed: {report['files']}")
    print(json.dumps(report["files"], indent=1), flush=True)


if __name__ == "__main__":
    main()
