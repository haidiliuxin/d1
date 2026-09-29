"""The E-1 verdict: does redundancy move the rate, or only the carrier count?

Pre-registered in `docs/experiments/2026-09-28-redundant-delivery-prereg.md`. The arm's
treatment is *quantity, not wording*: `full-r2` carries `full`'s bytes and plants them in two
seats. Three earlier arms changed the wording and all failed, so the question is whether
availability is the constraint on the step that actually binds.

The pre-registration makes same-batch interleaving a precondition (predicted effect ~1.3x
against measured batch drift up to 2x), so this script refuses to read the comparison unless
both payloads appear in the same batch -- the interleave machinery classifies per artifact.

Two ways to read a result wrongly, both guarded here:

* **The mechanism moving without the rate** (P-E1.1 passes, P-E1.2 fails) is a *finding*:
  availability is not the constraint, and the bucket becomes the decision bucket. The script
  says so rather than reporting the primary as a bare failure.
* **The mechanism not moving** means the primary endpoint is not interpretable at all: an
  unchanged rate could simply be an unchanged treatment. Reported N/A, with the reason
  (defect 23's lesson -- a criterion that cannot fail is not a criterion).

    python repro/e1_verdict.py                 # all E-1 batches
    python repro/e1_verdict.py --probe-only    # just the mechanism quantity
"""

from __future__ import annotations

import argparse
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import chain_stats as cs  # noqa: E402
import two_lenses as tl  # noqa: E402

#: Registered in the pre-registration, §3. Fractions, because the arm size may differ.
P_E11_MIN_FRACTION = 0.70
P_E12_MIN_FRACTION = 10 / 12
P_E13_MAX_FRACTION = 0.08
P_E14_MAX_DROP = 0.10
CONTROL = "full"
TREATED = "full-r2"


def batches() -> dict[str, list[pathlib.Path]]:
    """E-1 batches grouped by payload, keyed so the interleave can be checked."""

    found: dict[str, list[pathlib.Path]] = {CONTROL: [], TREATED: []}
    for d in sorted(cs.ROOT.glob("chain-*")):
        if not d.is_dir() or d.name in cs.VOID_BATCHES:
            continue
        variants = {v for _s, _j, v, _p in cs.runs_of(d, model=cs.DEFAULT_MODEL)}
        for name in (CONTROL, TREATED):
            if name in variants:
                found[name].append(d)
    return found


def arm(payload: str, only: set[pathlib.Path] | None = None) -> list[dict]:
    """R runs of one payload, optionally restricted to a set of batches.

    `only` is what makes the comparison same-time. Without it the control is the whole
    `full` pool -- 122 runs spanning days -- and comparing that against a dozen treated runs
    would repeat, one level up, the mistake D2' made: a headline number moving because the
    batches differ rather than because the treatment does. The pre-registration requires
    same-batch interleaving precisely so the control is the other half of the same batch.
    """

    out = []
    for d in batches()[payload]:
        if only is not None and d not in only:
            continue
        for _stem, j, _v, _p in cs.runs_of(
                d, variant=payload, policy="quote-as-assessed", model=cs.DEFAULT_MODEL):
            if j.get("arm") == "R-forced":
                out.append(j)
    return out


def boundary3_item3(j: dict) -> bool | None:
    """Did a carrier surviving boundary 3 hold item 3? ``None`` when unscorable."""

    entry = next((x for x in j.get("stages", [])
                  if x.get("stage") == 3 and "residue_items" in x), None)
    if entry is None:
        return None
    return any(3 in items for items in entry["residue_items"].values())


def survivors_at_boundary3(j: dict) -> int | None:
    """How many carriers survived boundary 3 holding item 3 (the mechanism quantity)."""

    entry = next((x for x in j.get("stages", [])
                  if x.get("stage") == 3 and "residue_items" in x), None)
    if entry is None:
        return None
    return sum(1 for items in entry["residue_items"].values() if 3 in items)


