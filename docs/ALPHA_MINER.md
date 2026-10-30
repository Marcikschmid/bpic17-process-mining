# Alpha Miner (classic): additional discovery baseline

Tutor feedback: "Alpha miner -> WF-net". Keyword notes only; numbers are taken from the files named below.

Reference: van der Aalst, Weijters, Maruster (2004), *Workflow mining: discovering process models from event logs*, IEEE TKDE 16(9), 1128–1142, doi:10.1109/TKDE.2004.47 (BibTeX key suggestion `vdaalst2004workflow`).

## Files and reproduction

| Artefact | Content |
|---|---|
| `scripts/discover_alpha.py` | Discovery, export, footprint, textbook Y_L check, directed WF-net check; `--audit` step |
| `src/net_certificates.py` | Directed WF-net check, Farkas certificate for final-marking unreachability, deterministic exact replay |
| `results/alpha/alpha_miner.pnml` | Native PM4Py result (only the net name normalised) |
| `results/alpha/alpha_miner.{pdf,png,svg,gv}` | Graphviz figure, same layout settings as `scripts/discover_models.py` |
| `results/alpha/manifest.json` | Input identity + counts, parameters, versions, runtime, footprint, structure, artefact SHA-256 |
| `results/assessment/alpha_miner.json` | Shared assessment (`scripts/assess_model.py`) |
| `results/alpha/completion_audit.json` | Final-marking certificate, exact whole-case replay |
| `results/alpha/dead_transition_certificates.json` | Dead-transition certificates (format of `results/tables/dead_transition_audit.json`) |

```powershell
.\.venv\Scripts\python.exe scripts/discover_alpha.py
.\.venv\Scripts\python.exe scripts/assess_model.py results/alpha/alpha_miner.pnml --name alpha_miner --out results/assessment
.\.venv\Scripts\python.exe scripts/discover_alpha.py --audit
```

- No `--diagnostics`: net unbounded and not easy sound, so the finite-state diagnostics are not applicable.
- Runtime: discovery 0.32 s; whole script 3.5 s; token metrics 16.7 s.
- Determinism: no randomness; `PYTHONHASHSEED=20261029` fixes set order (PM4Py place names, order-dependent pair merging). PNML arc ids and Graphviz node ids come from object hashes, so behaviour is reproducible but bytes are not.

## Input

- Same completion projection as IM/HM/Genetic: 31,509 cases, 475,306 completed events, 24 activities, 5,623 variants; original XES order within each case.
- EventLog built from `tmp/evaluation/projected_sequences.json` (SHA-256 `1838e245…279d`), not from the raw XES. Events carry `concept:name` only.
- Sufficient because classic Alpha reads only the directly-follows relation and the start/end activities, i.e. the order within each case.
- Checks in the script: raw SHA-256 = data manifest = cache; cache projection summary identical to `results/tables/discovery_manifest.json` preprocessing; case, event, activity and per-activity counts; unique case ids.

## What the Alpha Miner does

- Footprint from the directly-follows relation `a > b`:
  - causality `a → b`: `a > b` and not `b > a`
  - parallelism `a || b`: `a > b` and `b > a`
  - choice `a # b`: neither
- Places = maximal pairs (A, B): all `a ∈ A`, `b ∈ B` with `a → b`; elements within A, and within B, pairwise `#` (incl. `a # a`). Plus one source place (to start activities) and one sink place (from end activities).
- One visible transition per activity; **no silent transitions**, no duplicate labels → cannot skip activities, no invisible routing.
- **No parameters**: no thresholds, no noise or frequency filter. A single occurrence of `a b` changes the footprint. Only `activity_key`, `timestamp_key`, `case_id_key` (manifest `tuning_parameters.count = 0`); with EventLog input the timestamp and case keys are not read.
- Known limits:
  - length-1 loops (`a > a`): `a || a`, so `a` belongs to no place
  - length-2 loops (`a b a`): `a || b`, so there is no place between them
  - no noise handling; completeness of `>` assumed
  - no implicit/non-local dependencies
  - rediscovery guarantee only for sound SWF-nets without short loops and a complete log
- PM4Py implementation: single-pass pair merging (not the literal Y_L enumeration). Own textbook enumeration of Y_L gives the **same 23 internal places** (`manifest.json` → `structure.pm4py_places_equal_textbook_Y_L = true`).

## Footprint of the projection

| Relation | Count |
|---|---:|
| Directly-follows pairs (ordered, incl. self) | 159 |
| Causal pairs `→` | 91 |
| Parallel pairs `||` (unordered) | 30 |
| Choice pairs `#` (unordered, distinct) | 155 |
| Start activities | 1 (`A_Create Application`) |
| End activities | 16 |
| Length-1 loop activities | 8 |
| Length-2 loop pairs (`a b a` observed) | 12, all classified `||` |

- Length-1 loops: A_Incomplete, O_Cancelled, O_Refused, O_Returned, O_Sent (mail and online), O_Sent (online only), W_Assess potential fraud, W_Validate application.
- Length-2 loops include O_Create Offer/O_Created, A_Validating/W_Validate application, A_Complete/O_Sent (mail and online); full list in `manifest.json`.

## Discovered net

- 25 places (23 internal + `start` + `end`), 24 transitions (24 visible, 0 silent), 87 arcs.
- All 8 length-1 loop activities: only an arc to `end` (all are end activities), **no input place** → always enabled.
- O_Created: no input place (only predecessor O_Create Offer is `||` via the length-2 loop).
- O_Create Offer: **no output place** (only successor O_Created is `||`).

## WF-net verdict

