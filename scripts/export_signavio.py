"""BPMN 2.0 files of the final model for import into SAP Signavio Process Manager.

Writes three variants of the same control flow to results/signavio/; only the
task names and the labels named below are visible (no gateway or event names):
- bpic17_final_plain.bpmn: no labels at the decisions.
- bpic17_final_probabilities.bpmn: every outgoing XOR flow labelled with its
  branch probability in percent (decision mining step 1).
- bpic17_final_rules.bpmn: every outgoing XOR flow labelled with one letter; the
  learned conditions follow as a legend below the diagram (one box per decision).
  The flows keep their full conditionExpression from render_decisions.py.
All files get their own process/diagram name and the block-structured
left-to-right layout of src/bpmn_layout.py (standard element sizes, orthogonal
flows); the PM4Py/Graphviz layouts of the sources are not suited for Signavio.
All files are checked: every flow node and annotation has a shape, every flow
an orthogonal edge with >= 2 waypoints, unique ids, no overlapping shapes, no
negative coordinates, and the control-flow language equals the final PNML.
"""
import json
import re
import string
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
from scripts.mine_decisions import MODEL
from src.bpmn_layout import BlockLayout, apply_layout
from src.decision_mining import NS, BPMN
from src.replay_coverage import ExactReplay

OUT = ROOT / "results/signavio"
MINED = ROOT / "results/decision_mining"
NODES = ("task", "startEvent", "endEvent", "exclusiveGateway", "parallelGateway")
UNNAMED = ("startEvent", "endEvent", "exclusiveGateway", "parallelGateway", "sequenceFlow")
# The distinguishing word comes first: the Signavio explorer truncates long names.
NAMES = {"plain": "Control flow - BPIC-17 final model",
         "probabilities": "Branch probabilities - BPIC-17 final model",
         "rules": "Decision rules - BPIC-17 final model"}
FILES = {"plain": "bpic17_final_plain.bpmn", "probabilities": "bpic17_final_probabilities.bpmn",
         "rules": "bpic17_final_rules.bpmn"}
ROW_WIDTH = 1800      # maximum width of one row of the wrapped main line (four rows)
LEGEND_CHARS = 58     # characters per legend line: three legend columns fit below the diagram
LEGEND_HEAD = "\n".join([
    "Legend: learned conditions at the XOR splits",
    "A letter marks one outgoing flow of a split.",
    "Lines with the same letter are alternatives (OR).",
    "otherwise = all remaining cases of that split.",
    "last. = last synchronized offer value",
    "hist. = case history before this decision",
    "Learned associations; not bank policy."])


def strip_labels(process):
    """Only task names stay visible: empty the names of gateways, events and flows."""
    for element in process:
        if element.tag.split("}")[-1] in UNNAMED:
            element.set("name", "")


