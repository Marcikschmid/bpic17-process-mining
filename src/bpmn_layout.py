"""Block-structured left-to-right BPMN diagram layout for modelling tools.

The PM4Py and Graphviz layouts of the exported models use tool-specific node
sizes, curved flows and partly negative coordinates; SAP Signavio shows them
distorted. This module rebuilds the BPMN DI section of a block-structured model
(process-tree origin) from its control flow alone:

- standard element sizes (task 100x80, gateway 40x40, events 30/28);
- main line from left to right, wrapped into balanced rows; at every XOR/AND
  split the most frequent non-empty branch stays on the main line, the other
  branches are stacked below it, skip branches run below as a bypass;
- the empty redo flow of a loop runs back below the loop body;
- orthogonal flows only, attached at the centre of an element side;
- optional legend: free text annotations arranged in columns below the diagram.

Only loops with an empty redo path are supported (all loops of the final model);
other structures raise ValueError instead of producing a wrong picture.
"""
import xml.etree.ElementTree as ET
from itertools import combinations

import networkx as nx

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
DI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
OMGDI = "http://www.omg.org/spec/DD/20100524/DI"
SIZE = {"task": (100, 80), "startEvent": (30, 30), "endEvent": (28, 28),
        "exclusiveGateway": (40, 40), "parallelGateway": (40, 40)}
GATE = 40          # gateway width and height
GAP = 60           # horizontal distance between consecutive elements
BRANCH_GAP = 40    # vertical distance between stacked branches
LANE = 55          # vertical distance of a bypass or loop-back flow (room for a rotated flow label)
ROW_GAP = 90       # vertical distance between two rows of the wrapped main line
TURN = 40          # horizontal overshoot of the connector between two rows
MARGIN = 60        # diagram origin
LEGEND_GAP = 30    # distance between two legend boxes
LEGEND_TOP = 50    # distance between the diagram and its legend


def _tag(element):
    return element.tag.split("}")[-1]


class Leaf:
    def __init__(self, node):
        self.node = node


class Seq:
    def __init__(self, items):
        self.items = items


class Split:
    def __init__(self, split, merge, branches):
        self.split, self.merge, self.branches = split, merge, branches


class Loop:
    def __init__(self, join, split, body, leave):
        self.join, self.split, self.body, self.leave = join, split, body, leave


def annotation_size(text):
    """Box that holds pre-wrapped annotation text in a 12 px modelling font."""
    lines = text.split("\n")
    return max(220, round(6.6 * max(len(line) for line in lines) + 24)), round(15.5 * len(lines) + 20)


