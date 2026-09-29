# Batch stopped part-way — D-1 treatment arm, 2026-09-29 11:31 UTC

**1 of 12 runs completed** (`R-forced-9501`, written 11:46 UTC), then the batch stopped. No
provider error was recorded: the driving job ended while the run was in flight (the runner
process is gone, and the session that owned the background job no longer has it). The
control batch of the same arms finished all 12 runs before it.

## What happens to the one run

It is **kept and counted** and will not be overwritten: the relaunch uses `--seed-base 9510`
rather than re-running 9500–9505. A same-seed rerun would produce a different run of the same
treatment and replace a completed one, which would make the arm's n depend on which attempt
happened to survive. So the treated arm becomes 1 (this batch) + 12 (the relaunch) = 13 runs,
and the control stays at 12 from `chain-20260929-085508-full`.

The asymmetry is recorded rather than smoothed: `repro/d1_verdict.py` prints both arm sizes
and marks any status resting on fewer runs than the registered 12 as preliminary.

## Why the comparison is still sound

D-1's treatment is the `--roles` switch, not the batch, and the verdict script classifies it
**per artifact** (`roles=true` vs `roles=false`). The 13 treated runs and the 12 control runs
were produced within a few hours of each other on the same endpoint, which is what the
pre-registration's "same hour, back to back" requirement was protecting against; that
requirement is now satisfied approximately rather than exactly, and the pre-registration's
§2 power argument (predicted effect ~1.3x against measured drift up to 2x) is unchanged.