def letter(index):
    alphabet = string.ascii_uppercase
    return alphabet[index] if index < 26 else alphabet[index // 26 - 1] + alphabet[index % 26]


def parse_rules(text):
    """Rule block of render_decisions.py -> (balanced test accuracy, {branch label: [conditions]})."""
    lines, rules, current = text.split("\n"), {}, None
    for line in lines[2:]:
        match = re.match(r"(B\d+): (.*)", line)
        if match:
            current = [match.group(2)]
            rules.setdefault(match.group(1), []).append(current)
        elif line.startswith("    ") and current is not None:
            current.append(line.strip())
        else:
            current = None
    return lines[1].split(": ")[1], {label: [" ".join(parts) for parts in found] for label, found in rules.items()}


def legend_block(decision, accuracy, entries):
    """One legend box: the branch with the most conditions is the complement ('otherwise') of the others."""
    rest = max(entries[::-1], key=lambda entry: (len(entry[1]), sum(len(rule) for rule in entry[1])))
    lines = [f"{decision} | balanced accuracy (test) {accuracy}"]
    for entry in [e for e in entries if e is not rest] + [rest]:
        mark, rules = entry
        if entry is rest:
            lines.append(f"{mark}: otherwise")
        elif not rules:
            lines.append(f"{mark}: never chosen by the tree")
        else:
            for rule in rules:
                lines += textwrap.wrap(f"{mark}: {rule}", width=LEGEND_CHARS, subsequent_indent="    ")
    return "\n".join(lines)


def check(path, reference, layout):
    import pm4py
    root = ET.parse(path).getroot()
    ids = [e.attrib["id"] for e in root.iter() if "id" in e.attrib]
    process = root.find("b:process", NS)
    nodes = {e.attrib["id"] for e in process if e.tag.split("}")[-1] in NODES}
    notes = {e.attrib["id"] for e in process if e.tag.endswith("}textAnnotation")}
    flows = {e.attrib["id"] for e in process.findall("b:sequenceFlow", NS)}
    flows |= {e.attrib["id"] for e in process if e.tag.endswith("}association")}
    boxes = {}
    for shape in root.iter(f"{{{NS['di']}}}BPMNShape"):
        b = shape.find("dc:Bounds", NS).attrib
        boxes[shape.attrib["bpmnElement"]] = tuple(float(b[k]) for k in ("x", "y", "width", "height"))
    routes = {e.attrib["bpmnElement"]: [(float(w.attrib["x"]), float(w.attrib["y"])) for w in e.findall("edge:waypoint", NS)]
              for e in root.iter(f"{{{NS['di']}}}BPMNEdge")}
    items = sorted(boxes.items())
    overlaps = [f"{a}/{c}" for i, (a, (x1, y1, w1, h1)) in enumerate(items) for c, (x2, y2, w2, h2) in items[i + 1:]
                if x1 < x2 + w2 and x2 < x1 + w1 and y1 < y2 + h2 and y2 < y1 + h1]
    problems = {"duplicate_ids": len(ids) - len(set(ids)), "nodes_without_shape": sorted((nodes | notes) - set(boxes)),
                "flows_without_edge": sorted(flows - set(routes)),
                "edges_below_two_waypoints": sorted(k for k, p in routes.items() if len(p) < 2),
                "non_orthogonal_edges": sorted(k for k, p in routes.items()
                                               if any(abs(a[0] - b[0]) > 0.05 and abs(a[1] - b[1]) > 0.05 for a, b in zip(p, p[1:]))),
                "overlapping_shapes": overlaps,
                "negative_coordinates": sorted(k for k, (x, y, _, _) in boxes.items() if x < 0 or y < 0)}
    equivalence = reference.language_equivalent(ExactReplay(*pm4py.convert_to_petri_net(pm4py.read_bpmn(str(path)))))
    ok = not any(problems.values()) and equivalence["equivalent"]
    labels = sorted({e.attrib["name"] for e in process.findall("b:sequenceFlow", NS) if e.attrib.get("name")})
    return {"file": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "name": process.attrib.get("name"),
            "tasks": sum(1 for e in process if e.tag.endswith("}task")), "sequence_flows": len(process.findall("b:sequenceFlow", NS)),
            "flow_labels": len(labels), "layout": layout, "diagram": problems,
            "language_equivalent_to_final_pnml": equivalence["equivalent"], "ok": ok}


def write(tree, kind):
    ET.indent(tree.getroot(), space="  ")
    path = OUT / FILES[kind]
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path


def main():
    import pm4py
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads((MINED / "decision_mining.json").read_text(encoding="utf-8"))
    if data["identity"]["bpmn_sha256"] != sha(MODEL / "final_model.bpmn"):
        raise ValueError("Decision mining was run on a different final BPMN")
    for prefix, uri in (("bpmn", BPMN), ("bpmndi", NS["di"]), ("omgdc", NS["dc"]), ("omgdi", NS["edge"]),
                        ("xsi", "http://www.w3.org/2001/XMLSchema-instance"), ("xsd", "http://www.w3.org/2001/XMLSchema")):
        ET.register_namespace(prefix, uri)
    splits = {g["bpmn_id"]: g for g in data["gateways"] if g["kind"] == "split"}
    # the most frequent branch of every XOR split stays on the main line of all diagrams
    weights = {flow: count for g in splits.values() for flow, count in g["branch_counts"].items()}
    layouts, paths = {}, {}

    tree = ET.parse(MODEL / "final_model.bpmn")
    strip_labels(tree.getroot().find("b:process", NS))
    layouts["plain"] = apply_layout(tree.getroot(), NAMES["plain"], weights, ROW_WIDTH)
    paths["plain"] = write(tree, "plain")

    tree = ET.parse(MODEL / "final_model.bpmn")
    process = tree.getroot().find("b:process", NS)
    strip_labels(process)
    flows = {e.attrib["id"]: e for e in process.findall("b:sequenceFlow", NS)}
    for g in splits.values():
        total = sum(g["branch_counts"].values())
        for flow in g["outgoing"]:
            flows[flow].set("name", f"{100 * g['branch_counts'].get(flow, 0) / total:.1f}%")
    layouts["probabilities"] = apply_layout(tree.getroot(), NAMES["probabilities"], weights, ROW_WIDTH)
    paths["probabilities"] = write(tree, "probabilities")

    tree = ET.parse(MINED / "decision_model.bpmn")
    process = tree.getroot().find("b:process", NS)
    texts = {e.attrib["id"]: e.find("b:text", NS).text for e in process if e.tag.endswith("}textAnnotation")}
    notes = {}
    for element in [e for e in process if e.tag.endswith("}association")]:
        source, target = element.attrib["sourceRef"], element.attrib["targetRef"]
        gateway, note = (source, target) if target in texts else (target, source)
        notes[gateway] = texts[note]
    for element in [e for e in process if e.tag.split("}")[-1] in ("association", "textAnnotation")]:
        process.remove(element)                     # the rule blocks move into the legend
    strip_labels(process)
    order = BlockLayout(process, weights, ROW_WIDTH).decisions()    # reading order of the decisions
    if {gateway for gateway, _ in order} != set(splits) or set(notes) != set(splits):
        raise ValueError("Decision gateways of layout, decision mining and rule blocks differ")
    flows = {e.attrib["id"]: e for e in process.findall("b:sequenceFlow", NS)}
    legend, index = [("legend_head", LEGEND_HEAD)], 0
    for gateway, outgoing in order:
        accuracy, rules = parse_rules(notes[gateway])
        entries = []
        for flow in outgoing:
            flows[flow].set("name", letter(index))
            entries.append((letter(index), rules.get(splits[gateway]["branches"][flow], [])))
            index += 1
        legend.append((f"legend_{splits[gateway]['id']}", legend_block(splits[gateway]["id"], accuracy, entries)))
    for ident, text in legend:
        annotation = ET.SubElement(process, f"{{{BPMN}}}textAnnotation", {"id": ident})
        ET.SubElement(annotation, f"{{{BPMN}}}text").text = text
    layouts["rules"] = apply_layout(tree.getroot(), NAMES["rules"], weights, ROW_WIDTH, legend=[ident for ident, _ in legend])
    paths["rules"] = write(tree, "rules")

    reference = ExactReplay(*pm4py.read_pnml(str(MODEL / "final_model.pnml")))
    report = {"source_bpmn": (MODEL / "final_model.bpmn").relative_to(ROOT).as_posix(),
              "decision_mining_sha256": sha(MINED / "decision_mining.json"),
              "files": [check(paths[kind], reference, layouts[kind]) for kind in FILES],
              "implementation_sha256": sha(Path(__file__)), "layout_sha256": sha(ROOT / "src/bpmn_layout.py")}
    write_json(OUT / "manifest.json", report)
    if not all(f["ok"] for f in report["files"]):
        raise ValueError(f"Signavio export check failed: {report['files']}")
    print(json.dumps(report["files"], indent=1), flush=True)


if __name__ == "__main__":
    main()
