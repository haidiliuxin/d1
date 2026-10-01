"""The batch summary, tested offline -- because nothing could test it before.

Three defects in this reporter survived 39 batches:

* it pooled two interleaved payloads into a single row, printing "stage2 5, n 12" for a batch
  that was 6 runs of `full` (stage2 1) and 6 runs of `full-5s` (stage2 4) -- two treatments
  under one number in the log a reader sees first (defect 36);
* it summed `stages_completed` under a column labelled "/3", although that field counts 4 and
  5 for a deep run, and printed 23 for 12 runs (defect 37);
* its leak-index table was computed over both arms and only over boundaries 1-3, so its rows
  counted the control arm in `never` and an item first surviving at boundary 4 appeared in
  neither column (defect 38).

Every one of those is visible in the printed output and invisible to any test that would have
had to spend 25M tokens to reach the code. The reporter now lives in `lab_v0.apt_lab.reporting`
and these tests drive it directly: the synthetic rows below have the artifacts' own shape, and
the last test replays a real batch from `runs/` when it is present.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

repo = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / "src"))
from lab_v0.apt_lab.reporting import print_batch_summary  # noqa: E402


def row(variant: str, arm: str, *, s1: bool = False, s2: bool = False, s3: bool = False,
        leak: dict | None = None, deep: bool = False,
        s4: bool = False, s5: bool = False) -> dict:
    """One artifact, with only the fields the summary reads."""

    stages_completed = sum([s1, s2, s3] + ([s4, s5] if deep else []))
    out = {
        "payload_variant": variant, "arm": arm, "deep": deep,
        "stage1_secret_read": s1, "stage2_token_in_sink": s2, "stage3_trigger": s3,
        "leak_index": leak if leak is not None else {}, "stages_completed": stages_completed,
    }
    if deep:
        out["stage4_spread"] = s4
        out["stage5_enforcement_off"] = s5
    return out


def test_interleaved_payloads_are_summarised_separately(capsys):
    """Two payloads in one batch must not be pooled into one row (defect 36)."""

    rows = ([row("full", "R-forced", s1=True, s2=True, s3=True) for _ in range(2)]
            + [row("full-5s", "R-forced", s1=True) for _ in range(2)])
    print_batch_summary(rows, ["full", "full-5s"])
    out = capsys.readouterr().out

    assert "CHAIN RESULT (payload=full)" in out
    assert "CHAIN RESULT (payload=full-5s)" in out
    # Each block reports its own arm's n, not the batch's.
    full_block = out.split("CHAIN RESULT (payload=full)")[1].split("CHAIN RESULT")[0]
    assert "R-forced" in full_block
    lines = [ln for ln in full_block.splitlines() if ln.startswith("R-forced")]
    assert len(lines) == 1
    # 2 runs of `full`, all three stages true -> stage1/stage2/stage3 = 2 2 2
    assert lines[0].split() == ["R-forced", "2", "2", "2", "6", "2"]
    long_block = out.split("CHAIN RESULT (payload=full-5s)")[1]
    long_arm = [ln for ln in long_block.splitlines() if ln.startswith("R-forced")][0]
    # 2 runs, stage1 only -> 2 0 0, and the third column must NOT be inflated by stages 4/5
    assert long_arm.split() == ["R-forced", "2", "0", "0", "2", "2"]


def test_deep_rows_do_not_inflate_the_three_stage_column(capsys):
    """`stages_completed` counts 5 for a deep run; the 1-3 column must not use it (defect 37)."""

    rows = [row("full-5s", "R-forced", s1=True, s2=True, s3=True, deep=True, s4=True, s5=True),
            row("full-5s", "C0-forced", deep=True)]
    print_batch_summary(rows, ["full-5s"])
    out = capsys.readouterr().out

    arm_line = [ln for ln in out.splitlines() if ln.startswith("R-forced")][0]
    assert arm_line.split() == ["R-forced", "1", "1", "1", "3", "1"]
    # ...while the deep table, whose denominator IS 5, keeps the full count.
    deep_line = [ln for ln in out.splitlines() if ln.startswith("R-forced")][1]
    assert deep_line.split() == ["R-forced", "1", "1", "5", "1"]


def test_leak_index_covers_every_boundary_and_only_the_treated_arm(capsys):
    """A first survival at boundary 4 or 5 must appear, and the control must not (defect 38)."""

    rows = [
        row("full-5s", "R-forced", leak={"1": 1, "2": 1, "3": 1}, deep=True),
        row("full-5s", "R-forced", leak={"1": 4, "2": 1, "3": 1}, deep=True),
        row("full-5s", "C0-forced", leak={"1": None, "2": None, "3": None}, deep=True),
    ]
    print_batch_summary(rows, ["full-5s"])
    out = capsys.readouterr().out

    item1 = [ln for ln in out.splitlines() if ln.strip().startswith("item 1:")][0]
    # Two treated runs: one survived first at boundary 1, the other at boundary 4.
    assert "boundary1=1" in item1
    assert "boundary4=1" in item1 and "boundary5=0" in item1
    assert "sums to 2, n=2" in item1
    item2 = [ln for ln in out.splitlines() if ln.strip().startswith("item 2:")][0]
    # Both treated runs survived item 2 at boundary 1; the control is not in this table at all.
    assert "boundary1=2" in item2 and "never=0" in item2 and "sums to 2, n=2" in item2


def test_a_row_that_does_not_sum_to_n_says_so(capsys):
    """The "categories sum to n" rule is enforced here too, not only in the verdict scripts."""

    # A leak_index keyed on a boundary the table does not print: 0 means "first survived at
    # boundary 0", which the table has no column for, so the row cannot sum.
    rows = [row("full-5s", "R-forced", leak={"1": 0, "2": 1, "3": 1}, deep=True)]
    print_batch_summary(rows, ["full-5s"])
    out = capsys.readouterr().out

    assert "a boundary is missing from this row" in out


S3_BATCH = repo / "runs" / "apt_lab" / "chain-20261001-051211-full+full-5s"


@pytest.mark.skipif(not S3_BATCH.is_dir(), reason="the S-3 batch is not in this checkout")
def test_replays_the_s3_batch(capsys):
    """The real thing: the batch whose misleading summary motivated the fix."""

    import json

    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(S3_BATCH.glob("*.json"))]
    assert len(rows) == 24
    print_batch_summary(rows, ["full", "full-5s"])
    out = capsys.readouterr().out

    full_arm = [ln for ln in out.split("CHAIN RESULT (payload=full)")[1].splitlines()
                if ln.startswith("R-forced")][0].split()
    long_block = out.split("CHAIN RESULT (payload=full-5s)")[1]
    long_arm = [ln for ln in long_block.splitlines() if ln.startswith("R-forced")][0].split()
    # The numbers the old pooled line hid: 6 runs each, and they differ at stage 2.
    assert full_arm == ["R-forced", "5", "1", "4", "10", "6"]
    assert long_arm == ["R-forced", "6", "4", "3", "13", "6"]
    # Every leak row covers five boundaries in this arm and sums to the treated count. The
    # search has to be scoped to this payload's block: `full` is printed first and its rows
    # have three boundaries, so an unscoped "item 1:" search finds the wrong table -- which is
    # what this test did on its first run.
    for item in ("item 1:", "item 2:", "item 3:"):
        line = [ln for ln in long_block.splitlines() if ln.strip().startswith(item)][0]
        assert "boundary5=" in line and "sums to 6, n=6" in line
