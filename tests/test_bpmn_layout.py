"""Block-structured BPMN layout: positive coordinates, orthogonal flows, no overlaps, rows, legend."""
import unittest
import xml.etree.ElementTree as ET

from src.bpmn_layout import BPMN, DC, DI, OMGDI, BlockLayout, apply_layout

# start -> A -> XOR(B | skip) -> loop(C, empty redo) -> end; one free text annotation as legend
MODEL = f"""<definitions xmlns="{BPMN}"><process id="p">
<startEvent id="s"/><task id="A" name="A"/><exclusiveGateway id="x1"/><task id="B" name="B"/>
<exclusiveGateway id="m1"/><exclusiveGateway id="j"/><task id="C" name="C"/><exclusiveGateway id="x2"/>
<endEvent id="e"/>
<sequenceFlow id="f1" sourceRef="s" targetRef="A"/><sequenceFlow id="f2" sourceRef="A" targetRef="x1"/>
<sequenceFlow id="f3" sourceRef="x1" targetRef="B" name="A"/><sequenceFlow id="f4" sourceRef="x1" targetRef="m1" name="B"/>
<sequenceFlow id="f5" sourceRef="B" targetRef="m1"/><sequenceFlow id="f6" sourceRef="m1" targetRef="j"/>
<sequenceFlow id="f7" sourceRef="j" targetRef="C"/><sequenceFlow id="f8" sourceRef="C" targetRef="x2"/>
<sequenceFlow id="f9" sourceRef="x2" targetRef="j" name="D"/><sequenceFlow id="f10" sourceRef="x2" targetRef="e" name="C"/>
<textAnnotation id="n"><text>Legend\nA: first rule\nB: otherwise</text></textAnnotation>
</process></definitions>"""


def diagram(row_width=1800, legend=None):
    root = ET.fromstring(MODEL)
    summary = apply_layout(root, "Test model", row_width=row_width, legend=legend)
    boxes = {s.attrib["bpmnElement"]: tuple(float(s.find(f"{{{DC}}}Bounds").attrib[k]) for k in ("x", "y", "width", "height"))
             for s in root.iter(f"{{{DI}}}BPMNShape")}
    routes = {e.attrib["bpmnElement"]: [(float(w.attrib["x"]), float(w.attrib["y"])) for w in e.findall(f"{{{OMGDI}}}waypoint")]
              for e in root.iter(f"{{{DI}}}BPMNEdge")}
    return root, summary, boxes, routes


class LayoutTests(unittest.TestCase):
    def test_every_element_is_drawn_once_with_standard_sizes(self):
        root, summary, boxes, routes = diagram()
        self.assertEqual(set(boxes), {"s", "A", "x1", "B", "m1", "j", "C", "x2", "e"})
        self.assertEqual(set(routes), {f"f{i}" for i in range(1, 11)})
        self.assertEqual(boxes["A"][2:], (100, 80))
        self.assertEqual(boxes["x1"][2:], (40, 40))
        self.assertEqual(root.find(f"{{{BPMN}}}process").attrib["name"], "Test model")
        self.assertEqual(root.find(f"{{{DI}}}BPMNDiagram").attrib["name"], "Test model")
        self.assertEqual(summary["legend_boxes"], 0)

    def test_flows_are_orthogonal_and_coordinates_positive(self):
        _, _, boxes, routes = diagram(legend=["n"])
        for points in routes.values():
            self.assertGreaterEqual(len(points), 2)
            for (x1, y1), (x2, y2) in zip(points, points[1:]):
                self.assertTrue(x1 == x2 or y1 == y2)
        self.assertTrue(all(x >= 0 and y >= 0 for x, y, _, _ in boxes.values()))

    def test_shapes_do_not_overlap_and_structure_is_readable(self):
        _, _, boxes, routes = diagram(legend=["n"])
        items = list(boxes.values())
        for i, (x1, y1, w1, h1) in enumerate(items):
            for x2, y2, w2, h2 in items[i + 1:]:
                self.assertFalse(x1 < x2 + w2 and x2 < x1 + w1 and y1 < y2 + h2 and y2 < y1 + h1)
        axis = boxes["A"][1] + 40
        self.assertEqual(boxes["B"][1] + 40, axis)                       # the only filled branch stays on the main line
        self.assertGreater(max(y for _, y in routes["f4"]), axis)        # the skip branch runs below it
        self.assertGreater(max(y for _, y in routes["f9"]), axis)        # the loop goes back below its body
        self.assertLess(routes["f9"][-1][0], routes["f9"][0][0])         # ... from right to left

    def test_legend_sits_below_the_whole_diagram(self):
        _, summary, boxes, routes = diagram(legend=["n"])
        lowest = max(max(y + h for k, (_, y, _, h) in boxes.items() if k != "n"),
                     max(y for points in routes.values() for _, y in points))
        self.assertGreater(boxes["n"][1], lowest)
        self.assertEqual((summary["legend_boxes"], summary["legend_columns"]), (1, 1))
        self.assertGreaterEqual(summary["height"], boxes["n"][1] + boxes["n"][3])

    def test_decisions_are_listed_in_reading_order_with_the_main_flow_first(self):
        process = ET.fromstring(MODEL).find(f"{{{BPMN}}}process")
        self.assertEqual(BlockLayout(process).decisions(), [("x1", ["f3", "f4"]), ("x2", ["f10", "f9"])])

    def test_main_line_wraps_into_rows(self):
        _, wide, _, _ = diagram()
        _, narrow, boxes, routes = diagram(row_width=400)
        self.assertEqual(wide["rows"], 1)
        self.assertGreater(narrow["rows"], 1)
        self.assertLess(narrow["width"], wide["width"])
        self.assertGreater(boxes["e"][1], boxes["s"][1])
        self.assertTrue(any(len(points) == 6 for points in routes.values()))   # connector between two rows

    def test_unsupported_structure_is_rejected(self):
        root = ET.fromstring(MODEL.replace('<sequenceFlow id="f9" sourceRef="x2" targetRef="j" name="D"/>',
                                           '<task id="R" name="R"/><sequenceFlow id="f9" sourceRef="x2" targetRef="R"/>'
                                           '<sequenceFlow id="f11" sourceRef="R" targetRef="j"/>'))
        with self.assertRaises(ValueError):
            apply_layout(root, "Loop with a redo task")


if __name__ == "__main__":
    unittest.main()
