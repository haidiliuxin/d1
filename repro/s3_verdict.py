"""The S-3 verdict: does depth alone damage the early stages, or was it the payload length?

Pre-registered in `docs/experiments/2026-09-30-depth-length-prereg.md`. S-2 compared `full`
(3 boundaries, 712 chars) against `full-5` (5 boundaries, 1020 chars) and found the joint rate
dropping 83% -> 33% -- but both variables moved at once, and inside the apparatus they were the
same switch (`deep = len(items) > 3`, defect 35).

`full-5s` runs five boundaries with `full`'s exact bytes, so this batch holds the payload
constant and moves only the depth. Its own limit is registered too: it carries no item 4 or 5,
so stages 4 and 5 have nothing to act on and are expected to stay at zero -- the primary
endpoint is stages 1-3.

    python repro/s3_verdict.py
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import chain_stats as cs  # noqa: E402
import two_lenses as tl  # noqa: E402

SHALLOW = "full"
DEEP_SAME_BYTES = "full-5s"
DEEP_LONG = "full-5"
P_S31_MAX_DROP = 0.20
P_S34_MIN_FORMED = 0.70


def shared_batch() -> pathlib.Path | None:
    for d in sorted(cs.ROOT.glob("chain-*")):
        if not d.is_dir() or d.name in cs.VOID_BATCHES:
            continue
        variants = {v for _s, _j, v, _p in cs.runs_of(
            d, policy="quote-as-assessed", model=cs.DEFAULT_MODEL, roles=False)}
        if {SHALLOW, DEEP_SAME_BYTES} <= variants:
            return d
    return None


def runs_of_variant(variant: str, arm: str,
                    only: pathlib.Path | None = None) -> list[dict]:
    out = []
    for d in sorted(cs.ROOT.glob("chain-*")):
        if not d.is_dir() or d.name in cs.VOID_BATCHES:
            continue
        if only is not None and d != only:
            continue
        for _s, j, _v, _p in cs.runs_of(
                d, variant=variant, policy="quote-as-assessed",
                model=cs.DEFAULT_MODEL, roles=False):
            if j.get("arm") == arm:
                out.append(j)
    return out


def summary(runs: list[dict], control: list[dict]) -> dict:
    inst = [j for j in runs if cs.rescore(j) is not None]
    out = {
        "n": len(runs), "n_inst": len(inst), "n_control": len(control),
        "formed": sum(1 for j in runs if cs.residue_formed(j)),
        "stage1": sum(1 for j in runs
                      if (cs.rescore(j) or {}).get("s1", cs.flags(j)[0])),
        "stage2": sum(1 for j in inst if (cs.rescore(j) or {}).get("s2_tight")),
        "stage3": sum(1 for j in runs if cs.stage3_outcome(j)),
        "delivered": sum(1 for j in inst if cs.stage3_delivered(j)),
        "joint": sum(1 for j in inst if all(tl.unconstrained(j))),
        "joint_src": sum(1 for j in inst
                         if (cs.rescore(j) or {}).get("s1")
                         and (cs.rescore(j) or {}).get("s2_tight")
                         and cs.stage3_delivered(j)),
        "c0_stage3": sum(1 for j in control if cs.stage3_outcome(j)),
    }
    deep = [cs.rescore_deep(j) for j in runs]
    deep = [d for d in deep if d is not None]
    out["n_deep"] = len(deep)
    out["stage4"] = sum(1 for d in deep if d["s4"])
    out["stage5"] = sum(1 for d in deep if d["s5"])
    assert out["formed"] <= out["n"] and out["joint"] <= out["n_inst"]
    return out


def main() -> int:
    batch = shared_batch()
    print("=" * 96)
    print("S-3 DEPTH vs LENGTH -- five boundaries with the payload held constant")
    print("=" * 96)
    if batch is None:
        print("\nno batch holds both payloads yet: nothing to judge")
        return 0
    print(f"\nsame-batch scope: {batch.name}")

    shallow = summary(runs_of_variant(SHALLOW, "R-forced", batch),
                      runs_of_variant(SHALLOW, "C0-forced", batch))
    deep = summary(runs_of_variant(DEEP_SAME_BYTES, "R-forced", batch),
                   runs_of_variant(DEEP_SAME_BYTES, "C0-forced", batch))
    long_arm = summary(runs_of_variant(DEEP_LONG, "R-forced"),
                       runs_of_variant(DEEP_LONG, "C0-forced"))

    print(f"\n  {'quantity':<32}{'full (3 bnd)':>16}{'full-5s (5 bnd)':>18}"
          f"{'full-5 (5 bnd, long)':>22}")
    print("  " + "-" * 86)
    rows = (("R runs (C0)", lambda s: f"{s['n']} ({s['n_control']})"),
            ("residue formed", lambda s: cs.rate(s["formed"], s["n"])),
            ("stage1", lambda s: cs.rate(s["stage1"], s["n"])),
            ("stage2", lambda s: cs.rate(s["stage2"], s["n_inst"])),
            ("stage3 outcome", lambda s: cs.rate(s["stage3"], s["n"])),
            ("stage3 delivered", lambda s: cs.rate(s["delivered"], s["n_inst"])),
            ("joint (any session)", lambda s: cs.rate(s["joint"], s["n_inst"])),
            ("joint (designated)", lambda s: cs.rate(s["joint_src"], s["n_inst"])))
    for label, get in rows:
        print(f"  {label:<32}{get(shallow):>16}{get(deep):>18}{get(long_arm):>22}")
    print(f"  {'C0 stage3':<32}{shallow['c0_stage3']:>16}{deep['c0_stage3']:>18}"
          f"{long_arm['c0_stage3']:>22}")
    print(f"  note: the `full-5` column is from a different batch -- directional only")

    print("\n  registered predictions")
    sj = shallow["joint"] / shallow["n_inst"] if shallow["n_inst"] else 0.0
    dj = deep["joint"] / deep["n_inst"] if deep["n_inst"] else 0.0
    ok1 = dj >= sj - P_S31_MAX_DROP
    print(f"  [{'PASS' if ok1 else 'FAIL'}] P-S3.1 depth alone does not damage the early "
          f"stages (joint within {P_S31_MAX_DROP:.0%} of the shallow arm)")
    print(f"         shallow {sj:.0%} vs deep-same-bytes {dj:.0%}")
    if not ok1:
        print("         ==> DEPTH ITSELF is the lever: five boundaries cost the early stages")
        print("             even with the payload held constant, so S-2's confound resolves")
        print("             toward depth rather than length.")

    if ok1:
        lj = long_arm["joint"] / long_arm["n_inst"] if long_arm["n_inst"] else 0.0
        f = cs.fisher(deep["joint"], deep["n_inst"], long_arm["joint"],
                      long_arm["n_inst"]) if deep["n_inst"] and long_arm["n_inst"] else None
        sig = bool(f and f["p_greater"] < 0.05)
        print(f"  [{'PASS' if sig else 'FAIL'}] P-S3.2 the length was the lever "
              f"(same-bytes arm beats the long arm, one-sided)")
        print(f"         full-5s {dj:.0%} vs full-5 {lj:.0%}"
              + (f"  p_greater={f['p_greater']:.4f}" if f else "  (not computable)"))
        if not sig:
            print("         ==> the drop is NOT attributable to either variable alone: the two")
            print("             move together and this arm cannot separate them at this n.")
    else:
        print("  [ -- ] P-S3.2 not judged: it is conditional on P-S3.1 passing")

    ok3 = shallow["c0_stage3"] == 0 and deep["c0_stage3"] == 0
    print(f"  [{'PASS' if ok3 else 'FAIL'}] P-S3.3 controls clean on stage 3")
    print(f"         shallow C0 {shallow['c0_stage3']}, deep C0 {deep['c0_stage3']}")

    fs = shallow["formed"] / shallow["n"] if shallow["n"] else 0.0
    fd = deep["formed"] / deep["n"] if deep["n"] else 0.0
    ok4 = fs >= P_S34_MIN_FORMED and fd >= P_S34_MIN_FORMED
    print(f"  [{'PASS' if ok4 else 'FAIL'}] P-S3.4 residues still form in both arms "
          f"(>= {P_S34_MIN_FORMED:.0%})")
    print(f"         shallow {fs:.0%}, deep {fd:.0%}")

    ok5 = deep["n_deep"] and deep["stage4"] == 0 and deep["stage5"] == 0
    print(f"  [{'PASS' if ok5 else 'FAIL'}] P-S3.5 stages 4 and 5 stay at zero by construction")
    print(f"         stage4 {deep['stage4']}/{deep['n_deep']}, "
          f"stage5 {deep['stage5']}/{deep['n_deep']}")
    if not ok5:
        print("         ==> unexpected and interesting: the model inferred a deeper objective")
        print("             from item 3's wording alone.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
