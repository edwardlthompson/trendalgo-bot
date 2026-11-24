using Microsoft.Data.Sqlite;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

public sealed class ResultsDbReader
{
    private readonly string _dbPath;

    public ResultsDbReader(string? dbPath = null)
    {
        _dbPath = dbPath ?? ProfilePaths.ResultsDb;
    }

    public bool Exists => File.Exists(_dbPath);

    public IReadOnlyList<StrategyRow> LoadStrategyPage(string runId, int offset = 0, int limit = 500)
    {
        if (!Exists)
            return Array.Empty<StrategyRow>();

        var rows = new List<StrategyRow>();
        using var conn = new SqliteConnection($"Data Source={_dbPath}");
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText =
            "SELECT strategy_id, pair, payload_json FROM strategy_rows " +
            "WHERE run_id=$run ORDER BY row_id LIMIT $limit OFFSET $offset";
        cmd.Parameters.AddWithValue("$run", runId);
        cmd.Parameters.AddWithValue("$limit", limit);
        cmd.Parameters.AddWithValue("$offset", offset);
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            rows.Add(new StrategyRow(
                reader.GetString(0),
                reader.GetString(1),
                reader.IsDBNull(2) ? "{}" : reader.GetString(2)));
        }
        return rows;
    }

    public string? LatestRunId(string kind = "all_ta", string? lane = null)
    {
        if (!Exists)
            return null;
        using var conn = new SqliteConnection($"Data Source={_dbPath}");
        conn.Open();
        using var cmd = conn.CreateCommand();
        if (string.IsNullOrWhiteSpace(lane))
        {
            cmd.CommandText =
                "SELECT run_id FROM runs WHERE kind=$kind ORDER BY started_at DESC LIMIT 1";
            cmd.Parameters.AddWithValue("$kind", kind);
        }
        else
        {
            cmd.CommandText =
                "SELECT run_id FROM runs WHERE kind=$kind AND lane=$lane " +
                "ORDER BY started_at DESC LIMIT 1";
            cmd.Parameters.AddWithValue("$kind", kind);
            cmd.Parameters.AddWithValue("$lane", lane);
        }
        return cmd.ExecuteScalar() as string;
    }

    public string? JobState(string jobId)
    {
        if (!Exists)
            return null;
        using var conn = new SqliteConnection($"Data Source={_dbPath}");
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT state FROM job_control WHERE job_id=$id";
        cmd.Parameters.AddWithValue("$id", jobId);
        return cmd.ExecuteScalar() as string;
    }

    public int CountStrategies(string runId) => CountTable("strategy_rows", runId);

    public int CountOpportunities(string runId) => CountTable("opportunity_rows", runId);

    public IReadOnlyList<StrategyRow> LoadOpportunityPage(string runId, int offset = 0, int limit = 500)
    {
        if (!Exists)
            return Array.Empty<StrategyRow>();
        var rows = new List<StrategyRow>();
        using var conn = new SqliteConnection($"Data Source={_dbPath}");
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText =
            "SELECT pair, payload_json FROM opportunity_rows " +
            "WHERE run_id=$run ORDER BY row_id LIMIT $limit OFFSET $offset";
        cmd.Parameters.AddWithValue("$run", runId);
        cmd.Parameters.AddWithValue("$limit", limit);
        cmd.Parameters.AddWithValue("$offset", offset);
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var pair = reader.GetString(0);
            rows.Add(new StrategyRow("opportunity", pair, reader.IsDBNull(1) ? "{}" : reader.GetString(1)));
        }
        return rows;
    }

    private int CountTable(string table, string runId)
    {
        if (!Exists)
            return 0;
        using var conn = new SqliteConnection($"Data Source={_dbPath}");
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = $"SELECT COUNT(*) FROM {table} WHERE run_id=$run";
        cmd.Parameters.AddWithValue("$run", runId);
        return Convert.ToInt32(cmd.ExecuteScalar());
    }
}

public sealed record StrategyRow(string StrategyId, string Pair, string PayloadJson);
