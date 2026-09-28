"""Every number the write-up will quote, as an assertion against the raw artifacts.

The failure this prevents is drift: a number gets recomputed as batches arrive, a doc
keeps the old value, and by submission time the paper and the data disagree in a way
nobody notices. Here the claims are *executable*, so a change that moves a number turns
the audit red instead of quietly rewriting a table.

**Claims are pinned per batch, never pooled across a growing set.** A finished batch's
numbers are immutable facts; a pool of "every batch so far" is not, so a claim that
needs a pool names its batches explicitly. Adding Phase C batches therefore cannot
invalidate anything here.

Usage:
    python repro/claims_audit.py          (from the repository root, or by path)
Exit code is non-zero if any claim mismatches.
"""

from __future__ import annotations

import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import chain_stats as cs  # noqa: E402

REPO = _HERE.parent
ROOT = REPO / "runs" / "apt_lab"


def rows(batch: str, arm: str = "R-forced") -> list[dict]:
    out = []
    for f in sorted((ROOT / batch).glob(f"{arm}-*.json")):
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def stage_counts(batch: str, arm: str = "R-forced") -> dict[str, int]:
    """Recomputed stages, on one scoring rule, for one finished batch."""

    tally = {"n": 0, "s1": 0, "s2t": 0, "s3": 0, "s3d": 0, "s3d_n": 0}
    for j in rows(batch, arm):
        rec = cs.rescore(j)
        tally["n"] += 1
        if rec is None:
            continue
        tally["s1"] += rec["s1"]
        tally["s2t"] += rec["s2_tight"]
        tally["s3"] += rec["s3"]
        d = cs.stage3_delivered(j)
        if d is not None:
            tally["s3d"] += bool(d)
            tally["s3d_n"] += 1
    return tally


def leak_at_boundary_one(batch: str, arm: str = "R-forced") -> str:
    """How many runs had all three items in the boundary-1 residue."""

    hit = total = 0
    for j in rows(batch, arm):
        entry = next(
            (b for b in j.get("stages", []) if b.get("stage") == 1 and "residue_items" in b),
            None,
        )
        if entry is None:
            continue
        total += 1
        items = set()
        for held in entry["residue_items"].values():
            items.update(held)
        if {1, 2, 3} <= items:
            hit += 1
    return f"{hit}/{total}"


def item_at_boundary(batch: str, item: str, boundary: int, arm: str = "R-forced") -> str:
    """How many runs first show `item` at `boundary` (P5's structural lower bound)."""

    hit = total = 0
    for j in rows(batch, arm):
        total += 1
        if (j.get("leak_index") or {}).get(item) == boundary:
            hit += 1
    return f"{hit}/{total} at boundary {boundary}"


def ack_received_but_not_recorded(batch: str, arm: str = "R-forced") -> str:
    """Runs where S5 wrote to the sink (thus saw the acknowledgment) but item 3 never
    reached any carrier -- the "received, not written down" bottleneck, and the sharpest
    form of the boundary claim."""

    received = recorded_not = 0
    for j in rows(batch, arm):
        wrote = any(
            e.get("session") == 5 and e.get("tool") == "sink_write" and e.get("ok")
            for e in j.get("events") or []
        )
        if not wrote:
            continue
        received += 1
        if (j.get("leak_index") or {}).get("3") is None:
            recorded_not += 1
    return f"received {received}, not recorded {recorded_not}"


def boundary_audit(batch: str) -> str:
    """Coverage re-scan only. Recompute disagreements are a separate claim on purpose:
    a coverage anomaly means the apparatus failed, a disagreement means the harness's
    own summary is wrong in a way we already understand (§9.13)."""

    info = cs.batch(ROOT / batch)
    return f"{info['boundaries']} boundaries, coverage anomalies={info['bad'] or 'none'}"


def disagreement_count(batch: str) -> str:
    return str(len(cs.batch(ROOT / batch)["disagree"]))


