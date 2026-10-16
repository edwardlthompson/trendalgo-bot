"""Content lint for the wizard: no asks for secrets, official https sources, and required wording.

Each rule traces to a register item: W-SAFE (no secrets asked), W-LABEL and W-COST (sources and
dates), W-OCI3, W-OCI5, and W-OCI6 (region, budget, and upgrade wording), and W-KEY (permissions).
`lint` returns the problems it finds, and an empty list passes.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from urllib.parse import urlsplit

from trendalgo.device.wizard.model import Source, Step

OFFICIAL_HOSTS = frozenset(
    {"www.oracle.com", "docs.oracle.com", "www.kraken.com", "docs.kraken.com", "support.kraken.com"}
)
FORBIDDEN_ASKS = ("password", "seed phrase", "card number", "withdrawal address", "2fa code")
NEGATION = re.compile(r"\b(never|not|no|don't|do not)\b", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
STEP_ID = re.compile(r"^W\d+$")
REQUIRED_STEPS = ("W0", "W1", "W2", "W3", "W4", "W5")
SOURCED_STEPS = frozenset({"W1", "W3"})
REQUIRED_WORDING: dict[str, tuple[str, ...]] = {
    "W0": ("shadow mode",),
    "W1": ("Withdraw Funds",),
    "W3": ("home region", "2 OCPUs", "12 GB", "24 hours", "Path B", "static"),
    "W4": ("10 minutes", "fingerprint"),
}


def _asks_for_secret(sentence: str) -> bool:
    """True when a sentence names a secret without saying it must never be shared."""
    lowered = sentence.lower()
    return any(term in lowered for term in FORBIDDEN_ASKS) and not NEGATION.search(sentence)


def _step_problems(step: Step) -> list[str]:
    problems: list[str] = []
    if not step.title.strip():
        problems.append(f"{step.step_id}: empty title")
    if not step.body or any(not paragraph.strip() for paragraph in step.body):
        problems.append(f"{step.step_id}: empty paragraph")
    for paragraph in step.body:
        for sentence in SENTENCE_END.split(paragraph):
            if _asks_for_secret(sentence):
                problems.append(f"{step.step_id}: asks for a secret: {sentence!r}")
    text = " ".join(step.body)
    for phrase in REQUIRED_WORDING.get(step.step_id, ()):
        if phrase not in text:
            problems.append(f"{step.step_id}: missing required wording {phrase!r}")
    if step.step_id in SOURCED_STEPS and not step.sources:
        problems.append(f"{step.step_id}: provider claims need a source")
    return problems


def _source_problems(step_id: str, source: Source) -> list[str]:
    problems: list[str] = []
    if not source.label.strip():
        problems.append(f"{step_id}: a source has no label")
    parts = urlsplit(source.url)
    if parts.scheme != "https":
        problems.append(f"{step_id}: source {source.label!r} must use https")
    if (parts.hostname or "") not in OFFICIAL_HOSTS:
        problems.append(f"{step_id}: source {source.label!r} is not on the official list")
    return problems


def lint(steps: Sequence[Step]) -> list[str]:
    """Return the problems in the wizard content. An empty list means the content passes."""
    problems: list[str] = []
    seen: set[str] = set()
    for step in steps:
        if not STEP_ID.match(step.step_id):
            problems.append(f"{step.step_id!r}: step ids look like W0, W1, and so on")
        if step.step_id in seen:
            problems.append(f"{step.step_id}: duplicate step id")
        seen.add(step.step_id)
        problems.extend(_step_problems(step))
        for source in step.sources:
            problems.extend(_source_problems(step.step_id, source))
    for step_id in REQUIRED_STEPS:
        if step_id not in seen:
            problems.append(f"{step_id}: step is missing")
    return problems
