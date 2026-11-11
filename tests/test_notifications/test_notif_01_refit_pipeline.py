"""NOTIF-01: journal-first refit notify; dead sink still completes retune."""

from __future__ import annotations

from trendalgo.notifications.refit_pipeline import RefitNotifyPipeline, SinkResult


class DeadSink:
    name = "ntfy"

    def send(self, _title: str, _body: str) -> SinkResult:
        raise RuntimeError("unreachable")


class FlakyThenOk:
    name = "telegram"

    def __init__(self) -> None:
        self.calls = 0

    def send(self, _title: str, _body: str) -> SinkResult:
        self.calls += 1
        if self.calls < 2:
            return SinkResult(ok=False, detail="timeout")
        return SinkResult(ok=True, detail="sent")


def test_dead_sink_journals_and_completes_retune() -> None:
    journal: list[dict[str, object]] = []
    pipe = RefitNotifyPipeline(
        journal_append=journal.append,
        sinks=[DeadSink()],
        sleep_fn=lambda _s: None,
        max_attempts=2,
        backoff_seconds=(0.0, 0.0),
    )
    result = pipe.notify_after_retune(
        event="refit_proposed",
        title="proposed",
        body="evidence",
        retune_completed=True,
    )
    assert result.retune_completed is True
    assert len(journal) == 1
    assert journal[0]["event"] == "refit_proposed"
    assert result.deliveries[0].ok is False


def test_retry_backoff_then_success() -> None:
    journal: list[dict[str, object]] = []
    flaky = FlakyThenOk()
    pipe = RefitNotifyPipeline(
        journal_append=journal.append,
        sinks=[flaky],
        sleep_fn=lambda _s: None,
        max_attempts=3,
        backoff_seconds=(0.0, 0.0, 0.0),
    )
    result = pipe.notify_after_retune(
        event="refit_promoted",
        title="promoted",
        body="shadow ok",
        retune_completed=True,
    )
    assert flaky.calls == 2
    assert result.deliveries[0].ok is True
    assert len(journal) == 1
