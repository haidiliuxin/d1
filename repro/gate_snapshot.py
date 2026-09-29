"""Record the Phase B gate as a dated snapshot, with the batches it read.

A verdict that lives only in a terminal scrollback is not evidence. This writes the
numbers, the batch list and the verdict to one JSON, so that "the gate returned X on
date Y" can be checked later against the same artifacts -- and so that a later
re-run which quietly reads a different batch set is visible rather than invisible.

    python repro/gate_snapshot.py
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import chain_stats as cs  # noqa: E402

REPO = _HERE.parent
OUT = REPO / "runs" / "apt_lab"


def pool_for(variant: str, policy: str,
             model: str = cs.DEFAULT_MODEL) -> tuple[dict, list[str]]:
    """The pooled arms for one (payload, policy, model), plus the batch names that fed them.

    The model is part of the key for the same reason the payload is: every published rate
    is a `MiniMax-M2.7` rate, and a second model's runs must not be able to join one.
    """

    pool: dict[str, dict] = {}
    used: list[str] = []
    for d in sorted(cs.ROOT.glob("chain-*")):
        if not d.is_dir() or d.name in cs.VOID_BATCHES:
            continue
        if cs.variant_of(d) != variant or cs.policy_of(d) != policy:
            continue
        if variant == "full" and d.name in cs.PRE_FINAL_CRITERIA_BATCHES:
            continue
        # roles=False: every number this snapshot records is a published rate, and the
        # D-1 permission arm is a different treatment.
        info = cs.batch(d, variant=variant, policy=policy, model=model, roles=False)
        if not info["arms"]:
            continue
        used.append(d.name)
        for arm, r in info["arms"].items():
            p = pool.setdefault(arm, {
                "s1": 0, "s2": 0, "s2t": 0, "s3": 0, "n": 0, "n_s2": 0,
                "s3d": 0, "s3d_n": 0, "formed": [0, 0, 0, 0], "unformed": [0, 0, 0, 0],
            })
            for key in ("s1", "s2", "s2t", "s3", "n", "n_s2", "s3d", "s3d_n"):
                p[key] += r.get(key, 0)
            # The residue-formation split has to travel with the pool: the manipulation
            # guard reads it, and a pool that dropped it reported a manipulation failure
            # that had not happened -- which would have triggered the registered fallback
            # wording for no reason.
            for bucket in ("formed", "unformed"):
                for i, value in enumerate(r.get(bucket, [0, 0, 0, 0])):
                    p[bucket][i] += value
    return pool, used


def main() -> int:
    main_pool, main_batches = pool_for("full", "quote-as-assessed")
    abl_pool, abl_batches = pool_for("full", "conclusion-only")

    gates = cs.phase_b_gate(
        main_pool.get("R-forced", {}), main_pool.get("C0-forced", {}),
        abl_pool.get("R-forced", {}), abl_pool.get("C0-forced", {}),
    )
    verdict = "GO" if all(ok for _, ok, _ in gates) else "NO-GO"

    snapshot = {
        "taken_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "primary_batches": main_batches,
        "ablation_batches": abl_batches,
        "primary": {k: main_pool.get(k, {}) for k in ("R-forced", "C0-forced")},
        "ablation": {k: abl_pool.get(k, {}) for k in ("R-forced", "C0-forced")},
        "gates": [{"criterion": c, "met": bool(ok), "detail": d} for c, ok, d in gates],
        "verdict": verdict,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = OUT / f"phaseB-gate-{stamp}.json"
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )

    print("=" * 78)
    print(f"PHASE B GATE SNAPSHOT -- {snapshot['taken_utc']}")
    print("=" * 78)
    print(f"  primary  batches: {', '.join(main_batches) or '(none)'}")
    print(f"  ablation batches: {', '.join(abl_batches) or '(none)'}")
    for criterion, ok, detail in gates:
        print(f"  [{'GO  ' if ok else 'NOGO'}] {criterion}")
        if detail:
            print(f"          {detail}")
    print()
    print(f"  ==> {verdict}")
    print(f"  written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
