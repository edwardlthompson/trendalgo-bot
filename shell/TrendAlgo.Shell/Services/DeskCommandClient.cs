using System.Diagnostics;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace TrendAlgo.Shell.Services;

/// <summary>Enqueue Crypto/TradFi/Forex strip actions into the Python engine queue.</summary>
public sealed class DeskCommandClient
{
    private readonly string _repoRoot;

    public DeskCommandClient(string? repoRoot = null)
    {
        _repoRoot = repoRoot ?? EngineProcessRunner.FindRepoRoot();
    }

    public string Enqueue(
        string action,
        string lane,
        int? autoscan = null,
        bool forceFresh = false,
        string? pair = null,
        IReadOnlyList<string>? lanes = null)
    {
        var psi = BasePythonPsi();
        psi.ArgumentList.Add("--enqueue");
        psi.ArgumentList.Add(action);
        psi.ArgumentList.Add("--lane");
        psi.ArgumentList.Add(lane);
        if (autoscan is not null)
        {
            psi.ArgumentList.Add("--autoscan");
            psi.ArgumentList.Add(autoscan.Value.ToString());
        }
        if (forceFresh && action == "run_scan")
            psi.ArgumentList.Add("--force-fresh");
        if (!string.IsNullOrWhiteSpace(pair) && action == "run_backtest")
        {
            psi.ArgumentList.Add("--pair");
            psi.ArgumentList.Add(pair.Trim());
        }
        if (lanes is { Count: > 0 })
        {
            psi.ArgumentList.Add("--lanes");
            psi.ArgumentList.Add(string.Join(",", lanes));
        }

        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException("Failed to start desk enqueue process");
        var stdout = proc.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();
        proc.WaitForExit(60_000);
        if (proc.ExitCode != 0)
            throw new InvalidOperationException($"enqueue failed ({proc.ExitCode}): {stderr}\n{stdout}");
        return stdout.Trim();
    }

    /// <summary>Fire-and-forget one desk command (scan / cancel / ack).</summary>
    public void StartDeskOnce(bool dryRun = false)
    {
        // Overlapping workers are gated by Python desk_once.lock (single-flight).
        var psi = EngineProcessRunner.CreateResultsStorePsi(_repoRoot, redirectOutput: false);
        psi.ArgumentList.Add("--root");
        psi.ArgumentList.Add(ProfilePaths.DeviceRoot);
        psi.ArgumentList.Add("--desk-once");
        if (dryRun)
            psi.ArgumentList.Add("--desk-dry");
        Process.Start(psi);
    }

    private ProcessStartInfo BasePythonPsi()
    {
        var psi = EngineProcessRunner.CreateResultsStorePsi(_repoRoot, redirectOutput: true);
        psi.ArgumentList.Add("--root");
        psi.ArgumentList.Add(ProfilePaths.DeviceRoot);
        return psi;
    }

    public static string? PeekPendingAction(string? profileRoot = null)
    {
        var root = profileRoot ?? ProfilePaths.DeviceRoot;
        var dbPath = Path.Combine(root, "results.db");
        if (File.Exists(dbPath))
        {
            try
            {
                using var conn = new SqliteConnection($"Data Source={dbPath};Default Timeout=5");
                conn.Open();
                using var cmd = conn.CreateCommand();
                cmd.CommandText =
                    "SELECT action FROM desk_commands WHERE status='pending' ORDER BY seq DESC LIMIT 1";
                if (cmd.ExecuteScalar() is string dbAction && !string.IsNullOrWhiteSpace(dbAction))
                    return dbAction;
            }
            catch (SqliteException)
            {
                /* table may not exist on older DB before first enqueue; fall through to JSON mirror */
            }
        }
        var path = Path.Combine(root, "desk_commands.json");
        if (!File.Exists(path))
            return null;
        try
        {
            using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            using var doc = JsonDocument.Parse(fs);
            if (!doc.RootElement.TryGetProperty("commands", out var cmds))
                return null;
            for (var i = cmds.GetArrayLength() - 1; i >= 0; i--)
            {
                var row = cmds[i];
                if (row.TryGetProperty("status", out var st) && st.GetString() == "pending"
                    && row.TryGetProperty("action", out var act))
                    return act.GetString();
            }
        }
        catch (IOException)
        {
            return null;
        }
        return null;
    }
}
