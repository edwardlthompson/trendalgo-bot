"""Advisory go-live readiness: ``python -m trendalgo.notifications.golive_cli``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from trendalgo.notifications.grokbot_golive import emit_golive_readiness, report_from_env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Advisory dry-run readiness. Does not approve live or bypass go-live-gate.sh."
    )
    parser.add_argument(
        "--emit", action="store_true", help="also POST golive_readiness to Grok Bot"
    )
    args = parser.parse_args(argv)
    data = Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))
    if args.emit:
        out = emit_golive_readiness(data_dir=data, wait=True)
    else:
        out = {"report": report_from_env(data), "emit": None}
    print(json.dumps(out, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
