# Avalonia shell + Research Engine packaging (ADR-0021)

## Layout

| Path | Role |
|------|------|
| `shell/TrendAlgo.Shell/` | C# Avalonia desktop chrome (net8.0) |
| `src/trendalgo/` | Permanent Python Research Engine |
| `src/trendalgo/results_store/` | `results.db` schema + IPC handshake |
| Profile `~/.trendalgo/device/` | Shared `results.db`, `engine_ipc.json`, CredMan unchanged |

## Dev loop

```powershell
# Seed IPC + demo strategy rows
uv run python -m trendalgo.results_store --demo

# Build shell
dotnet build shell/TrendAlgo.Shell.sln -c Release

# Run shell (reads profile results.db)
dotnet run --project shell/TrendAlgo.Shell -c Release
```

PySide6 device remains the production GUI until inventory P0 parity is ✅.

## Official build contract

1. Pin **shell** assembly version ↔ **engine** `trendalgo-bot` version in release notes.
2. Handshake: `engine_ipc.json` `protocol_version=1`, `schema_version>=1`.
3. Bundle engine with `scripts/packaging/bundle-research-engine.ps1` into the shell publish folder.
4. Tri-OS publish helper:

```powershell
.\scripts\packaging\publish-avalonia-shell.ps1 -Rid win-x64
.\scripts\packaging\publish-avalonia-shell.ps1 -Rid all   # win-x64 + linux-x64 + osx-arm64
```

Outputs under `dist/shell/<rid>/` with `engine/` staged beside the shell.

## Non-goals

Do not ask end users to install Python themselves for official builds. Do not reimplement All-TA in C#.
