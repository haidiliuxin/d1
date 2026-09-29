# Mis-launched probe: only the control payload ran

This batch was meant to be E-1's mechanism probe — `full` against `full-r2`, interleaved — but
it was launched with `--seeds 1`, and the job list assigns
`variant_names[replicate % len(variant_names)]`. With a single replicate only the first payload
was ever used, so both runs here are `full`: **no `full-r2` run exists in this batch**, and it
cannot say anything about redundancy.

Recorded rather than deleted so that a later reader does not count it as a probe that found
nothing. `repro/e1_verdict.py` already ignores it: the control arm is restricted to batches
that hold *both* payloads, precisely so that a same-day treatment is never compared against a
multi-day baseline — and this batch holds only one.

The probe was re-run with `--seeds 6` (three replicates per payload per arm).
