# MISLAUNCHED — output truncation killed this batch after 2 of 24 runs

**Do not pool these two artifacts as M-1a. It is not a batch.**

## What happened

The batch was launched through a PowerShell pipeline that truncates:

```powershell
python run_m1a.py 2>&1 | Select-Object -First 24
```

`Select-Object -First N` stops the pipeline once N objects have passed, and PowerShell then
terminates the upstream command. `run_m1a.py` had produced exactly 24 lines — two runs' worth —
when the producer was killed. Seeds 9991 and 9993 (the SMS-seat replicates that started in the
same k=4 wave) died mid-run and wrote no artifact.

**Two artifacts exist, of twenty-four.** They are valid runs of the treatment; the batch is not
a batch, and the difference matters because M-1a's cells are six runs per seat per arm.

## The lesson, which is the reason this file exists

The live probe was launched through the *same* pipeline with `-First 30` and completed normally —
only because its output was shorter than the limit. So the launch path was broken before the
probe ran, and the probe's success said nothing about it.

A launch path that truncates output is a path that can silently kill a run, and the failure is
invisible from inside: the artifacts that exist look fine. What catches it is counting artifacts
against the registered cell size — which is exactly the check `repro/m1_verdict.py` performs
before it judges anything, and `repro/freeze_manifest.py` reports per batch.

Recorded as defect 42 in the chain spec's ledger. The relay is relaunched into a fresh directory
with `--seeds 12` and the same seed base: seeds are labels rather than RNG seeds
(`chain.py --seed-base` help), so the same seeds describe the same treatment.
