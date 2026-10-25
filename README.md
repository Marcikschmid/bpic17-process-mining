# BPIC-17 Process Mining

[Public GitHub repository](https://github.com/Marcikschmid/bpic17-process-mining)

Python implementation of Assignment I: event-log analysis, process discovery,
conformance checking, model refinement and decision mining on the BPI Challenge
2017 loan-application log. **Python 3.12.10** is the analysis language;
**PM4Py 2.7.23.11** is the process-mining library. The LaTeX report is maintained
separately in [`report/`](report/).

## Current status

| Assignment component | Available implementation and results |
|---|---|
| 3.2: log statistics | Full raw-log statistics and independent XML audit |
| 3.3.1: process discovery | Inductive Miner and Heuristics Miner baselines |
| 3.3.2: model quality | Four quality dimensions and independently implemented complexity measures; additional optimal HM alignment fitness remains incomplete |
| 3.3.3: refinement | 40 candidates; selected BPMN structure replays 25,350/31,509 cases (80.45%) |
| 3.3.4: decision mining | 16 XOR-split classifiers; rules visible directly in BPMN; separate test cases |
| Report | Selected factual tables and figures; author-written interpretation still pending |
| 3.4: advanced analysis | Not implemented |

**Structural coverage and guarded coverage are different.** The selected
control-flow model reaches 80.45% whole-case replay without learned guards.
Enforcing all learned guards yields 10.40% over all cases and **10.19% on the
held-out test cases**. These statistical rules are not validated bank policy.
See [refinement](docs/REFINEMENT.md), [decision mining](docs/DECISION_MINING.md)
and the [assignment checklist](docs/CHECKLIST.md) for limitations and open work.

## Quick start on Windows

Prerequisites: Git and Python 3.12, available as `python`. The setup creates a
local virtual environment, installs pinned dependencies, registers its notebook
kernel and installs the checked portable Graphviz version. Full-log processing
can require substantial memory; optimal alignments can run for a long time.

For a fresh checkout:

```powershell
git clone https://github.com/Marcikschmid/bpic17-process-mining.git
Set-Location bpic17-process-mining
.\scripts\setup.ps1
.\.venv\Scripts\python.exe scripts/download_data.py
```

For an existing checkout, start in the repository root containing `.git`, `src/`
and `report/`. Check it with `git rev-parse --show-toplevel`.

The pinned dependency set is in [`requirements.txt`](requirements.txt); direct
dependencies are in [`requirements.in`](requirements.in). The setup is validated
on Windows. Other platforms may need platform-specific dependency and Graphviz
setup changes. PowerShell scripts are setup/build helpers; the analysis itself
is Python. No database server is required: the input is a compressed XES log.

### Explore the data in Jupyter

```powershell
.\scripts\start_jupyter.ps1
```

Open the printed localhost URL, select **BPIC17 (.venv)** and run notebook cells
from top to bottom. Keep the terminal running; use a second terminal for other
commands. Stop Jupyter with `Ctrl+C`. Environment activation is optional because
the commands use its Python executable directly.

After moving the project, register the project-local kernel again:

```powershell
.\.venv\Scripts\python.exe -m ipykernel install --prefix .venv --name bpic17 --display-name "BPIC17 (.venv)"
```

### View the BPMN and its XOR decisions

Install the local browser assets once, then start the server from the repository
root and leave its terminal running:

```powershell
.\.venv\Scripts\python.exe scripts/setup_bpmn_viewer.py
.\.venv\Scripts\python.exe -m http.server 8787 --bind 127.0.0.1
```

- [BPMN with visible XOR rules](http://127.0.0.1:8787/results/decision_mining/viewer.html)
- [Decision trees and evaluation](http://127.0.0.1:8787/results/decision_mining/index.html)
- [Original refined control-flow model](http://127.0.0.1:8787/results/refinement/index.html)

These localhost links work on your computer while its server is running.
Use the gateway selector or zoom controls to inspect each decision. Static
outputs are also available: [BPMN PDF](results/decision_mining/decision_bpmn.pdf),
[BPMN XML](results/decision_mining/decision_model.bpmn) and
[all decision blocks](results/decision_mining/decision_blocks.pdf).

## Data and preprocessing

Source: Boudewijn van Dongen, *BPI Challenge 2017*,
[dataset DOI](https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b).
The download script verifies the original files against publisher metadata;
[`data/manifest.json`](data/manifest.json) records their checksums and provenance.
The original data and its terms are documented in [`data/README.md`](data/README.md).

- Raw log: **31,509 cases**, **1,202,267 events**, **26 activity labels**.
- Discovery/evaluation projection: completion events only, **475,306 events**,
  **24 activity labels**, all 31,509 cases and their original event order retained.
- The original compressed XES file stays unchanged. Raw statistics use all
  lifecycle states; control-flow results use the documented completion projection.

Raw downloads, virtual environments, browser libraries, alignment checkpoints
and bulky per-decision observations are excluded from Git. The repository tracks
source code, manifests, selected models, summary tables and figures.

## How Python and PM4Py are used

| Component | Main implementation |
|---|---|
| XES import | PM4Py `read_xes`, through [`src/event_log.py`](src/event_log.py) |
| Discovery | PM4Py Inductive Miner and Heuristics Miner CLASSIC, in [`src/discovery.py`](src/discovery.py) |
| Quality metrics | PM4Py token/alignment fitness, precision, generalization and arc-degree simplicity; [`scripts/evaluate_models.py`](scripts/evaluate_models.py) |
| BPMN/PNML models | PM4Py process-tree conversion, import/export and Petri-net types |
| Independent checks | Python implementations of complexity, exact replay and finite-state alignment/precision; compared with PM4Py references |
| Decision rules | Alignment-derived input snapshots and scikit-learn CART; verified against PM4Py alignment costs |
| Figures and viewer | Python/Matplotlib/Graphviz outputs; local bpmn-js interface |

The independently implemented simplicity measures satisfy the assignment's
additional implementation requirement. PM4Py remains the core process-mining
library; custom checks and optimizations are identified in the method documents.

## Reproduce analyses

Run commands from the repository root. Normal analysis/rendering writes to
`results/` and ignored `tmp/`, without overwriting report sources.

**Raw statistics (3.2):**

```powershell
.\.venv\Scripts\python.exe scripts/analyze_log.py
.\.venv\Scripts\python.exe scripts/render_log_statistics.py
.\.venv\Scripts\python.exe scripts/verify_log_statistics.py
```

**Discovery (3.3.1):**

```powershell
.\.venv\Scripts\python.exe scripts/discover_models.py
```

**Baseline quality (3.3.2):** full recomputation is described in
[`docs/EVALUATION.md`](docs/EVALUATION.md). The optional optimal HM alignments
are computationally expensive; completed variants are checkpointed and reused.
No subset-average fitness is reported for the unfinished run. Existing results:
[`quality_metrics.md`](results/tables/quality_metrics.md).

**Refinement (3.3.3):** the complete candidate sweep, parameters, data selection,
export and verification commands are in [`docs/REFINEMENT.md`](docs/REFINEMENT.md).
Prepare the full-log sequence cache before refinement or decision mining:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_models.py --prepare
```

**Decision mining (3.3.4):** starting from the committed refined BPMN and the
prepared sequence cache:

```powershell
.\.venv\Scripts\python.exe scripts/mine_decisions.py
.\.venv\Scripts\python.exe scripts/render_decisions.py
.\.venv\Scripts\python.exe scripts/verify_decisions.py
```

The case-wise train/test split uses seed **20261018**. All repetitions of a case
stay in the same split. Parameters, feature availability, alignment ambiguity
and export limitations are in [`docs/DECISION_MINING.md`](docs/DECISION_MINING.md).

## Validation

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_setup.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The current suite contains 42 tests, covering preprocessing, metric calculations,
case weighting, resumable alignments, model semantics and decision-input timing.
Data-dependent audit scripts additionally verify complete-case coverage,
checksums, exported rules and reference results. A full decision audit requires
regenerating the ignored observation files with `mine_decisions.py` first.

## Build the LaTeX report

Install a TeX distribution with Latexmk and Perl, then run:

```powershell
.\report\build.ps1
```

Output: `report/build/main.pdf`. The build uses selected assets already under
`report/`, so it does not require Python, the raw log or a rerun of the analyses.
The build directory is ignored by Git. Report layout and asset selection are
explained in [`report/README.md`](report/README.md).

The report is in English with a maximum of five main pages, excluding references
and appendix. Its scientific narrative and abstract remain the author's work.
AI-assisted activity is recorded in [`docs/AI_USAGE.md`](docs/AI_USAGE.md).

## Repository layout

| Path | Purpose |
|---|---|
| `src/` | Reusable Python analysis, discovery, validation and decision-mining code |
| `scripts/` | Python entry points and PowerShell setup/start helpers |
| `tests/` | Automated tests on small examples and reference results |
| `notebooks/` | Interactive data exploration |
| `data/` | Data instructions, provenance and local raw/processed files |
| `results/` | Generated models, tables, figures and audit records |
| `report/` | Separate LaTeX project and deliberately selected result copies |
| `docs/` | Method details, codebase guide, checklist and AI-use record |
| `literature/` | Source catalogues; downloaded third-party material stays local |
| `1 Introduction/`, `2 Process Mining/`, `Allgemeines/` | Original course materials |

For module relationships, see [`docs/CODEBASE.md`](docs/CODEBASE.md).
Existing licence notices in course materials and the TUM template remain in
force; this repository does not assign a new licence to that material. Dataset
terms and third-party software licences remain separate.
