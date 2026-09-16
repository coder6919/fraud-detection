# Fraud Ring Detection via Graph Analysis

Detects coordinated fraud rings — clusters of accounts that share subtle
identifiers (device, browser, email domain, billing address) and collude —
rather than scoring transactions independently. Built on the [IEEE-CIS Fraud
Detection dataset](https://www.kaggle.com/c/ieee-fraud-detection) (Kaggle).

A single ring account can look unremarkable on its own — small amount,
normal hour, nothing a per-transaction classifier would flag. The ring only
becomes visible when you look at the *network*: a cluster of accounts
unusually densely connected through shared identifiers, created in a tight
time window, often with one hub account other members funnel through.

## Architecture

```
IEEE-CIS CSVs → ingest/clean → shared-identifier graph (NetworkX)
                                          |
                         Louvain community detection (python-louvain)
                                          |
                    ring scoring (density + fraud rate + creation-time tightness)
                                          |
                              FastAPI: /graph /rings /account
                                          |
                    React frontend: force-directed graph, ring list, drill-down
```

Two components: `backend/` (Python data pipeline + graph analysis + FastAPI)
and `frontend/` (React, plain JSX, custom D3-force graph rendering — no
off-the-shelf graph library).

## Running it

**Backend**
```bash
cd backend
python -m venv venv && venv/Scripts/activate  # or source venv/bin/activate
pip install -r requirements.txt
python -m scripts.build_graph --sample-frac 1.0   # builds graph_store/graph.pkl + rings.json
python -m uvicorn api.main:app --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, expects the API on :8000
```

The dataset (`ieee-fraud-detection/*.csv`) isn't in this repo — download it
from Kaggle and place the five CSVs at the project root in that folder.

## How the graph is built

- **Nodes** = accounts, derived from a composite of `card1–card6 + addr1 +
  addr2` (the dataset has no single clean account ID).
- **Edges** = a shared, genuinely non-null identifier value between two
  accounts (device fingerprint, browser/OS string, email domain, billing
  address), weighted by how strong that signal is.
- **Noise control**: a value shared by more than 40 accounts is excluded
  outright. Below that, edge weight is inverse-frequency dampened for
  *every* identifier field — a value shared by 2 accounts gets full weight,
  one shared by 30 gets roughly an eighth. Without this, generic values
  (`gmail.com`, or a `DeviceInfo` value that's really just "Windows")
  connect huge swaths of unrelated accounts and turn the graph into one
  meaningless blob.

## How rings are scored

Louvain partitions the graph into candidate clusters. Each is scored as a
weighted combination of internal edge density, transaction-level fraud rate,
and how tightly its accounts were created in time — normalized across all
candidates. Clusters over 50 members are penalized rather than trusted as a
single ring (large "clusters" are usually leftover identifier noise, not one
coordinated group).

**A tuning note worth keeping**: the first pass weighted density / fraud
rate / creation-time tightness at 0.3 / 0.45 / 0.25. On the full dataset,
density turned out to be ~1.0 for almost every candidate cluster (Louvain
tends to produce near-complete small subgraphs here), so it carried no real
ranking signal. Creation-time tightness, weighted that heavily, surfaced
several clusters that happened to open around the same time but had *zero*
actual fraud in them — ahead of real rings in score. Reweighting to 0.15 /
0.70 / 0.15 (fraud rate dominant) took top-ring precision from ~6% to 50% at
a 0.5 score threshold, and to 100% at 0.7. This is the kind of thing that
only shows up once you evaluate against the full dataset, not the dev
sample — worth watching for in any score blending real signals of very
different reliability.

## Results (full dataset, 590,540 transactions)

| | Ring detection (score ≥ 0.5) | Baseline Random Forest, matched to same alert volume |
|---|---|---|
| Alerts (transactions flagged) | 76 | 76 |
| Precision | 50% (2 of 4 flagged rings are majority-fraud) | 63% |
| Recall | 0.16% (34 of 20,663 fraud transactions) | 0.93% |

The baseline (tabular Random Forest, no graph features — amount, hour,
product code, card type, email domain) is evaluated on a held-out test
split, so its numbers are a fair generalization estimate. The ring numbers
are reported over the same data the rings were scored on, so precision here
is partly circular by construction — treat it as a structural sanity check
("does the score correlate with real fraud concentration"), not a
held-out claim. Both operating points are small-N (4 rings / 76 alerts) —
these percentages have wide confidence intervals.

**Honest takeaway**: at this operating point, the baseline classifier flags
more fraud per alert than graph-based ring detection does. That's not the
outcome the framing in the intro hoped for, and it's worth saying plainly
rather than glossing over. Two things are true at once, though:

1. Recall is low largely **by design**, not by failure — this approach can
   only ever catch fraud that shares identifiers with at least one other
   account. IEEE-CIS wasn't constructed with labeled ring fraud; most of its
   20,663 fraud transactions are very likely isolated (card testing,
   one-off takeover) rather than coordinated, and this method structurally
   cannot see those, by design (see `pipeline/evaluate.py`).
2. Of the fraud this method *can* see, the top-ranked rings are genuinely
   good: `ring_0054` (4 accounts, 67% fraud rate) and `ring_0019` (14
   accounts, 57% fraud rate) rank #1 and #2 by score — the scoring formula
   does surface real coordinated fraud at the top, it's just a small slice
   of total fraud volume.

The realistic production framing: graph-based ring detection is a
**complement** to per-transaction scoring, not a replacement — it finds a
different, high-confidence slice (coordinated multi-account fraud) that a
row-wise classifier has no way to see structurally, at the cost of missing
everything that isn't part of a detectable cluster. Run both; route ring
members to enhanced review rather than auto-decline on ring membership
alone given the small-N confidence caveat above.

## Known limitations

- Recall is inherently capped by identifier connectivity — isolated fraud is
  out of scope by design (see above).
- Account identity is a heuristic composite key, not a real account ID —
  two different real accounts could coincidentally collide, or one real
  account could fragment across multiple derived IDs if its card fields
  vary transaction-to-transaction.
- Precision numbers are computed on the same data the rings were scored
  against (fraud rate is a scoring input), so they're a sanity check, not a
  held-out generalization claim — see the results table above.
- Ring scoring weights were tuned by inspection against this dataset's full
  run; they're not cross-validated against a held-out set of rings.
