using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Threading;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.Views;

public partial class BenchmarkWindow : Window
{
    public sealed record AssetRow(
        string Lane, string Pair, string Status, string Source, string Bars,
        string Fetch, string Pass1, string Deepen, string Mc, string Sauce, string Total, string TopResult);

    public sealed record SubtestRow(
        string Asset, string Component, string Timeframe, string Duration, string Detail);

    private readonly DeskSurfaceClient _surfaces = new();
    private readonly Stopwatch _stopwatch = new();
    private CancellationTokenSource? _cts;
    private Process? _proc;

    public JsonDocument? LastEtaDoc { get; private set; }
    public bool BenchmarkSucceeded { get; private set; }

    public BenchmarkWindow() : this(runLive: false)
    {
    }

    public BenchmarkWindow(bool runLive)
    {
        InitializeComponent();
        if (!runLive)
        {
            LoadSavedResults();
            return;
        }
        ProgressPanel.IsVisible = true;
        CancelBtn.IsVisible = true;
        CloseBtn.IsEnabled = false;
        SummaryTitle.Text = "Benchmark in progress…";
        SummaryDetail.Text =
            "Pulling real data for Crypto (BTC/USD), TradFi (AAPL/USD), and Forex (EUR/USD) "
            + "and running full All-TA + Secret Sauce…";
        Opened += OnLiveOpened;
    }

    private async void OnLiveOpened(object? sender, EventArgs e)
    {
        Opened -= OnLiveOpened;
        _cts = new CancellationTokenSource();
        _stopwatch.Restart();
        var pollTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(250) };
        pollTimer.Tick += (_, _) => PollProgressFile();
        pollTimer.Start();