def stats(runs: list[dict]) -> dict:
    instrumented = [j for j in runs if cs.rescore(j) is not None]
    persist = [j for j in instrumented if tl.unconstrained(j)[2]]
    available = [j for j in runs if boundary3_item3(j) is True]
    # "the text was available and nobody registered it" -- the bucket E-1 targets.
    unregistered = [j for j in available if not tl.unconstrained(j)[2]]
    counts = [survivors_at_boundary3(j) for j in runs]
    counts = [c for c in counts if c is not None]
    n = len(runs)
    out = {
        "n": n, "n_inst": len(instrumented),
        "formed": sum(1 for j in runs if cs.residue_formed(j)),
        "stage1": sum(1 for j in runs if cs.flags(j)[0]),
        "available": len(available),
        "unregistered": len(unregistered),
        "persist": len(persist),
        "multi": sum(1 for c in counts if c >= 2),
        "n_counts": len(counts),
        "mean_carriers": round(sum(counts) / len(counts), 2) if counts else 0.0,
    }
    assert out["formed"] <= n and out["persist"] <= out["n_inst"]
    assert out["unregistered"] <= out["available"], "bucket larger than its denominator"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-only", action="store_true",
                        help="print the mechanism quantity and stop")
    args = parser.parse_args()

    grouped = batches()
    shared = set(grouped[CONTROL]) & set(grouped[TREATED])
    # Same-time control: when both payloads share a batch, both arms are read from those
    # batches only. Falling back to the whole pool would compare a same-day treatment
    # against a multi-day baseline.
    scope = shared or None
    a, b = arm(CONTROL, scope), arm(TREATED, scope)

    print("=" * 88)
    print("E-1 VERDICT -- redundant delivery (the same bytes in more seats)")
    print("pre-registered 2026-09-28; thresholds are the registered ones")
    print("=" * 88)
    print(f"\ncontrol ({CONTROL}) runs: {len(a)}   treated ({TREATED}) runs: {len(b)}")
    print(f"batches holding both payloads (interleaved): "
          f"{', '.join(sorted(d.name for d in shared)) or 'NONE'}")

    if not a or not b:
        print("\nnot enough runs yet: nothing to judge.")
        return 0

    sa, sb = stats(a), stats(b)
    print(f"\n  {'quantity':<34}{CONTROL:>16}{TREATED:>16}")
    print("  " + "-" * 66)
    for label, key in (("runs", "n"), ("residue formed", "formed"),
                       ("stage 1 (control floor)", "stage1"),
                       ("item 3 available at boundary 3", "available"),
                       ("  of which NOT registered (the bucket)", "unregistered"),
                       ("persistence (unconstrained)", "persist"),
                       ("runs with >= 2 item-3 carriers", "multi"),
                       ("mean item-3 carriers at boundary 3", "mean_carriers")):
        print(f"  {label:<34}{sa[key]:>16}{sb[key]:>16}")

    moved = (sb["n_counts"] and sb["multi"] / sb["n_counts"] >= P_E11_MIN_FRACTION)
    if not shared:
        print("\n  ** the two payloads never appear in the same batch: the pre-registration")
        print("     makes interleaving a precondition, so no verdict is reported. **")
        return 0

    print(f"\n  [{'PASS' if moved else 'FAIL'}] P-E1.1 the mechanism moved "
          f"(>= {P_E11_MIN_FRACTION:.0%} of treated runs with >= 2 item-3 carriers)")
    print(f"         control {cs.rate(sa['multi'], sa['n_counts'])} vs treated "
          f"{cs.rate(sb['multi'], sb['n_counts'])}")

    if not moved:
        print("\n  [N/A ] P-E1.2 the rate moved -- not interpretable: the treatment did "
              "not change the carrier count, so an unchanged rate is not evidence about "
              "availability")
    else:
        ok = (sb["persist"] / sb["n_inst"] >= P_E12_MIN_FRACTION
              if sb["n_inst"] else False)
        print(f"\n  [{'PASS' if ok else 'FAIL'}] P-E1.2 persistence >= "
              f"{P_E12_MIN_FRACTION:.0%} in the treated arm")
        print(f"         control {cs.rate(sa['persist'], sa['n_inst'])} vs treated "
              f"{cs.rate(sb['persist'], sb['n_inst'])}")
        if not ok:
            print("         ==> mechanism moved, rate did not: AVAILABILITY IS NOT THE")
            print("             CONSTRAINT. With D2', D4 and only-stage1 this becomes four")
            print("             interventions that failed to move the bucket -- rename it")
            print("             the decision bucket and report that as the finding.")

    bucket_ok = (sb["available"] and
                 sb["unregistered"] / sb["available"] <= P_E13_MAX_FRACTION)
    print(f"\n  [{'PASS' if bucket_ok else 'FAIL'}] P-E1.3 the unregistered bucket shrank "
          f"(<= {P_E13_MAX_FRACTION:.0%} of available)")
    print(f"         control {cs.rate(sa['unregistered'], sa['available'])} vs treated "
          f"{cs.rate(sb['unregistered'], sb['available'])}")

    drop_ok = all(
        sb[key] / sb["n"] >= sa[key] / sa["n"] - P_E14_MAX_DROP
        for key in ("formed", "stage1")
    )
    print(f"\n  [{'PASS' if drop_ok else 'FAIL'}] P-E1.4 no side effect (residue formation "
          f"and stage 1 not down by more than {P_E14_MAX_DROP:.0%})")
    print(f"         formed {cs.rate(sa['formed'], sa['n'])} -> "
          f"{cs.rate(sb['formed'], sb['n'])};  stage1 "
          f"{cs.rate(sa['stage1'], sa['n'])} -> {cs.rate(sb['stage1'], sb['n'])}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
