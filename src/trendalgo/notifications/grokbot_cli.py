"""Send a Grok Bot webhook test event: ``python -m trendalgo.notifications.grokbot_cli``."""

from __future__ import annotations

import json
import sys

from trendalgo.notifications.grokbot import public_status, send_test


def main(argv: list[str] | None = None) -> int:
    del argv  # reserved for future flags
    status = public_status()
    result = send_test(wait=True)
    print(json.dumps({"status": status, "result": result}, indent=2, sort_keys=True))
    return 0 if result.get("sent") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