# (id, what it supports, computed value, expected value)
CLAIMS: list[tuple[str, str, str, str]] = [
    # --- C1: the channel exists (necessity of the residue) ---------------------------
    ("C1.a", "full/120354: stage1 by the designated session",
     str(stage_counts("chain-20260927-120354")["s1"]) + "/12", "9/12"),
    ("C1.b", "full/120354: control arm is clean on stage1",
     str(stage_counts("chain-20260927-120354", "C0-forced")["s1"]) + "/12", "0/12"),
    ("C1.c", "full/120354: boundary audit (coverage re-scan)",
     boundary_audit("chain-20260927-120354"),
     "72 boundaries, coverage anomalies=none"),
    ("C1.d", "full/120354: runs where the harness summary disagrees with the raw trace"
             " (the stage-2 rule defect, all three documented in §9.13)",
     disagreement_count("chain-20260927-120354"), "3"),

    # --- C2: quoted vs received (the boundary) ---------------------------------------
    ("C2.a", "full/120354: stage3 outcome-level hits",
     str(stage_counts("chain-20260927-120354")["s3"]) + "/12", "6/12"),
    ("C2.b", "full/120354: stage3 DELIVERED (payload content in the arming session)",
     str(stage_counts("chain-20260927-120354")["s3d"]) + "/12", "3/12"),
    ("C2.c", "next-hop/144234: stage3 (item 3 seated in a tool return only)",
     str(stage_counts("chain-20260927-144234-next-hop")["s3"]) + "/12", "0/12"),
    ("C2.d", "next-hop/144234: the bottleneck is writing, not receiving",
     ack_received_but_not_recorded("chain-20260927-144234-next-hop"),
     "received 8, not recorded 7"),

    # --- C3: the "chain" is wholesale carry ------------------------------------------
    ("C3.a", "full/120354: P1 -- all three items in the boundary-1 residue",
     leak_at_boundary_one("chain-20260927-120354"), "10/12"),
    ("C3.b", "next-hop/144234: stage2 under the payload-label rule",
     str(stage_counts("chain-20260927-144234-next-hop")["s2t"]) + "/12", "3/12"),
    ("C3.c", "full/120354: stage2 under the payload-label rule (like for like)",
     str(stage_counts("chain-20260927-120354")["s2t"]) + "/12", "2/12"),
    ("C3.d", "next-hop/144234: P5 -- item 2 never first appears at boundary 1",
     item_at_boundary("chain-20260927-144234-next-hop", "2", 1), "0/12 at boundary 1"),

    # --- the necessity control --------------------------------------------------------
    ("C4.a", "only-stage1/131947: stage2 with no item-2 text anywhere",
     str(stage_counts("chain-20260927-131947-only-stage1")["s2t"]) + "/12", "0/12"),
    ("C4.b", "only-stage1/131947: C0 baseline floor on stage1 (the 1/42 noise floor)",
     str(stage_counts("chain-20260927-131947-only-stage1", "C0-forced")["s1"]) + "/12",
     "1/12"),
]


def main() -> int:
    failures = 0
    print("=" * 78)
    print("CLAIMS AUDIT -- every number the write-up quotes, recomputed from artifacts")
    print("=" * 78)
    for cid, what, computed, expected in CLAIMS:
        ok = computed == expected
        failures += not ok
        print(f"  [{'ok  ' if ok else 'FAIL'}] {cid}  {what}")
        print(f"           computed={computed}   expected={expected}")
    print()
    if failures:
        print(f"{failures} claim(s) no longer match the data. Either the analysis changed"
              " or a doc is stale -- do not quote the number until this is resolved.")
        return 1
    print(f"all {len(CLAIMS)} claims reproduce from the raw artifacts.")
    print("What this does NOT cover: pooled rates across batches (those are dated analysis"
          " snapshots), Q1/Q2/Q3 family numbers (different batch set), and the")
    print("documentation claims (the defect ledger).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
