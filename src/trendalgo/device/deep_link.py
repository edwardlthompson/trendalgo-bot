"""Parse device deep links into Settings → About → Feedback with a sanitized subject."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

from trendalgo.device.privacy_report.sanitize import sanitize_report_text


@dataclass(frozen=True)
class FeedbackDeepLink:
    kind: str  # bug | feature
    subject: str


def parse_feedback_deep_link(raw: str | None) -> FeedbackDeepLink | None:
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    if "://" not in text and text.startswith("settings/"):
        text = f"trendalgo://app/{text}"
    try:
        parts = urlparse(text)
    except ValueError:
        return FeedbackDeepLink("bug", "")
    combined = f"{parts.netloc}{parts.path or ''}".lower().replace("//", "/").strip("/")
    if "settings/about/feedback" not in combined:
        return None
    query = parse_qs(parts.query)
    subject_raw = ""
    for key in ("subject", "text", "description", "title"):
        vals = query.get(key)
        if vals and vals[0]:
            subject_raw = unquote(vals[0])
            break
    kind = "feature" if query.get("kind", [""])[0].lower() == "feature" else "bug"
    return FeedbackDeepLink(kind, sanitize_report_text(subject_raw))


def feedback_link_from_argv(argv: list[str]) -> FeedbackDeepLink | None:
    for arg in argv[1:]:
        if "feedback" in arg.lower() or arg.startswith("trendalgo:"):
            parsed = parse_feedback_deep_link(arg)
            if parsed is not None:
                return parsed
    return None
