# Heuristics Miner: native heuristics net and dependency sweep

Keyword notes. Numbers from `results/heuristics/manifest.json` (written by
`scripts/discover_heuristics_variants.py`) and `results/assessment/heuristics_*.json`
(`scripts/assess_model.py`). Same full completion projection as all other models
(31,509 cases, 475,306 events, 24 activities).

```powershell
.\.venv\Scripts\python.exe scripts/discover_heuristics_variants.py
.\.venv\Scripts\python.exe scripts/assess_model.py results/heuristics/dep_0.9/model.pnml --name heuristics_dep_0.9 --out results/assessment
```

## Native output (tutor: "Heuristic -> Miner")

- Native result = heuristics net (dependency graph), not a Petri net: `pm4py.discover_heuristics_net`, frequency decoration.
- Figures: `results/heuristics/native/heuristics_net.{pdf,svg,png}` (edge label: dependency value and frequency), `heuristics_net_pm4py.*` (unchanged PM4Py rendering).
- Default net: 24 activity nodes, 65 dependency arcs, 4 self-loops, 4 length-two-loop arcs, 15 AND-split pairs, 21 AND-join pairs.
- 1 start activity (`A_Create Application`), **16 end activities** -> conversion needs many silent routing transitions (70 in the converted net).
- DFG pre-cleaning (`dfg_pre_cleaning_noise_thresh` 0.05) removes 83 of 159 directly-follows arcs **before** the dependency threshold acts.
- Lowest kept dependency at default: 0.7375 -> every threshold <= 0.7375 yields the same net (0.5 and 0.7 identical).

## Sweep: `dependency_thresh` 0.5 / 0.7 / 0.9 / 0.99 (all other parameters default)

| Threshold | Dependency arcs | L2L arcs | AND splits / joins | Petri-net nodes | Bounded | Sound |
|---|---:|---:|---:|---:|---|---|
| 0.5 (default) | 65 | 4 | 15 / 21 | 143 | no (witness) | no |
| 0.7 | 65 | 4 | 15 / 21 | 143 | no (witness) | no |
| 0.9 | 59 | 12 | 10 / 16 | 141 | no (witness) | no |
| 0.99 | 49 | 12 | 8 / 13 | 124 | no (witness) | no |

- Result: no threshold removes the unboundedness -> HM is not a sound simulation base at any tested setting.
- Default net: >= 12 certified dead transitions (incl. `O_Refused`, `O_Sent (mail and online)`) -> at most 411 / 31,509 cases (1.30 %) can fit exactly (`results/tables/dead_transition_audit.json`).
- Token precision ~0.997 at all thresholds although almost no case fits: precision of a non-fitting net is not meaningful on its own.
- Whole sweep: 18.5 s.

## Reproducibility caveat (token-replay metrics on HM nets)

- Same heuristics net (dep. 0.5 and 0.7 are identical; 94 transitions, 70 silent, 49 places), four assessments on 2026-10-29: token fitness 0.8334-0.8363, token generalization 0.8338-0.8611 (`results/models/heuristics_miner.pnml` twice, `dep_0.5`, `dep_0.7`).
- Cause: PM4Py token replay chooses among enabled silent transitions in hash/set order; HM net has 70 silent transitions and is unbounded, so the chosen path changes with object ids and `PYTHONHASHSEED`.
- Consequence: HM token values differ by up to ~0.03 between runs; differences between HM sweep points below that are not meaningful.
- Not affected: sound, bounded IM/IMf nets (exact replay, exact alignments and Align-ET are deterministic, cross-checked against PM4Py).
