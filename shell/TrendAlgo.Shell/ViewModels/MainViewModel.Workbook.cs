using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    [RelayCommand]
    private void ReloadWorkbook()
    {
        StrategyRows.Clear();
        RefreshHandshake();
        var run = string.IsNullOrEmpty(RunId) ? _results.LatestRunId() : RunId;
        run ??= _results.LatestRunId("migrate_opportunity") ?? _results.LatestRunId("opportunity");
        if (run is null)
        {
            RowCount = 0;
            StatusText = _results.Exists
                ? $"results.db present — no runs yet ({ProfilePaths.ResultsDb})"
                : $"Waiting for engine results.db at {ProfilePaths.ResultsDb}";
            return;
        }
        RunId = run;
        RowCount = Math.Max(_results.CountStrategies(run), _results.CountOpportunities(run));
        foreach (var row in _results.LoadStrategyPage(run, limit: 1000))
            StrategyRows.Add(row);
        if (StrategyRows.Count == 0)
            foreach (var row in _results.LoadOpportunityPage(run, limit: 1000))
                StrategyRows.Add(row);
        StatusText = $"Run {run[..Math.Min(8, run.Length)]}… — {RowCount} rows (showing {StrategyRows.Count})";
    }

    [RelayCommand]
    private void RefreshHandshake()
    {
        var hs = EngineHandshake.TryLoad();
        HandshakeText = hs is null ? "Engine IPC: missing (start Python writer)"
            : hs.IsCompatible ? $"Engine IPC OK — v{hs.EngineVersion} schema {hs.SchemaVersion}"
            : $"Engine IPC incompatible — protocol {hs.ProtocolVersionValue} schema {hs.SchemaVersion}";
    }

    [RelayCommand]
    private void ApplyQuery()
    {
        if (string.IsNullOrWhiteSpace(QueryText)) { ReloadWorkbook(); return; }
        var needle = QueryText.Trim();
        var filtered = StrategyRows.Where(r =>
            r.StrategyId.Contains(needle, StringComparison.OrdinalIgnoreCase)
            || r.Pair.Contains(needle, StringComparison.OrdinalIgnoreCase)
            || r.PayloadJson.Contains(needle, StringComparison.OrdinalIgnoreCase)).ToList();
        StrategyRows.Clear();
        foreach (var row in filtered) StrategyRows.Add(row);
        StatusText = $"Query '{needle}' → {StrategyRows.Count} rows";
        ShowWorkbook = true;
    }

    [RelayCommand]
    private void SetJobDial(string? workers)
    {
        if (int.TryParse(workers, out var n) && n is >= 1 and <= 64) JobWorkers = n;
        StatusText = $"Job dial (P2): engine worker cap hint = {JobWorkers}";
    }

    [RelayCommand]
    private void CycleThemeDensity()
    {
        ThemeDensity = ThemeDensity == "comfortable" ? "compact" : "comfortable";
        StatusText = $"Theme pack (P2): density = {ThemeDensity}";
    }

    [RelayCommand]
    private void CycleThemeMode()
    {
        ThemeMode = ThemeMode switch
        {
            "system" => "light",
            "light" => "dark",
            _ => "system",
        };
        ShellTheme.Persist(ThemeMode, AccentColor);
        StatusText = $"Theme = {ThemeMode} · accent={(string.IsNullOrEmpty(AccentColor) ? "default" : AccentColor)}";
    }

    [RelayCommand]
    private void CycleAccent()
    {
        var presets = ShellTheme.AccentPresets;
        var i = Array.FindIndex(presets, a =>
            string.Equals(a, AccentColor, StringComparison.OrdinalIgnoreCase));
        AccentColor = presets[(i + 1) % presets.Length];
        ShellTheme.Persist(ThemeMode, AccentColor);
        StatusText = $"Accent = {(string.IsNullOrEmpty(AccentColor) ? "default" : AccentColor)} · theme={ThemeMode}";
    }

    [RelayCommand]
    private void OpenCommandPalette() => Navigate("palette");

    [RelayCommand]
    private void ExportSelection()
    {
        var dir = Path.Combine(ProfilePaths.DeviceRoot, "exports");
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, $"workbook-{DateTime.Now:yyyyMMddHHmmss}.tsv");
        File.WriteAllLines(path, StrategyRows.Select(r => $"{r.StrategyId}\t{r.Pair}\t{r.PayloadJson}"));
        StatusText = $"Export studio (P1): wrote {StrategyRows.Count} rows → {path}";
    }
}
