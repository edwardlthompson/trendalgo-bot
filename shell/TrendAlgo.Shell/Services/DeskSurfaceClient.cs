using System.Diagnostics;
using System.Text.Json;

namespace TrendAlgo.Shell.Services;

/// <summary>Call Python --surface exporters for Results / DEX / chart / events / sauce.</summary>
public sealed class DeskSurfaceClient
{
    private readonly string _repoRoot;

    public DeskSurfaceClient(string? repoRoot = null)
    {
        _repoRoot = repoRoot ?? EngineProcessRunner.FindRepoRoot();
    }

    public JsonDocument Fetch(string surface, string lane, string pair = "") =>
        FetchAsync(surface, lane, pair).GetAwaiter().GetResult();

    public async Task<JsonDocument> FetchAsync(
        string surface, string lane, string pair = "", CancellationToken ct = default)
    {
        var warm = await PythonSidecarClient.Instance.TryRequestAsync(
            _repoRoot,
            new { op = "surface", surface, lane, pair },
            ct: ct).ConfigureAwait(false);
        if (warm is not null)
            return warm;
        return await RunJsonAsync(BuildSurfacePsi(surface, lane, pair), $"surface {surface}", allowFail: false, ct: ct)
            .ConfigureAwait(false);
    }

    private ProcessStartInfo BuildSurfacePsi(string surface, string lane, string pair)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--surface");
        psi.ArgumentList.Add(surface);
        psi.ArgumentList.Add("--lane");
        psi.ArgumentList.Add(lane);
        if (!string.IsNullOrWhiteSpace(pair))
        {
            psi.ArgumentList.Add("--pair");
            psi.ArgumentList.Add(pair);
        }
        return psi;
    }

    public JsonDocument ToggleWatch(string lane, string pair) =>
        ToggleWatchAsync(lane, pair).GetAwaiter().GetResult();

    public async Task<JsonDocument> ToggleWatchAsync(string lane, string pair, CancellationToken ct = default)
    {
        var warm = await PythonSidecarClient.Instance.TryRequestAsync(
            _repoRoot,
            new { op = "toggle_watch", lane, pair },
            ct: ct).ConfigureAwait(false);
        if (warm is not null)
            return warm;
        return await RunJsonAsync(BuildToggleWatchPsi(lane, pair), "toggle_watch", allowFail: false, ct: ct)
            .ConfigureAwait(false);
    }

    private ProcessStartInfo BuildToggleWatchPsi(string lane, string pair)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--toggle-watch");
        psi.ArgumentList.Add("--lane");
        psi.ArgumentList.Add(lane);
        psi.ArgumentList.Add("--pair");
        psi.ArgumentList.Add(pair);
        return psi;
    }

    public JsonDocument CreateBot(string pair, string indicator)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--create-bot");
        psi.ArgumentList.Add("--pair");
        psi.ArgumentList.Add(pair);
        psi.ArgumentList.Add("--indicator");
        psi.ArgumentList.Add(indicator);
        return RunJson(psi);
    }

    public JsonDocument SharePng(
        string kind,
        string lane,
        string pair = "",
        string dest = "",
        IEnumerable<string>? pairs = null,
        string title = "",
        string filtersJsonPath = "",
        bool includeMarketContext = true)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--share-png");
        psi.ArgumentList.Add(kind);
        psi.ArgumentList.Add("--lane");
        psi.ArgumentList.Add(lane);
        if (!string.IsNullOrWhiteSpace(pair) && kind is not "dashboard" and not "board")
        {
            psi.ArgumentList.Add("--pair");
            psi.ArgumentList.Add(pair);
        }
        if (!string.IsNullOrWhiteSpace(dest))
        {
            psi.ArgumentList.Add("--dest");
            psi.ArgumentList.Add(dest);
        }
        if (kind == "board" && pairs is not null)
        {
            var joined = string.Join(",", pairs.Where(p => !string.IsNullOrWhiteSpace(p)));
            if (!string.IsNullOrWhiteSpace(joined))
            {
                psi.ArgumentList.Add("--pairs");
                psi.ArgumentList.Add(joined);
            }
        }
        if (kind == "board" && !string.IsNullOrWhiteSpace(title))
        {
            psi.ArgumentList.Add("--share-title");
            psi.ArgumentList.Add(title);
        }
        if (kind == "board" && !string.IsNullOrWhiteSpace(filtersJsonPath))
        {
            psi.ArgumentList.Add("--filters-json");
            psi.ArgumentList.Add(filtersJsonPath);
        }
        if (kind == "board")
        {
            psi.ArgumentList.Add("--include-mc");
            psi.ArgumentList.Add(includeMarketContext ? "1" : "0");
        }
        return RunJson(psi);
    }

    public JsonDocument ApplyScanSettings(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-scan-settings");
        psi.ArgumentList.Add(jsonPath);
        return RunJson(psi);
    }

    public JsonDocument ApplyDashboardCustomize(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-dashboard-customize");
        psi.ArgumentList.Add(jsonPath);
        return RunJson(psi);
    }

    public JsonDocument ApplyDashboardMins(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-dashboard-mins");
        psi.ArgumentList.Add(jsonPath);
        return RunJson(psi);
    }

    public async Task<JsonDocument> VerifyExchangeKeyAsync(
        string exchangeId, CancellationToken ct = default)
    {
        var warm = await PythonSidecarClient.Instance.TryRequestAsync(
            _repoRoot,
            new { op = "verify_exchange_key", exchange_id = exchangeId },
            ct: ct).ConfigureAwait(false);
        if (warm is not null)
            return warm;
        var psi = BasePsi();
        psi.ArgumentList.Add("--verify-exchange-key");
        psi.ArgumentList.Add(exchangeId);
        return await RunJsonAsync(psi, "verify-exchange-key", allowFail: true, timeoutMs: 45_000, ct: ct)
            .ConfigureAwait(false);
    }

    public async Task<JsonDocument> SyncPortfolioAsync(CancellationToken ct = default)
    {
        var warm = await PythonSidecarClient.Instance.TryRequestAsync(
            _repoRoot,
            new { op = "portfolio_sync" },
            ct: ct).ConfigureAwait(false);
        if (warm is not null)
            return warm;
        var psi = BasePsi();
        psi.ArgumentList.Add("--portfolio-sync");
        return await RunJsonAsync(psi, "portfolio-sync", allowFail: true, timeoutMs: 120_000, ct: ct)
            .ConfigureAwait(false);
    }

    public Task<JsonDocument> ApplyDashboardLayoutAsync(
        string jsonPath, CancellationToken ct = default)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-dashboard-layout");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAsync(psi, "apply-dashboard-layout", allowFail: true, ct: ct);
    }

    public Task<JsonDocument> ExportPortfolioReportAsync(
        string jsonPath, CancellationToken ct = default)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--export-portfolio-report");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAsync(psi, "export-portfolio-report", allowFail: true, timeoutMs: 60_000, ct: ct);
    }

    public JsonDocument BotsPanic()
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--bots-panic");
        return RunJson(psi);
    }

    public JsonDocument BotsPublishPlan()
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--bots-publish-plan");
        return RunJsonAllowFail(psi);
    }

    public JsonDocument BotsSetEnabled(string botId, bool enabled)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--bots-set-enabled");
        psi.ArgumentList.Add(botId);
        psi.ArgumentList.Add(enabled ? "--bots-enable" : "--bots-pause");
        return RunJsonAllowFail(psi);
    }

    public JsonDocument DeriveOracle(string lane, string pair)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--derive-oracle");
        psi.ArgumentList.Add("--lane");
        psi.ArgumentList.Add(lane);
        psi.ArgumentList.Add("--pair");
        psi.ArgumentList.Add(pair);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument ApplyVenue(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-venue");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument ApplyLanes(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-lanes");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument ApplyConnection(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-connection");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument ApplySettingsLayout(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-settings-layout");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument WizardAdvance(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--wizard-advance");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument WizardBack()
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--wizard-back");
        return RunJsonAllowFail(psi);
    }

    public JsonDocument ApplyPrivacy(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-privacy");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument ApplyData(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-data");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument CheckUpdates()
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--check-updates");
        return RunJsonAllowFail(psi);
    }

    public JsonDocument ExportHub(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--export-hub");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument ApplyResultsPrefs(string jsonPath)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--apply-results-prefs");
        psi.ArgumentList.Add(jsonPath);
        return RunJsonAllowFail(psi);
    }

    public JsonDocument TestTelegram()
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--test-telegram");
        return RunJsonAllowFail(psi);
    }

    public JsonDocument TestTelegramRich()
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--test-telegram-rich");
        return RunJsonAllowFail(psi);
    }

    public JsonDocument TestGrokbot()
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--test-grokbot");
        return RunJsonAllowFail(psi);
    }

    public JsonDocument RunBenchmark()
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--benchmark");
        return RunJsonAllowFail(psi);
    }

    public Task<JsonDocument> RunBenchmarkAsync(
        Action<Process>? onStarted = null, CancellationToken ct = default)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--benchmark");
        return RunJsonAsync(psi, "benchmark", allowFail: true, timeoutMs: 900_000, onStarted: onStarted, ct: ct);
    }

    public Task<JsonDocument> RunPairBacktestAsync(
        string pair,
        string lane = "crypto",
        Action<Process>? onStarted = null,
        CancellationToken ct = default)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--pair-backtest");
        psi.ArgumentList.Add("--pair");
        psi.ArgumentList.Add(pair);
        psi.ArgumentList.Add("--lane");
        psi.ArgumentList.Add(string.IsNullOrWhiteSpace(lane) ? "crypto" : lane);
        return RunJsonAsync(psi, "pair-backtest", allowFail: true, timeoutMs: 900_000, onStarted: onStarted, ct: ct);
    }

    public JsonDocument AckStartup(string kind, string version = "", bool dismissed = false)
    {
        var psi = BasePsi();
        psi.ArgumentList.Add("--ack-startup");
        psi.ArgumentList.Add(kind);
        if (!string.IsNullOrWhiteSpace(version))
        {
            psi.ArgumentList.Add("--ack-version");
            psi.ArgumentList.Add(version);
        }
        if (dismissed)
            psi.ArgumentList.Add("--ack-dismissed");
        return RunJsonAllowFail(psi);
    }

    private ProcessStartInfo BasePsi()
    {
        var psi = EngineProcessRunner.CreateResultsStorePsi(_repoRoot, redirectOutput: true);
        psi.ArgumentList.Add("--root");
        psi.ArgumentList.Add(ProfilePaths.DeviceRoot);
        return psi;
    }

    private static JsonDocument RunJson(ProcessStartInfo psi, string label = "mutate") =>
        RunJsonAsync(psi, label, allowFail: false).GetAwaiter().GetResult();

    private static JsonDocument RunJsonAllowFail(ProcessStartInfo psi) =>
        RunJsonAsync(psi, "mutate", allowFail: true).GetAwaiter().GetResult();

    private static async Task<JsonDocument> RunJsonAsync(
        ProcessStartInfo psi,
        string label,
        bool allowFail,
        int timeoutMs = 60_000,
        Action<Process>? onStarted = null,
        CancellationToken ct = default)
    {
        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException($"Failed to start {label}");
        onStarted?.Invoke(proc);
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(timeoutMs);
        var outTask = proc.StandardOutput.ReadToEndAsync();
        var errTask = proc.StandardError.ReadToEndAsync();
        try
        {
            await proc.WaitForExitAsync(cts.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try { proc.Kill(entireProcessTree: true); } catch { /* ignore */ }
            if (allowFail)
                return JsonDocument.Parse("{\"ok\":false,\"error\":\"cancelled\"}");
            throw new TimeoutException($"{label} timed out");
        }
        var stdout = await outTask.ConfigureAwait(false);
        var stderr = await errTask.ConfigureAwait(false);
        if (!allowFail && proc.ExitCode != 0)
            throw new InvalidOperationException($"{label} failed: {stderr}\n{stdout}");

        var jsonPayload = ExtractJsonPayload(stdout);
        if (allowFail && !string.IsNullOrWhiteSpace(jsonPayload) && jsonPayload.StartsWith('{'))
            return JsonDocument.Parse(jsonPayload);
        if (allowFail && (proc.ExitCode != 0 || string.IsNullOrWhiteSpace(jsonPayload)))
        {
            var errMsg = string.IsNullOrWhiteSpace(stderr)
                ? $"Exited with code {proc.ExitCode}"
                : TailLines(stderr, 8);
            return JsonDocument.Parse(
                JsonSerializer.Serialize(new { ok = false, exit_code = proc.ExitCode, error = errMsg }));
        }
        return JsonDocument.Parse(string.IsNullOrWhiteSpace(jsonPayload) ? "{}" : jsonPayload);
    }

    private static string ExtractJsonPayload(string stdout)
    {
        if (string.IsNullOrWhiteSpace(stdout))
            return "";
        var lines = stdout.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        for (var i = lines.Length - 1; i >= 0; i--)
        {
            if (lines[i].StartsWith('{') && lines[i].EndsWith('}'))
                return lines[i];
        }
        return stdout.Trim();
    }

    private static string TailLines(string text, int count)
    {
        var lines = text.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        return string.Join("\n", lines.TakeLast(count));
    }
}
