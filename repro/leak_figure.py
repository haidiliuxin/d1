"""The paper's key figure, from the raw artifacts.

The claim it carries is the whole boundary story in one view: for each payload item, at
**which boundary did it first sit in a surviving carrier?** In the wholesale arm every
item first appears at boundary 1, because the review record copies the memo. In the
staged arm item 2 cannot appear before boundary 2 and item 3 before boundary 3, because
the apparatus withholds them until the step that reveals them -- and that is what makes
0/12 at stage 3 a statement about the channel rather than about the model.

Emits a CSV (for plotting) and an ASCII rendering (so it works with no plotting stack).
Writes nothing unless you pass `--csv`.

    python repro/leak_figure.py [--csv PATH]
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1] / "runs" / "apt_lab"

#: Batches whose traces carry the per-item residue record. Everything else predates the
#: instrumentation and cannot appear in this figure at all.
INSTRUMENTED = (
    ("full", "chain-20260927-082833"),
    ("full", "chain-20260927-120354"),
    ("full", "chain-20260927-154757-full"),          # anchored detector, may be partial
    ("next-hop", "chain-20260927-144234-next-hop"),
    ("only-stage1", "chain-20260927-131947-only-stage1"),
    ("full/conclusion-only", "chain-20260927-160307-full-conclusion-only"),
)

BOUNDARIES = (1, 2, 3)


def runs(batch: str, arm: str) -> list[dict]:
    return [
        json.loads(f.read_text(encoding="utf-8"))
        for f in sorted((ROOT / batch).glob(f"{arm}-*.json"))
    ]


def first_boundary(j: dict, item: str) -> str:
    value = (j.get("leak_index") or {}).get(item)
    return "never" if value is None else f"b{value}"


def is_instrumented(rows: list[dict]) -> bool:
    """Whether these artifacts can carry the figure at all.

    A batch that predates the per-item instrumentation has no `leak_index` field, and
    reading absent as `None` would paint it as "the item never survived" -- a structural
    zero standing in for missing data, which is the exact confusion this project has
    paid for more than once. Batches are all-or-nothing, and that is asserted rather
    than assumed.
    """

    flags = ["leak_index" in j for j in rows]
    assert len(set(flags)) == 1, "a batch is partly instrumented; that should not happen"
    return bool(flags) and flags[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=pathlib.Path, default=None)
    parser.add_argument("--arm", default="R-forced")
    args = parser.parse_args()

    table: list[dict[str, str]] = []
    print("=" * 78)
    print("WHERE EACH ITEM FIRST SURVIVES (R-forced; instrumented batches only)")
    print("=" * 78)
    for label, batch in INSTRUMENTED:
        rows = runs(batch, args.arm)
        if not rows:
            continue
        if not is_instrumented(rows):
            print(f"\n  {label:<22} {batch}  (n={len(rows)})  "
                  f"[NOT INSTRUMENTED - predates the per-item record, excluded]")
            continue
        print(f"\n  {label:<22} {batch}  (n={len(rows)})")
        for item in ("1", "2", "3"):
            counts = Counter(first_boundary(j, item) for j in rows)
            cells = "  ".join(
                f"{seat}={counts.get(seat, 0)}"
                for seat in (*[f"b{b}" for b in BOUNDARIES], "never")
                if counts.get(seat, 0)
            )
            bar = "".join(
                "#" * counts.get(f"b{b}", 0) for b in BOUNDARIES
            ) + "." * counts.get("never", 0)
            print(f"    item {item}   {cells:<44} {bar}")
            for j in rows:
                table.append({
                    "batch": batch, "label": label, "arm": args.arm,
                    "seed": str(j.get("seed")), "item": item,
                    "first_boundary": first_boundary(j, item),
                })

    print()
    print("  reading: 'b1' = the item was already in the residue that survives the FIRST")
    print("  hand-off. For the wholesale arm that is wholesale carry; for the staged arm")
    print("  b1 would mean the seal failed (registered as P5).")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
        print(f"\n  wrote {len(table)} rows to {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
