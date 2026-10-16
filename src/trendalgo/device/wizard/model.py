"""Typed shape of a wizard step and of the official sources it relies on."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Source:
    """An official page a step relies on, and the date someone last checked it."""

    label: str
    url: str
    verified: date


@dataclass(frozen=True)
class Step:
    """One wizard step: a title, plain-language paragraphs, and sources for provider claims."""

    step_id: str
    title: str
    body: tuple[str, ...]
    sources: tuple[Source, ...] = ()
