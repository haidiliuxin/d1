# Batch failed to start — MiniMax same-time reference, 2026-09-28 10:21 UTC

**Zero artifacts.** The batch directory was created, then the first model call raised and
the process exited before any run completed. Nothing was measured; the provider's plan cap
was hit before a single session ran.

## What broke

```
openai.RateLimitError: Error code: 429
  {'error': {'type': 'rate_limit_error',
             'message': '已达到 Token Plan 用量上限 … (2056)'}}
```

This is the fourth 429 of the campaign and the first that killed a batch on its **first**
call. The earlier three arrived part-way through a batch (a rolling window cap that
recovered within the hour); this one is the plan's usage ceiling for the current window.
Two concurrent k=4 batches had been started; one call from a diagnostic probe also
contended for the same window.

## Consequence for the registered design

The cross-model pre-registration (`docs/experiments/2026-09-28-cross-model-prereg.md`) asked
for a same-time MiniMax reference batch so that batch drift (measured up to 2x) could not
masquerade as a model difference. That reference is **deferred**, not cancelled: the
comparison it guards is the *descriptive* cross-model contrast, and none of the four
registered predictions depends on it -- P-C1.1 (residue formation >= 8/12), P-C1.2
(stage3_delivered <= 4/12), P-C1.3 (joint == persistence, internal to the arm), P-C1.4
(control clean) are all absolute or internal to the model under test. No cross-model
significance test was registered at n=12.

Registered amendment §9 records this and the launch-failure fix together, before any data
from the arm existed.
