# Feature: Avalonia dual-runtime (ADR-0021)

## Goal

Ship C# Avalonia desktop chrome with a permanent Python Research Engine. Shared `results.db` + versioned IPC. PySide6 stays shippable until inventory P0 parity is complete.

## Acceptance

- [x] ADR-0021 accepted
- [x] `src/trendalgo/results_store/` schema v1 + progressive strategy writes + handshake
- [x] `shell/TrendAlgo.Shell` Workbook DataGrid reads `results.db`
- [x] Nav stubs for inventory §12 + P1/P2 hooks
- [x] `scripts/packaging/bundle-research-engine.ps1` + packaging doc
- [ ] Full page parity (sequential follow-on BUILD_PLAN rows)
- [ ] Tri-OS official installers with frozen engine

## Validation

```bash
uv run pytest tests/test_results_store.py tests/test_device/test_device_profile.py tests/test_device/test_device_data_path.py -q --tb=short --no-cov
dotnet build shell/TrendAlgo.Shell.sln -c Release
uv run python -m trendalgo.results_store --demo
```

## Fallback

If Avalonia build fails on a machine without .NET 8 SDK, engine contract tests alone still gate the Python side.
