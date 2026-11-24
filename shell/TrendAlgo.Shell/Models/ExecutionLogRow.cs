namespace TrendAlgo.Shell.Models;

/// <summary>Execution/timing log entry for scans, backtests, benchmarks, trades, and startup.</summary>
public sealed record ExecutionLogRow(
    string Time,
    string Kind,
    string Scope,
    string Duration,
    string Stages,
    string Summary);