        try
        {
            using var doc = await _surfaces.RunBenchmarkAsync(p => _proc = p, _cts.Token);
            pollTimer.Stop();
            _stopwatch.Stop();
            ProgressPanel.IsVisible = false;
            CancelBtn.IsVisible = false;
            CloseBtn.IsEnabled = true;

            var root = doc.RootElement;
            if (root.TryGetProperty("eta", out var etaEl) && etaEl.ValueKind == JsonValueKind.Object)
                LastEtaDoc = JsonDocument.Parse(etaEl.GetRawText());
            BenchmarkSucceeded = root.TryGetProperty("ok", out var ok) && ok.ValueKind == JsonValueKind.True;
            BindReport(root);
        }
        catch (Exception ex)
        {
            pollTimer.Stop();
            _stopwatch.Stop();
            ProgressPanel.IsVisible = false;
            CancelBtn.IsVisible = false;
            CloseBtn.IsEnabled = true;
            BenchmarkSucceeded = false;
            SummaryTitle.Text = "Benchmark Failed";
            SummaryDetail.Text = ex.Message;
        }
    }

    private void PollProgressFile()
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, "benchmark_progress.json");
        var text = TryReadSharedText(path);
        if (string.IsNullOrWhiteSpace(text))
            return;
        try
        {
            using var doc = JsonDocument.Parse(text);
            var r = doc.RootElement;
            var done = r.TryGetProperty("tests_done", out var de) ? de.GetInt32() : 0;
            var total = Math.Max(1, r.TryGetProperty("tests_total", out var te) ? te.GetInt32() : 1);
            var rem = r.TryGetProperty("tests_remaining", out var re) ? re.GetInt32() : Math.Max(0, total - done);
            var jsonElapsed = r.TryGetProperty("elapsed_s", out var ee) && ee.TryGetDouble(out var ev) ? ev : 0;
            var elapsed = Math.Max(jsonElapsed, _stopwatch.Elapsed.TotalSeconds);
            var lane = r.TryGetProperty("current_lane", out var le) ? le.ToString() : "";
            var pair = r.TryGetProperty("current_pair", out var pe) ? pe.ToString() : "";
            var phase = r.TryGetProperty("phase", out var ph) ? ph.ToString() : "";
            var msg = r.TryGetProperty("message", out var me) ? me.ToString() : "";

            ProgressHeader.Text = string.IsNullOrWhiteSpace(pair)
                ? $"Running real-data 3-asset benchmark… {elapsed:0.0}s"
                : $"Benchmarking {lane} ({pair}) · Phase: {phase} · {elapsed:0.0}s";
            ProgressCounts.Text = $"Tests completed: {done} / {total} · Remaining: {rem}";
            ProgressBar.Value = Math.Clamp(100.0 * done / total, 0, 100);
            ProgressMessage.Text = msg;

            if (r.TryGetProperty("completed_assets", out var ca)
                && ca.ValueKind == JsonValueKind.Array
                && ca.GetArrayLength() > 0)
            {
                BindAssets(ca);
            }
        }
        catch { /* ignore mid-write */ }
    }

    public void LoadSavedResults()
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, "benchmark_last_results.json");
        var text = TryReadSharedText(path);
        if (string.IsNullOrWhiteSpace(text))
            return;
        try
        {
            using var doc = JsonDocument.Parse(text);
            BindReport(doc.RootElement);
        }
        catch { /* ignore corrupt file */ }
    }

    private void BindReport(JsonElement r)
    {
        var ranAt = LocalTimeFormat.FormatTimestamp(Str(r, "ran_at"));
        var totalS = Dbl(r, "benchmark_s");
        var done = Int(r, "tests_done");
        var total = Int(r, "tests_total");
        var strats = Int(r, "strategies_count");
        var tfs = Int(r, "timeframes_count");
        var ok = !r.TryGetProperty("ok", out var okEl) || okEl.ValueKind == JsonValueKind.True;
        var cancelled = r.TryGetProperty("cancelled", out var ce) && ce.ValueKind == JsonValueKind.True;
        var etaTotal = r.TryGetProperty("eta", out var eta) && eta.TryGetProperty("total", out var et)
            ? et.ToString() : "";

        if (!ok && !cancelled)
        {
            SummaryTitle.Text = "Benchmark Failed";
            var errText = Str(r, "error");
            SummaryDetail.Text = string.IsNullOrWhiteSpace(errText) ? "Benchmark process failed." : errText;
            return;
        }

        SummaryTitle.Text = cancelled ? $"Benchmark Cancelled · {ranAt}" : $"Benchmark Complete · {ranAt}";
        SummaryDetail.Text =
            $"Wall time: {totalS:0.0}s · Tests: {done}/{total} ({strats} strategies × {tfs} timeframes + Secret Sauce)"
            + (string.IsNullOrWhiteSpace(etaTotal) ? "" : $"\n{etaTotal}");

        if (r.TryGetProperty("assets", out var aArr) && aArr.ValueKind == JsonValueKind.Array)
            BindAssets(aArr);

        var subs = new ObservableCollection<SubtestRow>();
        if (r.TryGetProperty("subtests", out var sArr) && sArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var s in sArr.EnumerateArray())
            {
                subs.Add(new SubtestRow(
                    Str(s, "asset"),
                    Str(s, "component"),
                    Str(s, "timeframe"),
                    $"{Dbl(s, "duration_s"):0.3}s",
                    Str(s, "detail")));
            }
        }
        SubtestsGrid.ItemsSource = subs;
    }

    private void BindAssets(JsonElement aArr)
    {
        var assets = new ObservableCollection<AssetRow>();
        foreach (var a in aArr.EnumerateArray())
        {
            var topInd = Str(a, "top_indicator");
            var topTf = Str(a, "top_timeframe");
            var topNet = a.TryGetProperty("top_net_pct", out var tn) && tn.TryGetDouble(out var tnv)
                ? $"{tnv:+0.0;-0.0;0.0}%" : "—";
            var sauceNet = a.TryGetProperty("sauce_net_pct", out var sn) && sn.TryGetDouble(out var snv)
                ? $" · Sauce {snv:+0.0;-0.0;0.0}%" : "";
            assets.Add(new AssetRow(
                Str(a, "lane"), Str(a, "pair"), Str(a, "status"), Str(a, "data_source"),
                Int(a, "bars").ToString(), $"{Dbl(a, "load_s"):0.2}s", $"{Dbl(a, "pass1_s"):0.2}s",
                $"{Dbl(a, "deepen_s"):0.2}s", $"{Dbl(a, "mc_s"):0.2}s", $"{Dbl(a, "sauce_s"):0.2}s",
                $"{Dbl(a, "total_s"):0.2}s", $"{topTf} {topInd} ({topNet}){sauceNet}"));
        }
        AssetsGrid.ItemsSource = assets;
    }

    private static string? TryReadSharedText(string path)
    {
        if (!File.Exists(path))
            return null;
        try
        {
            using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
            using var sr = new StreamReader(fs, Encoding.UTF8);
            return sr.ReadToEnd();
        }
        catch
        {
            return null;
        }
    }

    private void OnCancel(object? sender, RoutedEventArgs e)
    {
        try { File.WriteAllText(Path.Combine(ProfilePaths.DeviceRoot, "benchmark_cancel.flag"), "1"); }
        catch { /* ignore */ }
        _cts?.Cancel();
        try { _proc?.Kill(entireProcessTree: true); } catch { /* ignore */ }
    }

    private void OnClose(object? sender, RoutedEventArgs e) => Close();

    private static string Str(JsonElement e, string k) =>
        e.TryGetProperty(k, out var p) && p.ValueKind != JsonValueKind.Null ? p.ToString() : "";

    private static double Dbl(JsonElement e, string k) =>
        e.TryGetProperty(k, out var p) && p.TryGetDouble(out var v) ? v : 0;

    private static int Int(JsonElement e, string k) =>
        e.TryGetProperty(k, out var p) && p.TryGetInt32(out var v) ? v : 0;
}
