"""Entry point for `python -m trendalgo.device` and the frozen Windows build (D1).

`freeze_support()` runs first, so spawned pool workers never open a window.
"""

from __future__ import annotations

import argparse
import multiprocessing
import sys


def main(argv: list[str] | None = None) -> int:
    from trendalgo.device.env_bootstrap import ensure_device_env

    ensure_device_env()
    parser = argparse.ArgumentParser(prog="trendalgo-device", description="TrendAlgo device app.")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="check workers, WAL, and the profile lock, then exit",
    )
    parser.add_argument(
        "--smoke-backtest",
        metavar="PAIR",
        default=None,
        help="run one All-TA pair scan (e.g. BTC/USD) and print a row summary, then exit",
    )
    args = parser.parse_args(argv)
    testing = bool(args.selftest or args.smoke_backtest)
    if testing and sys.platform == "win32":
        # Windowed frozen builds have no console; attach one for the report.
        try:
            import ctypes

            ctypes.windll.kernel32.AllocConsole()
        except Exception:
            pass
    if args.selftest:
        from trendalgo.device.selftest import run_selftest

        return run_selftest()
    if args.smoke_backtest:
        from trendalgo.device.smoke_backtest import run_smoke_backtest

        return run_smoke_backtest(args.smoke_backtest)
    from trendalgo.device.console_detach import detach_console_if_needed

    detach_console_if_needed(testing=False)
    from trendalgo.device.app import run

    return run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    # Before any WorkerPool: hide spawn consoles (uv venv → base python.exe).
    from trendalgo.device.spawn_no_console import install_spawn_no_console

    install_spawn_no_console()
    sys.exit(main())