- **Not a WF-net by definition** (van der Aalst: unique source place i, unique sink place o, every node on a directed path from i to o). Source `start` and sink `end` are unique, but:
  - no directed path from `start`: 9 transitions (8 length-1 loop activities + O_Created)
  - no directed path to `end`: A_Accepted, O_Create Offer, 3 places whose only output is O_Create Offer, 1 place whose only output is A_Accepted
- PM4Py `check_wfnet` = true, because PM4Py only tests connectivity of the **undirected** graph. `results/assessment/alpha_miner.json` reports this PM4Py value as `workflow_net: true`; the directed check (`manifest.json` → `structure.workflow_net_directed_definition`) is decisive.

## Soundness verdict: not sound

| Condition | Result | Evidence |
|---|---|---|
| Boundedness | violated | Witness: M0 = [start]; fire `A_Incomplete` (no input place) → [start, end] covers M0; repeatable without limit (`soundness.classical.witness`) |
| Proper completion | violated | Same firing: `end` marked while `start` still holds a token |
| Option to complete | violated | Final marking [end] unreachable from M0: Farkas vector y with y·C ≥ 0 for all transitions, y·M_f = 99 < y·M0 = 100, verified with exact fractions (`completion_audit.json`) |
| No dead transitions | violated | 10 transitions certified dead (place-subinvariant certificates, lower bound): A_Cancelled, A_Complete, A_Denied, A_Pending, A_Validating, O_Accepted, O_Create Offer, W_Call after offers, W_Call incomplete files, W_Complete application |
| Easy soundness | false | No complete run exists (final marking unreachable) |
| Relaxed soundness | false | No transition lies on a complete run |
| Safeness | false | 87 tokens in one place within the explored 30,000 states |
| Woflan (PM4Py) | unsound | Agrees, 3.3 s |

- The shared tool reports `easy_sound`/`relaxed_sound` as `null` (exploration stopped at 30,000 markings); the Farkas certificate settles both as false.
- Main failing condition: boundedness, caused by the length-1 loop transitions without input place.

## Quality dimensions (full projection, 31,509 cases)

| Dimension | Metric | Alpha | IM baseline | HM baseline | Genetic | Refined IMf |
|---|---|---:|---:|---:|---:|---:|
| Fitness | Exact whole-case replay | **0.00 %** (0 cases) | 100.00 % | ≤ 1.30 % | not enumerated | 80.45 % |
| Fitness | Token replay fitness | 0.4958 | 1.0000 | 0.8334 | 0.7410 | 0.9875 |
| Fitness | Token-fitting cases | 0.00 % | 100.00 % | 0.00 % | 0.00 % | 81.62 % |
| Fitness | Alignment fitness | not computed | 0.9998 | incomplete | – | 0.9765 |
| Precision | ETC token precision | 0.1259 | 0.2926 | 0.9978 | 0.5970 | 0.5952 |
| Precision | Align-ET | not computed | 0.2926 | 0.9975 | – | 0.5977 |
| Generalization | PM4Py token-based | 0.9870 | 0.9757 | 0.8611 | 0.9828 | 0.9912 |
| Simplicity | Arc degree (PM4Py) | 0.392 | 0.6170 | 0.4815 | 0.7755 | 0.7008 |
| Simplicity | Nodes / arcs (own) | 49 / 87 | 87 / 114 | 143 / 220 | 76 / 87 | 89 / 108 |
| Simplicity | Extended Cardoso (own) | 34 | 47 | 108 | 43 | 52 |
| Simplicity | Extended Cyclomatic (own) | n/a (unbounded) | 1552 | unbounded | unbounded | 551 |

Sources: Alpha `results/assessment/alpha_miner.json`, `results/alpha/completion_audit.json`; IM/HM `results/tables/quality_metrics.md`; Genetic `results/genetic/seed_20261025/manifest.json` (`metrics`); refined IMf `results/assessment/refined_imf.json`.

- Exact replay is deterministic (unique labels, no silent transitions), so it is exact even for an unbounded net. First failing step:
  - O_Create Offer not enabled: 20,421 cases. Every case has its first O_Create Offer before any A_Complete and before any A_Validating, but some input places of O_Create Offer are filled only by A_Complete or A_Validating.
  - A_Concept not enabled: 11,086 cases (= number of cases without A_Submitted). A_Concept has two input places; one is filled only by A_Submitted, so skipping A_Submitted leaves it empty.
  - W_Complete application not enabled: 2 cases.
- Consistent upper bound: every case contains a certified dead activity, so at most 0 % of cases can fit (`dead_transition_certificates.json`).
- Alignment fitness / Align-ET: skipped by the shared tool because its finite-state solver needs a bounded net with reachable final marking. Not approximated.
- Token fitness 0.50: replay with missing/remaining tokens; tokens accumulate in `end`; heuristic, no case fits.
- Precision 0.13: lowest in the table; the 9 transitions without input place are always enabled, like a flower part.
- Generalization 0.99: frequency heuristic over transition firings; not meaningful for a model with 0 fitting cases.
- Simplicity: smallest net (no silent transitions), but the lowest PM4Py arc-degree score in the table; small size alone does not make the model readable here.

## Why not suitable as the base model

- Not a WF-net (directed definition); not sound: unbounded and all three classical conditions violated; not easy sound.
- 0 % exact replay vs. the ~80 % target; lowest token fitness and token precision in the table.
- 10 of 24 activities dead, 9 always enabled → the model does not express the observed control flow.
- Representational bias: one visible transition per activity, no silent transitions (skipped A_Submitted blocks A_Concept in 11,086 cases); short loops lost (8 length-1, 12 length-2 loop patterns in the log).
- No noise handling and no parameters: rare directly-follows pairs (5,623 variants) shape the footprint, and the algorithm has no setting to tune against that.
- Kept only as a documented baseline for the tutor's feedback; the IMf-based model (sound, 80.45 % exact replay, `results/assessment/refined_imf.json`) remains the base.
