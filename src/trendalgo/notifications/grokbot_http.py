"""HTTPS webhook POST that never follows redirects (sender key stays put)."""

from __future__ import annotations

import urllib.request
from typing import Any


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """3xx is failure. Do not copy Authorization onto a Location hop."""

    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


def urlopen(req: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout)
