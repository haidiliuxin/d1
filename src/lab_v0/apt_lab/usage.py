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

#: Roles a provider may not know. AgentDojo's OpenAI wrapper maps a system message to
#: OpenAI's newer `developer` role; MiniMax accepts it, DeepSeek rejects the whole request
#: (`unknown variant 'developer'`), so a cross-provider arm cannot start at all. The
#: rewrite is *opt-in per endpoint* rather than always-on, because switching the frozen
#: arm's wire format would make its runs incomparable with the published pool for a reason
#: that has nothing to do with the mechanism.
ROLE_ALIASES = {"developer": "system"}


def blank_usage() -> dict[str, int]:
    return {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def rewrite_roles(messages: Any) -> int:
    """Apply `ROLE_ALIASES` in place. Returns how many messages were changed."""

    if not isinstance(messages, list):
        return 0
    changed = 0
    for message in messages:
        try:
            alias = ROLE_ALIASES.get(message.get("role"))
        except AttributeError:
            continue
        if alias is not None:
            message["role"] = alias
            changed += 1
    return changed


class _Completions:
    def __init__(self, real: Any, sink: dict[str, int], role_compat: bool = False) -> None:
        self._real = real
        self._sink = sink
        self._role_compat = role_compat
        #: How many messages this run had to have their role rewritten for. Recorded so
        #: that "this arm ran on a slightly different wire format" is visible in the data
        #: rather than only in a commit message.
        self.role_rewrites = 0

    def create(self, *args: Any, **kwargs: Any) -> Any:
        if self._role_compat:
            self.role_rewrites += rewrite_roles(kwargs.get("messages"))
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
    def __init__(self, real: Any, sink: dict[str, int], role_compat: bool = False) -> None:
        self._real = real
        self.completions = _Completions(real.completions, sink, role_compat)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class UsageRecordingClient:
    """An OpenAI client that counts what the run spends.

    Delegation is lazy (`__getattr__`), so anything the underlying client exposes --
    `base_url` included -- keeps working.
    """

    def __init__(self, real: Any, sink: dict[str, int] | None = None, *,
                 role_compat: bool = False) -> None:
        self._real = real
        self.usage: dict[str, int] = sink if sink is not None else blank_usage()
        self.chat = _Chat(real.chat, self.usage, role_compat)

    @property
    def role_rewrites(self) -> int:
        return self.chat.completions.role_rewrites

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def summarise(usages: list[dict[str, int]]) -> dict[str, int]:
    """Add up per-run usage, for the batch report."""

    total = blank_usage()
    for u in usages:
        for key in total:
            total[key] += int(u.get(key, 0))
    return total
