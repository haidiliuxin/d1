# Batch failed to start — `deepseek-chat` arm, 2026-09-28 10:21 UTC

**Zero artifacts.** The batch directory was created, then the very first model call of the
first replicate raised and the process exited before any run completed. Nothing was
measured, so this batch is not evidence about anything and is excluded from every pool by
construction (`runs_of` yields nothing for it, and the inventory skips batches with no
runs).

## What broke

```
openai.UnprocessableEntityError: Error code: 422
  Failed to deserialize the JSON body into the target type:
  messages[0].role: unknown variant `developer`, expected one of `system`, `user`,
  `assistant`, `tool`, `latest_reminder`
```

AgentDojo's OpenAI wrapper (`agentdojo/agent_pipeline/llms/openai_llm.py`) maps a **system**
message to OpenAI's newer **`developer`** role. `MiniMax-M2.7` accepts that role (verified:
the same request against MiniMax returns a model error, not a role error). DeepSeek rejects
the request outright.

## Fix, and why it is opt-in

`lab_v0.apt_lab.usage.rewrite_roles` rewrites `developer` -> `system` on the wire, enabled by
the new `role_compat` flag that `chain.py` sets **only** for a non-MiniMax `--base-url`. It
is deliberately not always-on: switching the frozen arm's wire format would make new
MiniMax runs incomparable with the published pool for a reason that has nothing to do with
the mechanism under test. The flag is recorded per artifact as `role_compat`.

Two-direction check (one real model call each, `repro`-free probe):
`role_compat=False` -> 422, reproducing this failure; `role_compat=True` -> OK, 4597 tokens.

Protocol amendment registered in `docs/experiments/2026-09-28-cross-model-prereg.md` §9.