class BlockLayout:
    def __init__(self, process, weights=None, row_width=1800):
        self.weights = weights or {}
        self.kind, self.out, self.inc, self.flow = {}, {}, {}, {}
        for element in process:
            if _tag(element) in SIZE:
                node = element.attrib["id"]
                self.kind[node], self.out[node], self.inc[node] = _tag(element), [], []
        label = 0
        for element in process:
            if _tag(element) != "sequenceFlow":
                continue
            flow, source, target = element.attrib["id"], element.attrib["sourceRef"], element.attrib["targetRef"]
            if source not in self.kind or target not in self.kind:
                raise ValueError(f"Flow {flow} connects an unsupported element")
            if (source, target) in self.flow:
                raise ValueError(f"Parallel flows between {source} and {target} are not supported")
            self.out[source].append((flow, target))
            self.inc[target].append((flow, source))
            self.flow[(source, target)] = flow
            if self.kind[source] == "exclusiveGateway":
                label = max(label, len(element.attrib.get("name", "")))
        self.split_gap = max(GAP, round(6.5 * label) + 30)   # room for the flow label behind a split
        starts = [n for n, k in self.kind.items() if k == "startEvent"]
        ends = [n for n, k in self.kind.items() if k == "endEvent"]
        if len(starts) != 1 or len(ends) != 1:
            raise ValueError("Exactly one start and one end event are required")
        self.back = self._back_edges(starts[0])
        forward = nx.DiGraph()
        forward.add_nodes_from(self.kind)
        forward.add_edges_from((t, s) for s in self.out for _, t in self.out[s] if (s, t) not in self.back)
        self.post = nx.immediate_dominators(forward, ends[0])
        self.placed = []
        self.tree = self._parse(starts[0], None)
        if sorted(self.placed) != sorted(self.kind):
            raise ValueError("Model is not block-structured: not every element was reached exactly once")
        self.bounds, self.edges = {}, {}
        self._measure(self.tree)
        self._place_rows(row_width)
        if set(self.edges) != set(self.flow.values()):
            raise ValueError("Not every sequence flow was routed")
        self._normalise()

    # ------------------------------------------------------------ structure
    def _back_edges(self, start):
        back, state, stack = set(), {start: 0}, [start]
        while stack:
            node = stack[-1]
            if state[node] < len(self.out[node]):
                target = self.out[node][state[node]][1]
                state[node] += 1
                if target not in state:
                    state[target] = 0
                    stack.append(target)
                elif target in stack:
                    back.add((node, target))
            else:
                stack.pop()
        return back

    def _parse(self, node, stop):
        items = []
        while node is not None and node != stop:
            outs, gateway = self.out[node], self.kind[node].endswith("Gateway")
            loop_back = [s for _, s in self.inc[node] if (s, node) in self.back]
            if gateway and loop_back:
                split = loop_back[0]
                exits = [t for _, t in self.out[split] if t != node]
                if len(loop_back) != 1 or len(outs) != 1 or len(self.out[split]) != 2 or len(exits) != 1 \
                        or self.kind[split] != "exclusiveGateway":
                    raise ValueError(f"Loop at {node}: only loops with an empty redo path are supported")
                self.placed += [node, split]
                items.append(Loop(node, split, self._parse(outs[0][1], split), exits[0]))
                node = exits[0]
            elif gateway and len(outs) > 1:
                merge = self.post[node]
                if len(self.out[merge]) != 1 or self.kind[merge] != self.kind[node]:
                    raise ValueError(f"Split {node} has no matching merge gateway")
                self.placed += [node, merge]
                items.append(Split(node, merge, [(flow, self._parse(target, merge)) for flow, target in outs]))
                node = self.out[merge][0][1]
            else:
                if len(outs) > 1 or len(self.inc[node]) > 1:
                    raise ValueError(f"Element {node} breaks the block structure")
                self.placed.append(node)
                items.append(Leaf(node))
                node = outs[0][1] if outs else None
        return Seq(items)

    def _entry(self, block):
        if isinstance(block, Seq):
            return self._entry(block.items[0])
        return block.node if isinstance(block, Leaf) else block.split if isinstance(block, Split) else block.join

    def _exit(self, block):
        if isinstance(block, Seq):
            return self._exit(block.items[-1])
        return block.node if isinstance(block, Leaf) else block.merge if isinstance(block, Split) else block.split

    def _gap_after(self, block):
        return self.split_gap if isinstance(block, Loop) else GAP   # loop exit flows carry a label

    def decisions(self):
        """XOR decisions in reading order: (gateway, outgoing flows with the main-line flow first)."""
        found = []

        def visit(block):
            if isinstance(block, Seq):
                for item in block.items:
                    visit(item)
            elif isinstance(block, Split):
                if self.kind[block.split] == "exclusiveGateway":
                    found.append((block.split, [block.main[0]] + [f for f, _ in block.lower] + [f for f, _ in block.bypass]))
                visit(block.main[1])
                for _, branch in block.lower:
                    visit(branch)
            elif isinstance(block, Loop):
                visit(block.body)
                found.append((block.split, [self.flow[(block.split, block.leave)], self.flow[(block.split, block.join)]]))

        visit(self.tree)
        return found

    # ---------------------------------------------------------------- sizes
    def _measure(self, block):
        if isinstance(block, Leaf):
            block.w, height = SIZE[self.kind[block.node]]
            block.up = block.down = height / 2
        elif isinstance(block, Seq):
            for item in block.items:
                self._measure(item)
            block.w = sum(i.w for i in block.items) + sum(self._gap_after(i) for i in block.items[:-1])
            block.up = max((i.up for i in block.items), default=0)
            block.down = max((i.down for i in block.items), default=0)
        elif isinstance(block, Split):
            for _, branch in block.branches:
                self._measure(branch)
            filled = [(flow, branch) for flow, branch in block.branches if branch.items]
            if not filled:
                raise ValueError(f"Split {block.split} has only empty branches")
            block.main = max(filled, key=lambda item: self.weights.get(item[0], 0))
            block.lower = [item for item in filled if item is not block.main]
            cursor = max(block.main[1].down, GATE / 2)
            for _, branch in block.lower:
                branch.dy = cursor + BRANCH_GAP + branch.up
                cursor = branch.dy + branch.down
            block.bypass = []
            for flow, branch in block.branches:
                if not branch.items:
                    cursor += LANE
                    block.bypass.append((flow, cursor))
            block.down = cursor
            block.up = max(block.main[1].up, GATE / 2)
            tail = max(self._gap_after(branch.items[-1]) for _, branch in filled)
            block.w = GATE + self.split_gap + max(branch.w for _, branch in filled) + tail + GATE
        else:
            self._measure(block.body)
            block.lane = max(block.body.down, GATE / 2) + LANE
            block.down = block.lane
            block.up = max(block.body.up, GATE / 2)
            tail = self._gap_after(block.body.items[-1]) if block.body.items else GAP
            block.w = GATE + GAP + block.body.w + tail + GATE if block.body.items else GATE + GAP + GATE

    # ------------------------------------------------------------ positions
    def _box(self, node, x, y):
        width, height = SIZE[self.kind[node]]
        self.bounds[node] = (x, y - height / 2, width, height)

    def _left(self, node):
        x, y, _, height = self.bounds[node]
        return x, y + height / 2

    def _right(self, node):
        x, y, width, height = self.bounds[node]
        return x + width, y + height / 2

    def _straight(self, source, target):
        self.edges[self.flow[(source, target)]] = [self._right(source), self._left(target)]

    def _place(self, block, x, y):
        if isinstance(block, Leaf):
            self._box(block.node, x, y)
        elif isinstance(block, Seq):
            for index, item in enumerate(block.items):
                self._place(item, x, y)
                if index:
                    self._straight(self._exit(block.items[index - 1]), self._entry(item))
                x += item.w + self._gap_after(item)
        elif isinstance(block, Split):
            merge_x = x + block.w - GATE
            self._box(block.split, x, y)
            self._box(block.merge, merge_x, y)
            start, down = x + GATE + self.split_gap, y + GATE / 2
            split_c, merge_c = x + GATE / 2, merge_x + GATE / 2
            flow, branch = block.main
            self._place(branch, start, y)
            self.edges[flow] = [self._right(block.split), self._left(self._entry(branch))]
            self._straight(self._exit(branch), block.merge)
            for flow, branch in block.lower:
                level = y + branch.dy
                self._place(branch, start, level)
                self.edges[flow] = [(split_c, down), (split_c, level), self._left(self._entry(branch))]
                last = self._exit(branch)
                self.edges[self.flow[(last, block.merge)]] = [self._right(last), (merge_c, level), (merge_c, down)]
            for flow, offset in block.bypass:
                self.edges[flow] = [(split_c, down), (split_c, y + offset), (merge_c, y + offset), (merge_c, down)]
        else:
            split_x = x + block.w - GATE
            self._box(block.join, x, y)
            self._box(block.split, split_x, y)
            if block.body.items:
                self._place(block.body, x + GATE + GAP, y)
                self._straight(block.join, self._entry(block.body))
                self._straight(self._exit(block.body), block.split)
            else:
                self._straight(block.join, block.split)
            join_c, split_c, down = x + GATE / 2, split_x + GATE / 2, y + GATE / 2
            self.edges[self.flow[(block.split, block.join)]] = [
                (split_c, down), (split_c, y + block.lane), (join_c, y + block.lane), (join_c, down)]

    def _place_rows(self, row_width):
        """Wrap the main line into rows of at most ``row_width``; one connector flow links two rows."""
        items = self.tree.items

        def span(first, last):                       # width of items[first:last] as one row
            return sum(i.w for i in items[first:last]) + sum(self._gap_after(i) for i in items[first:last - 1])

        count, start = 1, 0                          # greedy fill gives the number of rows ...
        for index in range(1, len(items) + 1):
            if index - start > 1 and span(start, index) > row_width:
                count, start = count + 1, index - 1
        cuts = min(combinations(range(1, len(items)), count - 1),   # ... which are then balanced
                   key=lambda c: max(span(a, b) for a, b in zip((0,) + c, c + (len(items),))))
        rows = [items[a:b] for a, b in zip((0,) + cuts, cuts + (len(items),))]
        self.rows, self.row_widths, y, previous = len(rows), [], 0.0, None
        for row_items in rows:
            row = Seq(row_items)
            self._measure(row)
            self.row_widths.append(row.w)
            if previous is not None:
                middle = y + previous.down + ROW_GAP / 2
                y += previous.down + ROW_GAP + row.up
            self._place(row, 0.0, y)
            if previous is not None:
                source, target = self._exit(previous), self._entry(row)
                (right, level), (left, _) = self._right(source), self._left(target)
                turn = right + max(TURN, self._gap_after(previous.items[-1]) - 20)   # room for a flow label
                self.edges[self.flow[(source, target)]] = [
                    (right, level), (turn, level), (turn, middle), (-TURN, middle), (-TURN, y), (left, y)]
            previous = row

    def _normalise(self):
        dx = MARGIN - min(min(x for x, _, _, _ in self.bounds.values()),
                          min(x for points in self.edges.values() for x, _ in points))
        dy = MARGIN - min(y for _, y, _, _ in self.bounds.values())
        self.bounds = {k: (x + dx, y + dy, w, h) for k, (x, y, w, h) in self.bounds.items()}
        self.edges = {k: [(x + dx, y + dy) for x, y in points] for k, points in self.edges.items()}
        self.width = max(max(x + w for x, _, w, _ in self.bounds.values()),
                         max(x for points in self.edges.values() for x, _ in points)) + MARGIN
        self.height = max(max(y + h for _, y, _, h in self.bounds.values()),
                          max(y for points in self.edges.values() for _, y in points)) + MARGIN

    def place_legend(self, boxes):
        """Arrange (annotation id, text) boxes in balanced columns of equal width below the diagram."""
        sizes = [annotation_size(text) for _, text in boxes]
        column = max(width for width, _ in sizes)
        count = max(1, min(len(boxes), int((self.width - 2 * MARGIN + LEGEND_GAP) // (column + LEGEND_GAP))))
        target = (sum(height for _, height in sizes) + LEGEND_GAP * (len(boxes) - 1)) / count
        top = self.height - MARGIN + LEGEND_TOP
        index, y, bottom = 0, top, top
        for (annotation, _), (_, height) in zip(boxes, sizes):
            if y > top and index < count - 1 and y - top + height / 2 > target:
                index, y = index + 1, top
            self.bounds[annotation] = (MARGIN + index * (column + LEGEND_GAP), y, column, height)
            y += height + LEGEND_GAP
            bottom = max(bottom, y - LEGEND_GAP)
        self.width = max(self.width, 2 * MARGIN + (index + 1) * (column + LEGEND_GAP) - LEGEND_GAP)
        self.height = bottom + MARGIN
        return index + 1


def apply_layout(root, name, weights=None, row_width=1800, legend=None):
    """Replace the diagram of the single process in ``root``; name process and diagram ``name``.

    ``legend`` lists the ids of free text annotations to arrange below the diagram, in display order.
    """
    process = root.find(f"{{{BPMN}}}process")
    process.set("name", name)
    layout = BlockLayout(process, weights, row_width)
    columns = 0
    if legend:
        texts = {e.attrib["id"]: e.find(f"{{{BPMN}}}text").text or "" for e in process if _tag(e) == "textAnnotation"}
        columns = layout.place_legend([(annotation, texts[annotation]) for annotation in legend])
    for old in root.findall(f"{{{DI}}}BPMNDiagram"):
        root.remove(old)
    diagram = ET.SubElement(root, f"{{{DI}}}BPMNDiagram", {"id": "diagram_1", "name": name})
    plane = ET.SubElement(diagram, f"{{{DI}}}BPMNPlane", {"id": "plane_1", "bpmnElement": process.attrib["id"]})
    for element, (x, y, width, height) in layout.bounds.items():
        attributes = {"id": f"shape_{element}", "bpmnElement": element}
        if layout.kind.get(element) == "exclusiveGateway":
            attributes["isMarkerVisible"] = "true"
        shape = ET.SubElement(plane, f"{{{DI}}}BPMNShape", attributes)
        ET.SubElement(shape, f"{{{DC}}}Bounds", {"x": f"{x:.1f}", "y": f"{y:.1f}", "width": f"{width:.1f}", "height": f"{height:.1f}"})
    for element, points in layout.edges.items():
        edge = ET.SubElement(plane, f"{{{DI}}}BPMNEdge", {"id": f"edge_{element}", "bpmnElement": element})
        for x, y in points:
            ET.SubElement(edge, f"{{{OMGDI}}}waypoint", {"x": f"{x:.1f}", "y": f"{y:.1f}"})
    return {"name": name, "width": round(layout.width), "height": round(layout.height), "rows": layout.rows,
            "row_widths": [round(w) for w in layout.row_widths], "flow_label_gap": layout.split_gap,
            "legend_boxes": len(legend or []), "legend_columns": columns}
