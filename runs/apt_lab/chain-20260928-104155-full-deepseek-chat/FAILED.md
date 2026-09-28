# Batch stopped part-way — DeepSeek top-up, 2026-09-28 10:41 UTC

**4 of 12 runs completed** (R-forced seeds 9310–9313), then the provider returned:

```
openai.APIStatusError: Error code: 402
  {'error': {'message': 'Insufficient Balance'}}
```

The DeepSeek account ran out of credit. Unlike the four MiniMax 429s (a rolling plan window
that recovers), this one does not recover on its own: it needs the account to be topped up.

## What happens to the four runs

They are **kept and counted**. They are valid runs of the registered treatment (same host,
same payload, same policy, same model, `role_compat` on), written to disk complete and
individually verified:

* all four left a review record and all four residues held the payload at boundary 1
* boundary coverage 1.0, complete, on all 12 boundaries
* `leak_index` `{1: 1, 2: 1, 3: 1}` in each — the wholesale pattern, as on MiniMax

So they extend the R arm from 6 to **10** runs. The arm is still short of the 12 the
top-up was for, and the verdict script marks every status preliminary on that basis
(`repro/c1_verdict.py` prints the arm size and asterisks anything below it).

## Why this is recorded rather than deleted

A batch that is missing from the directory is indistinguishable from one that never ran, and
"4 runs, then the provider ran out of money" is a fact about the evidence that a reader
needs: it explains why the R arm is 10 and the control arm 6, and it stops a later reader
from assuming the asymmetry was a design choice.
