"""Token accounting has to be two-directional too.

Two ways to get it wrong, both of which would produce a confident cost figure for a
study that is about to spend real money:

* **Counting nothing.** If the proxy does not sit in the call path the wrapper actually
  uses, usage stays at zero and reads as "free".
* **Breaking the thing it wraps.** The wrapper keys its MiniMax temperature floor on
  `client.base_url`. A proxy that swallowed that attribute would silently change the
  sampling temperature -- an accounting change that alters the experiment.
"""

from __future__ import annotations

from types import SimpleNamespace

from lab_v0.apt_lab.usage import UsageRecordingClient, blank_usage, summarise


class FakeCompletions:
    def __init__(self, usage: object | None = None) -> None:
        self.calls: list[dict] = []
        self._usage = usage

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[object()], usage=self._usage)


def fake_client(usage: object | None = None, base_url: str = "https://api.minimaxi.com/v1"):
    completions = FakeCompletions(usage)
    return (
        SimpleNamespace(
            chat=SimpleNamespace(completions=completions), base_url=base_url
        ),
        completions,
    )


def test_usage_is_counted_from_the_call_the_wrapper_makes():
    real, completions = fake_client(
        SimpleNamespace(prompt_tokens=120, completion_tokens=30, total_tokens=150)
    )
    client = UsageRecordingClient(real)
    client.chat.completions.create(model="m", messages=[])
    client.chat.completions.create(model="m", messages=[])
    assert client.usage == {
        "calls": 2, "prompt_tokens": 240, "completion_tokens": 60, "total_tokens": 300,
    }
    assert len(completions.calls) == 2


def test_a_response_without_usage_counts_as_a_call_but_adds_no_tokens():
    real, _ = fake_client(None)
    client = UsageRecordingClient(real)
    client.chat.completions.create(model="m", messages=[])
    assert client.usage == blank_usage()


def test_the_proxy_keeps_base_url_visible():
    """The wrapper reads this to decide whether to floor the temperature at 0.1."""

    real, _ = fake_client(base_url="https://api.minimaxi.com/v1")
    client = UsageRecordingClient(real)
    assert str(client.base_url) == "https://api.minimaxi.com/v1"
    assert "minimax" in str(client.base_url).lower()


def test_the_proxy_passes_arguments_through_unchanged():
    real, completions = fake_client(
        SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)
    )
    client = UsageRecordingClient(real)
    client.chat.completions.create(model="MiniMax-M2.7", messages=[{"role": "user"}], temperature=0.1)
    assert completions.calls[0] == {
        "model": "MiniMax-M2.7", "messages": [{"role": "user"}], "temperature": 0.1
    }


def test_summarise_adds_up_runs():
    assert summarise([blank_usage(), {"calls": 2, "prompt_tokens": 10,
                                      "completion_tokens": 5, "total_tokens": 15}]) == {
        "calls": 2, "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
    }


def test_the_proxy_can_share_one_sink_across_runs():
    sink = blank_usage()
    for _ in range(3):
        real, _ = fake_client(
            SimpleNamespace(prompt_tokens=5, completion_tokens=5, total_tokens=10)
        )
        client = UsageRecordingClient(real, sink)
        client.chat.completions.create(model="m", messages=[])
    assert sink["calls"] == 3 and sink["total_tokens"] == 30
