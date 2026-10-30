# Genetic Miner budget notes

Keyword notes. Numbers from `results/genetic/budget_notes.json`, written by
`scripts/genetic_budget.py` from recorded artifacts only (no rerun):
`results/genetic/seed_20261025/manifest.json`, `evolution.csv`,
`tmp/genetic_seed_20261025.log`, installed PM4Py 2.7.23.11 source.

```powershell
.\.venv\Scripts\python.exe scripts/genetic_budget.py
```

## Recorded run (seed 20261025)

- Input: full completion projection, 31,509 cases, 475,306 events, 24 activities (same as IM/HM).
- Configured: population 10, generations 6, elitism 0.1 (1 elite), tournament sample 2, crossover 1.0, mutation 0.01.
- Planned maximum: 6 tournaments x 10 = 60 fitness evaluations.
- Actual: 2 tournaments (initial population + 1 offspring generation) = 20 fitness evaluations, 1 of them an elite re-evaluation.
- Best native objective: 0.30489724447042077 in tournament 0 and tournament 1 (unchanged) -> native early stop.
- Fitness evaluation = one PM4Py token replay of the full log (`pm4py.fitness_token_based_replay`, classic.py line 234), every individual, every tournament (loop line 232; elites re-evaluated, no cache).

## Measured wall-clock

- `evolution.csv` stamps: naive local `datetime.now()` after each tournament (classic.py lines 157, 179).
- UTC offset derived, not assumed: `started_utc` + `discovery_seconds` (1460.533 s) vs. last row -> +3600 s, residual 0.002 s.
- Start -> tournament 0: 800.385 s (input preparation, causal matrix, initial population, 10 evaluations).
- Tournament 0 -> 1: 660.150 s for 10 evaluations (incl. selection, crossover, mutation, net conversion).
- **66.015 s per fitness evaluation** (2.095 ms per case, 138.9 us per event).
- Fixed overhead estimate: 800.385 - 660.150 = 140.2 s (assumes tournament 0 evaluations cost as much as tournament 1).
- Limit: one timed interval of 10 evaluations; no per-individual times, no variance.
- Log file has no timestamps; used only for consistency (START parameters = manifest; DONE generations 2 and native objective match).
- DONE quality line in the log = invalid duplicate-ID export (`audit/INVALID_export_evaluation.json`, token fitness 0.4745); not used.

## Extrapolation: PM4Py defaults on the same full log

Defaults: population 500, generations 100, elitism 0.01 (5 elites), tournament sample 5
(classic.py lines 117, 120, 129, 132; `pm4py.discover_petri_net_genetic` lines 456, 457, 460, 461).
Estimate = evaluations x 66.015 s; single process; excludes fixed overhead and token-replay cost variation between individuals.

| Scenario | Tournaments | Evaluations | Hours | Days |
|---|---:|---:|---:|---:|
| One default tournament | 1 | 500 | 9.17 | 0.38 |
| Earliest native stop (best unchanged in generation 1) | 2 | 1,000 | 18.34 | 0.76 |
| Earliest stop if generation 1 improves | 52 | 26,000 | 476.77 | 19.87 |
| Full default budget | 100 | 50,000 | 916.87 | 38.20 |
| This run (measured `discovery_seconds` 1460.533, incl. overhead) | 2 | 20 | 0.41 | 0.02 |

- Default maximum / this budget's maximum = 50,000 / 60 = 833x.

## Native early-stop rule

Source: `.venv/Lib/site-packages/pm4py/algo/discovery/genetic/variants/classic.py`
(sha256 `897b7002e0c98e9d082bac8fb6b4370ee6f7dd34aafed495d4df7dbe05f599a8`).

```python
155  population, fitness = tournament(...)                      # tournament 0
159  for _ in tqdm(range(generations-1), "Genetic generations"):
160      if fitness[0] == 1 or (history and all(f == fitness[0] for f in history[-int(generations/2):])):
161          break
162      history.append(fitness[0])
164      next_population = population[:round(elitism_rate * population_size)]
177      population, fitness = tournament(...)                  # every individual re-evaluated
```

- Stop if best objective == 1, or current best equals every value in `history[-int(generations/2):]`.
- Window: int(6/2) = 3 here; int(100/2) = 50 for defaults.
- `history` holds one best per finished check; while shorter than the window the slice is shorter.
- First check with non-empty history (2nd loop iteration): window = [best of tournament 0] -> one stagnant generation stops the search.
- Elite kept (line 164) and re-evaluated deterministically -> best never decreases; "equal" = no improvement.
- Possible tournament counts, this budget (all 32 improve/stagnate patterns replayed): 2, 5, 6.
- Possible tournament counts, defaults: 2, or 52..100 (if generation 1 improves, the window still contains tournament 0 up to check 51).
- This run: best of tournament 1 == tournament 0 -> stop at line 160/161 after 2 tournaments, 20 of 60 planned evaluations.

## Consequences

- Default budget on the full log: up to about 38 days single-process on this machine; even the earliest native stop about 18 h.
- Small budget (population 10) chosen before the run (D09); cost per evaluation now measured, not assumed.
- Early stop after one stagnant generation is a property of the installed implementation, not a convergence result.
- One seed, one run: no claim about the miner in general.

## Related records

- `results/genetic/seed_20261025/dead_transition_certificates.json`: 15 of 39 transitions certified dead (8 activities), other 24 fireable (verified witnesses); final marking certified unreachable -> exact replay ceiling 0 of 31,509 cases.
- `results/assessment/genetic_miner.json`: unbounded (witness), not sound; Woflan agrees.
