"""Token accounting for a run, without patching the benchmark.

The AgentDojo LLM wrapper builds its completion with `client.chat.completions.create(...)`
and then keeps only `completion.choices[0].message`; `completion.usage` is discarded. Cost
therefore cannot be reconstructed after the fact, which matters the moment a study scales
to hundreds of runs.

The fix is a proxy *client* rather than a patched wrapper: `OpenAILLM` only reads
`base_url` (for its temperature floor) and calls `chat.completions.create`, so an object
that delegates and counts is enough -- and the upstream checkout stays untouched, which
also means a later `git pull` there cannot silently drop the measurement.

`str(getattr(client, "base_url", ""))` is delegated on purpose: the wrapper's MiniMax
temperature fix keys on it, so a proxy that hid `base_url` would quietly change the
temperature and therefore the experiment.
"""

from __future__ import annotations

from typing import Any


def blank_usage() -> dict[str, int]:
    return {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class _Completions:
    def __init__(self, real: Any, sink: dict[str, int]) -> None:
        self._real = real
        self._sink = sink

    def create(self, *args: Any, **kwargs: Any) -> Any:
        response = self._real.create(*args, **kwargs)
        usage = getattr(response, "usage", None)
        if usage is not None:
            self._sink["calls"] += 1
            self._sink["prompt_tokens"] += int(getattr(usage, "prompt_tokens", 0) or 0)
            self._sink["completion_tokens"] += int(
                getattr(usage, "completion_tokens", 0) or 0
            )
            self._sink["total_tokens"] += int(getattr(usage, "total_tokens", 0) or 0)
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class _Chat:
    def __init__(self, real: Any, sink: dict[str, int]) -> None:
        self._real = real
        self.completions = _Completions(real.completions, sink)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class UsageRecordingClient:
    """An OpenAI client that counts what the run spends.

    Delegation is lazy (`__getattr__`), so anything the underlying client exposes --
    `base_url` included -- keeps working.
    """

    def __init__(self, real: Any, sink: dict[str, int] | None = None) -> None:
        self._real = real
        self.usage: dict[str, int] = sink if sink is not None else blank_usage()
        self.chat = _Chat(real.chat, self.usage)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def summarise(usages: list[dict[str, int]]) -> dict[str, int]:
    """Add up per-run usage, for the batch report."""

    total = blank_usage()
    for u in usages:
        for key in total:
            total[key] += int(u.get(key, 0))
    return total
