"""Independent re-derivation of the M20 / displacement statistics.

Written from scratch rather than by calling the branch's `fisher_exact.py`, because
importing the module under test to check the module under test is not a check. The
committed `criteria-evaluation.json` claims specific p-values; this recomputes them
from the arm counts in `summary-v2.json` and reports both Fisher definitions, since
the two-sided p depends on which one is used and the report does not say.

Also recomputes Wilson intervals and the contrasts the branch's `discriminator`
reduces to `inconclusive`, so that verdict can be confirmed rather than accepted.
"""

from __future__ import annotations

import json
import math
import pathlib

SUMMARY = (
    pathlib.Path(__file__).resolve().parent / "data" / "m20-summary-v2.json"
)


def _log_choose(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _hypergeom(a: int, b: int, c: int, d: int) -> float:
    """P(table with these margins and this cell)."""

    n = a + b + c + d
    return math.exp(
        _log_choose(a + b, a)
        + _log_choose(c + d, c)
        - _log_choose(n, a + c)
    )


def fisher(a: int, n1: int, c: int, n2: int) -> dict:
    """Two-sided Fisher exact on [[a, n1-a], [c, n2-c]] by two definitions.

    `double`  -- sum of all tables whose probability is <= the observed one.
                 This is the definition scipy uses for 2x2.
    `double_min` -- 2 * min(one-sided tails), capped at 1.
    """

    b, d = n1 - a, n2 - c
    observed = _hypergeom(a, b, c, d)
    total = 0.0
    for x in range(0, min(n1, a + c) + 1):
        y = a + c - x
        if y < 0 or y > n2 or (n1 - x) < 0:
            continue
        probability = _hypergeom(x, n1 - x, y, n2 - y)
        if probability <= observed + 1e-12:
            total += probability

    def tail(lo: int, hi: int) -> float:
        acc = 0.0
        for x in range(lo, hi + 1):
            y = a + c - x
            if 0 <= y <= n2 and 0 <= n1 - x:
                acc += _hypergeom(x, n1 - x, y, n2 - y)
        return acc

    upper = min(n1, a + c)
    lower = max(0, a + c - n2)
    return {
        "table": f"{a}/{n1} vs {c}/{n2}",
        "p_sum_small": round(min(1.0, total), 6),
        "p_double_min": round(min(1.0, 2 * min(tail(lower, a), tail(a, upper))), 6),
        "p_greater": round(tail(a, upper), 6),
    }


def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (round(centre - half, 4), round(centre + half, 4))


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    routes = summary["routes"]

    print("=" * 78)
    print("A) arm rates: my Wilson vs the committed Wilson")
    print("=" * 78)
    for route, body in routes.items():
        print(f"\n{route}")
        for arm, data in sorted(body["arms"].items()):
            n = data["n_eligible"]
            k = data.get("dispositions", {}).get("release", 0)
            low, high = wilson(k, n)
            theirs = (round(data["wilson_low"], 4), round(data["wilson_high"], 4))
            flag = "ok" if (low, high) == theirs else f"MISMATCH theirs={theirs}"
            print(f"  {arm:<20} {k}/{n} = {k/n if n else 0:.3f}  "
                  f"wilson=({low:.2f},{high:.2f})  {flag}")

    print()
    print("=" * 78)
    print("B) the Fisher contrasts the branch reports")
    print("=" * 78)
    gate = routes["CB-CDX-COVERAGE-GATE-01"]["arms"]

    def counts(arm: str) -> tuple[int, int]:
        data = gate[arm]
        return data.get("dispositions", {}).get("release", 0), data["n_eligible"]

    claimed = {
        ("decoy-rule", "decoy-norule"): 0.029,
        ("decoy-rule", "decoy-withdrawn"): 0.034,
        ("decoy-rule", "baseline"): 0.335,
    }
    for (left, right), reported in claimed.items():
        a, n1 = counts(left)
        c, n2 = counts(right)
        result = fisher(a, n1, c, n2)
        print(f"  {left} vs {right}: {result['table']}  "
              f"p_sum_small={result['p_sum_small']:.4f}  "
              f"p_double_min={result['p_double_min']:.4f}  "
              f"p_greater={result['p_greater']:.4f}  (report claims ~{reported})")

    print()
    print("=" * 78)
    print("C) the displacement hypothesis contrasts (the unreported part)")
    print("=" * 78)
    pairs = [
        ("no-decoy", "decoy-rejectable"),
        ("no-decoy", "decoy-inert"),
        ("no-decoy", "decoy-pre-rejected"),
        ("decoy-inert", "decoy-rule"),
        ("decoy-inert", "decoy-rejectable"),
    ]
    for left, right in pairs:
        a, n1 = counts(left)
        c, n2 = counts(right)
        result = fisher(a, n1, c, n2)
        print(f"  {left:<20} vs {right:<20} {result['table']:<16} "
              f"p={result['p_sum_small']:.4f}")

    # H1/H2 in the direction the design predicted: decoy arms ABOVE no-decoy.
    a, n1 = counts("no-decoy")
    pooled_k = sum(counts(arm)[0] for arm in ("decoy-rejectable", "decoy-inert", "decoy-pre-rejected"))
    pooled_n = sum(counts(arm)[1] for arm in ("decoy-rejectable", "decoy-inert", "decoy-pre-rejected"))
    result = fisher(a, n1, pooled_k, pooled_n)
    print(f"\n  no-decoy {a}/{n1} vs pooled decoy arms {pooled_k}/{pooled_n}: "
          f"p_sum_small={result['p_sum_small']:.4f}  p_greater={result['p_greater']:.4f}")
    print("  (H1 predicts decoy arms ABOVE no-decoy; the observed direction is "
          f"{'ABOVE' if pooled_k/pooled_n > a/n1 else 'BELOW'} no-decoy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
