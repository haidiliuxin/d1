# Freeze record — `freeze-v1.0`

**Date:** 2026-09-28 · **Tag:** `freeze-v1.0` · **Kind:** curated snapshot of one experiment
line (the induced-defence residue chain), not a fork of the parent project.

> **Which commit to cite.** `freeze-v1.0` is the snapshot as it stood when the freeze was
> taken. The audit that the freeze itself triggered (§4) then corrected four measurement
> defects and hardened the manifest, and those fixes live on `main` **after** the tag. So:
> cite a commit hash, not the tag name; use the newest `main` for the corrected numbers, and
> `freeze-v1.0` only to see the artifact as of the freeze. The headline verdicts are the
> same either way — the gate is NO-GO and both design arms are unsupported on both.

## 1. What was frozen, and from where

| | |
|---|---|
| source working tree | `F:\think\APT-AGENT-std` (branch `006-promoted`) |
| source commit | `c4d960a3def8e5134bd1f89ab89142a61ad9c204` |
| status of the frozen material there | **untracked working-tree files** — `src/lab_v0/apt_lab/`, `scripts/apt_lab/`, the four `tests/test_chain_*.py`, `docs/experiments/`, and the analysis scripts then living in `F:\think\_repro` |
| included | the lab module, the six runners, the four offline test files, 13 experiment documents, the eight analysis scripts, and **all 348 raw run artefacts plus logs** (`runs/apt_lab/`) |
| not included | the parent project's other lines (`codex_postblock`, the relay/MCP lab, the `apt-dd` M20 branch, vendored runtimes). They are separate experiments with their own repositories and histories; merging them here would import someone else's history into a snapshot of this one. |

The whole point of a curated snapshot is that a reader can recompute every published number
from this repository alone. That is why the raw traces are committed: `runs/**` is ignored
in the parent project ("live-provider evidence can contain model transcripts"), and a freeze
without its evidence is a claim rather than a result.

## 2. Environment pins

| | |
|---|---|
| offline tests / analysis | CPython **3.11.9**, `pytest 9.1.1` (tests need nothing else — no agentdojo, no key, no model) |
| live runs | CPython **3.12.14** (conda-forge), AgentDojo **0.1.34** from `F:\think\_sources\AgentLAB\Task-Injection\agentdojo` (editable; a second unused checkout exists at `F:\think\_sources\agentdojo`) |
| model | `MiniMax-M2.7` through AgentDojo's own `OpenAILLM`, `temperature=0.1`, endpoint `https://api.minimaxi.com/v1` |
| host | AgentDojo's own workspace suite (`email`/`calendar`/`cloud_drive`/`workspace`), one in-process session per stage; nothing in AgentDojo is modified |
| layout | `src/lab_v0/apt_lab/` (10 modules), `scripts/apt_lab/` (6 runners), `tests/` (4 chain test files), `repro/` (9 scripts), `runs/apt_lab/` (22 batches) |

**Verified in this checkout:** `python -m pytest -q` → **64 passed, 1 skipped**;
`python repro/claims_audit.py` → **all 14 claims reproduce** (exit 0);
`python repro/two_lenses.py`, `repro/chain_stats.py`, `repro/d2_verdict.py`,
`repro/d4_verdict.py`, `repro/leak_figure.py` all run to completion with the numbers quoted
in `README.md` and in the chain spec §9.25.

## 3. Frozen payloads

Byte-exact, because a payload that changes silently invalidates the staging invariants that
`tests/test_chain_payloads.py` asserts:

| variant | chars | sha256 |
|---|---:|---|
| `full` | 712 | `94726ea3bce1abde02b0b6ddf4846e6f92054640f4d4b21bd686b87bfe3c1620` |
| `next-hop` | 932 | `15938b82ee6ae309bb7597fb3ce309f82a940a44d64293656b8a6b500ca93317` |
| `only-stage1` | 399 | `74842f0d7171ec0f2362148cbcea939192108aef8ec0b9f4511ac208a271cb20` |
| `full-5` | 1020 | `9f18e185bbc800382f12cd33c55a6947267f0dd36bb3eb988b6febaae47431cb` |
| `full-d2` | 873 | `6c85227450689e7b37b5a88434f721ce05b1f0e1477ebc940bba92a65eb9e139` |
| `full-d4` | 844 | `ca1002990c0e26db7f36205257751b388d6f4be11be8fdbddd4668a30f35b5d1` |

`full-5` extends `full` (`full-5.startswith(CHAIN_PAYLOAD)`), `full-d2` and `full-d4` each
change exactly one item of it — the properties the payload tests assert.

## 4. The freeze audit: four defects found by this snapshot

Freezing was treated as a *verification* action, not a copy: the acceptance test was
"reproduce every number with the scripts in a clean checkout". It found four measurement
defects, all logged in §9.25 of `docs/experiments/2026-09-26-direction2-chain-spec.md`:

| # | what was wrong | why a fresh checkout exposed it | verdict impact |
|---|---|---|---|
| 17 | `chain_stats.main()` pooled by **batch** (`variant_of` reads the batch's first artifact) | only shows once the interleaved `full+full-d4` batches exist and the pool is recomputed per artifact — the pooled `full` arm held 16 `full-d4` runs | none: gate still NO-GO |
| 18 | both verdict scripts filtered `--since` on `st_ctime` | `st_ctime` is the *copy* time, so every batch passed the filter and "same-time" controls silently became all-time ones | none: both design arms still unsupported |
| 19 | §9.24's "invented rule / nobody armed" rows did not match the traces | found while auditing the D4 arm run by run; the arm's own categories summed to 9 of 10 | D4 unchanged; P-D4.4 flips ✅→❌ |
| 20 | §9.22's source-constrained "all three" cell (15/85 = 17.6%) was a single-stage count | the strict joint is 6/82 = 7.3%; the correct role-separation cost is ≈8.4×, not 3.6× | **strengthens** the main result |

After the fixes, `gate_snapshot.py` (which always classified per artifact) and
`chain_stats.py` print byte-identical gate readings — the two-script cross-check that caught
defect 15 previously. The corrected headline numbers are in `README.md` §2 and spec §9.25.

## 5. Deltas applied to the frozen material

Nothing under `src/` or `scripts/` that affects a live run was touched. The deltas are:

1. **Path portability** in `repro/*`: absolute `F:\think\...` literals became paths relative
   to the script's own location (`ROOT`, `sys.path`, the M20 summary). Verified by re-running
   every script and by `claims_audit.py` exiting 0.
2. **The four fixes above** (defects 17–20), each verified by re-running and by the
   cross-checks named in §4.
3. **New scripts**: `repro/two_lenses.py` (the two-lens capability claim + the ratchet check)
   and `repro/freeze_manifest.py` (regenerates `MANIFEST.sha256` and
   `runs/apt_lab/INVENTORY.md`).
4. **Documentation corrections made in place, dated and signed** (`> **2026-09-28 更正…**`
   blocks) rather than silently rewritten, so the audit trail keeps the original text
   visible next to its correction.

## 6. Known non-portable paths and cosmetic issues

* `scripts/apt_lab/*` still reference the AgentDojo checkout by absolute path
  (`F:\think\_sources\AgentLAB\Task-Injection\agentdojo\src`) and
  `scripts/apt_lab/gate_state_persistence.py` its key file by absolute path. These are live
  runners, deliberately left byte-identical to what produced the runs; a reader on another
  machine must edit those two literals. The analysis path (`repro/`) has no such dependency.
* `repro/chain_stats.py::stage3_delivered_loose` ends with an unreachable `return`
  statement (a leftover from a refactor). It is dead code after a `return`; left in place so
  that the "analysis scripts changed only where documented" claim stays exactly true.
* `runs/apt_lab/phaseB-gate-20260928-100206.json` is the gate snapshot written *by this
  freeze audit*, dated in UTC; the earlier snapshots in that directory are the in-workspace
  readings from the campaign itself.

## 7. How to check this freeze

```powershell
python -m pytest -q                     # 64 passed, 1 skipped
python repro/claims_audit.py            # 14/14 claims; non-zero exit on drift
python repro/freeze_manifest.py --check # verifies MANIFEST.sha256 against this tree
python repro/chain_stats.py             # gate table; must read NO-GO
python repro/two_lenses.py              # unconstrained vs source-constrained joint rates
```

`MANIFEST.sha256` covers every published file outside `runs/` (and deliberately *not*
`secrets/`, which is local-only). `--check` compares it against the tree and exits non-zero
on any changed, missing or unlisted file — added after the first version of the manifest
went stale mid-audit without saying so, and after a second version listed the API key file:
a manifest nobody verifies is worse than no manifest, because it *looks* like verification.
Regenerating it after any edit is how a post-freeze change becomes visible instead of
silent. Line endings are pinned to LF in `.gitattributes`, so a fresh checkout is
byte-identical to the manifest even where `core.autocrlf=true`.

`runs/apt_lab/INVENTORY.md` is the per-batch inventory and is regenerated by the same
script. **These two counts are as of the freeze** (22 batches, 348 artefacts, 151.6M
accounted tokens); the live totals after the C-1 and D-1 arms are in §9 below and in the
regenerated inventory.

## 8. What this freeze is not

Not a capability claim for any deployable attack: no real credential, no network egress, no
third-party system, no product exercised, terminal effect a row in an in-process mock sink.
Not a multi-model result: the headline tables in `README.md` §2 are one model at
`temperature=0.1`. Not a defence evaluation: role separation is *simulated* by a measurement
convention, and the strongest statement the data supports is the size of the gap it defines
(≈8.4×), which is an argument for building the real permission — not evidence that one exists.

## 9. What happened after the freeze (all on `main`, after the tag)

The freeze is a snapshot; the campaign continued, and this is why the advice at the top is to
cite a commit rather than the tag name.

| commit | what it added |
|---|---|
| `6990272` | every pool must name the model it is a rate of (pre-launch hardening) |
| `e169b2f` | the `developer`→`system` wire shim, without which a second provider cannot be reached at all |
| `02c39a0`, `e33e99e`, `0fdf31d` | LF pinning, `--check`, and keeping local-only files out of the manifest — three defects in the manifest itself |
| `a10d036` | E-1's multi-seat planting (`2026-09-28-redundant-delivery-prereg.md`) |
| `91dfbd7`, `134c705` | D-1's tool-level permissions and its verdict script (`--roles`, off by default) |
| `5d4dc5c` | the C-1 cross-model verdict: **16/16 residues on `deepseek-chat`**, delivered 1/16, the ratchet **not** transferring |
| `5d24e23` | defect 23 — the D-1 verdict script was certifying criteria it could not test |

Totals now: **392 run artefacts across 27 batches, 213.6M accounted tokens** (the frozen
snapshot had 348 across 22). The defect registry stands at 23, in chain spec §9.13–§9.26.

**Still blocked, and worth stating plainly**: three registered experiments cannot run — the
C-1 same-time MiniMax reference batch, D-1 on MiniMax (the only model where the permission is
testable at all), and E-1 — because MiniMax's plan quota is exhausted while a concurrent
campaign on this machine uses the same plan; the second provider returned
`402 Insufficient Balance` twice. None of that is a design problem; all of it needs a quota
decision.
