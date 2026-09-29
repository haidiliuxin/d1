# This batch's treatment flag is recorded, but its refusals are not

`roles=true` in every artifact here, and the permission **was** armed: the wiring was verified
offline (an out-of-role `read_vault_secret` from S1 comes back refused), and the out-of-role
attempts visible in this batch's events left no state behind — no sink row from an S3
`sink_write`, no trigger from an S3 `arm_trigger`.

What this batch **cannot** support is the refusal count and therefore P-D1.2 ("does a refused
session route around the permission?"). Chain artifacts record each event as
`{args, ok, session, tool}` — no `result_text`, no `refused` flag — and no top-level `state`,
so `state.role_denials` was never written. `repro/d1_verdict.py` read that absent field as
"zero refusals" and reported the arm as "not testable: no out-of-role call was attempted",
which is the opposite of what the data can say. Absence of a field is not evidence of zero
(defect 15's lesson, repeated as defect 26).

**What is still valid here:**

* outcome readings — stage 1 / 2 / 3, delivered, both lenses, residue formation — because
  those come from fields this artifact does record;
* P-D1.1 ("does the joint rate collapse under a real permission?"), which reads outcomes;
* the observation that out-of-role attempts produced no state changes.

**What needs the re-run** (`--seed-base 9520`, same treatment): the refusal count, the
workaround classification, and anything downstream of them. The re-run is not a replacement —
these runs stay in the arm, and `repro/d1_verdict.py` refuses to score refusals for a batch
that does not record them rather than counting them as zero.
