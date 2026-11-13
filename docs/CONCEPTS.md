# Event, case, trace, variant

Definitions used in this repository and their values in BPIC-17.

| Concept | Definition used here | BPIC-17 value |
|---|---|---|
| Event | One XES event: activity (`concept:name`), lifecycle state, timestamp, resource, attributes | Raw: **1,202,267** events (all lifecycle states) |
| Completion event | Event with `lifecycle:transition = complete`; input of discovery and evaluation (log C) | **475,306** events; 726,961 non-complete events excluded |
| Abstracted log | Completion events without logging artefacts (log A, [EVENT_ABSTRACTION.md](EVENT_ABSTRACTION.md)); input of the final model | **364,930** events, 17 labels |
| Lifecycle transition | State of one activity execution; 7 values: schedule, start, suspend, resume, complete, ate_abort, withdraw | A_/O_ events: `complete` only; W_ work items: all 7 states |
| Activity instance | One execution of an activity, possibly several lifecycle events | No instance identifier in the log; `EventID` unique per event (1,202,267 distinct) |
| Activity | Distinct `concept:name` label | Raw: 26; log C: 24 (`W_Personal Loan collection`, `W_Shortened completion ` have no complete events); log A: 17 |
| Case | Process instance; case ID `case:concept:name` | **31,509** cases = loan applications (`Application_...`); kept in every view |
| Trace | Ordered event sequence of one case, original XES order | 31,509 traces; mean raw length 38.156 events |
| Variant | Distinct activity sequence (one or more cases share it) | Raw (all lifecycle states): **15,930**; (activity, lifecycle) pairs: 16,692; log C: **5,623**; log A: **2,680** |
| Case notion | Choice of the object that groups events into a case | Application chosen; `EventOrigin` has 3 values: Application, Offer, Workflow |
| Offer | Sub-object of an application; `OfferID` is an event attribute, not a case ID | 42,995 distinct `OfferID` values = 42,995 `O_Create Offer` events; 8,559 applications with 2–10 offers |

The case notion is a design choice: offer events carry their own `OfferID` and
one application can have several offers, so an offer-level or object-centric view
would yield different cases, traces and variants.

Sources: [`raw_log_statistics.json`](../results/tables/raw_log_statistics.json),
[`import_summary.json`](../results/tables/import_summary.json),
[`raw_attribute_profile.tex`](../report/tables/raw_attribute_profile.tex),
[`abstraction_audit.json`](../results/abstraction/abstraction_audit.json) and the
`projection` blocks of the local caches in `tmp/evaluation/`.
