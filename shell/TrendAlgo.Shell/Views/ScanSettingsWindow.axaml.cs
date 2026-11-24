using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.ComponentModel;
using System.Text.Json;
using System.Text.Json.Nodes;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.Views;

public partial class ScanSettingsWindow : Window, INotifyPropertyChanged
{
    private static readonly string[] SubhourFallback = ["1m", "5m", "15m", "30m"];
    private static readonly string[] HoursFallback =
        Enumerable.Range(1, 24).Select(h => $"{h}h").ToArray();

    private readonly DeskSurfaceClient _surfaces = new();
    private readonly ScanSettingsEtaCalculator _etaCalc = new();
    private bool _suppressTfExclusivity;
    private bool _loadingPrefs;
    private string _note = "";

    public new event PropertyChangedEventHandler? PropertyChanged;

    private decimal _minVolume = 100_000m;
    public decimal MinVolume
    {
        get => _minVolume;
        set { if (_minVolume != value) { _minVolume = value; RecalculateLiveEta(); } }
    }

    private decimal _intervalMinutes = 60m;
    public decimal IntervalMinutes
    {
        get => _intervalMinutes;
        set { if (_intervalMinutes != value) { _intervalMinutes = value; RecalculateLiveEta(); } }
    }

    private bool _requireContinuous1h = true;
    public bool RequireContinuous1h
    {
        get => _requireContinuous1h;
        set { if (_requireContinuous1h != value) { _requireContinuous1h = value; RecalculateLiveEta(); } }
    }

    public bool Heatmap { get; set; }
    public bool PerfectOnly { get; set; }

    private bool _marketContext = true;
    public bool MarketContext
    {
        get => _marketContext;
        set { if (_marketContext != value) { _marketContext = value; RecalculateLiveEta(); } }
    }

    private bool _sauceWithScan;
    public bool SauceWithScan
    {
        get => _sauceWithScan;
        set { if (_sauceWithScan != value) { _sauceWithScan = value; RecalculateLiveEta(); } }
    }

    private decimal _sauceTopN = 30m;
    public decimal SauceTopN
    {
        get => _sauceTopN;
        set { if (_sauceTopN != value) { _sauceTopN = value; RecalculateLiveEta(); } }
    }

    public string OhlcvtPath { get; set; } = "";
    public bool OhlcvtAutoTip { get; set; }
    public string SubhourMixNote { get; set; } = "";
    public string Note
    {
        get => _note;
        set
        {
            if (_note == value)
                return;
            _note = value ?? "";
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Note)));
        }
    }
    public string TfSummary { get; set; } = "";
    public string StratSummary { get; set; } = "";
    public string EtaTitle { get; set; } = "Estimated scan time";
    public string EtaLines { get; set; } = "";
    public string EtaTotal { get; set; } = "";
    public string EtaNote { get; set; } = "";
    public bool EtaOverrun { get; set; }
    public string EtaWarning { get; set; } = "";
    public decimal RecommendedIntervalMinutes { get; set; } = 60m;
    public bool HasBenchmarkResults =>
        File.Exists(Path.Combine(ProfilePaths.DeviceRoot, "benchmark_last_results.json"));
    public bool BandsMixReady { get; private set; }

    private bool _autoScanCrypto = true;
    public bool AutoScanCrypto
    {
        get => _autoScanCrypto;
        set { if (_autoScanCrypto != value) { _autoScanCrypto = value; RecalculateLiveEta(); } }
    }

    private bool _autoScanTradfi;
    public bool AutoScanTradfi
    {
        get => _autoScanTradfi;
        set { if (_autoScanTradfi != value) { _autoScanTradfi = value; RecalculateLiveEta(); } }
    }

    private bool _autoScanForex;
    public bool AutoScanForex
    {
        get => _autoScanForex;
        set { if (_autoScanForex != value) { _autoScanForex = value; RecalculateLiveEta(); } }
    }

    public decimal TradfiAbsGain { get; set; } = 5m;
    public decimal TradfiRange { get; set; } = 8m;

    private decimal _tradfiTopN = 120m;
    public decimal TradfiTopN
    {
        get => _tradfiTopN;
        set { if (_tradfiTopN != value) { _tradfiTopN = value; RecalculateLiveEta(); } }
    }
    public decimal TradfiAdv { get; set; }
    public decimal TradfiPrice { get; set; }
    private string _pendingTradfiPreset = "";

    public ObservableCollection<PrefToggleRow> Timeframes { get; } = new();
    public ObservableCollection<TfBandGroup> TfBands { get; } = new();
    public ObservableCollection<PrefToggleRow> Strategies { get; } = new();
    public ObservableCollection<PrefToggleRow> VisibleStrategies { get; } = new();
    public ObservableCollection<PrefToggleRow> Exchanges { get; } = new();

    private static readonly (string Id, string Label)[] ExchangeCatalog =
    [
        ("kraken", "Kraken"),
        ("coinbase", "Coinbase"),
        ("binance", "Binance"),
    ];

    private string _strategyFilter = "";
    public string StrategyFilter
    {
        get => _strategyFilter;
        set
        {
            _strategyFilter = value ?? "";
            ApplyStrategyFilter();
        }
    }

    public ScanSettingsWindow()
    {
        InitializeComponent();
        LoadPrefs(null);
        DataContext = this;
    }

    private ScanSettingsWindow(JsonDocument? preloadedSurface)
    {
        InitializeComponent();
        LoadPrefs(preloadedSurface);
        preloadedSurface?.Dispose();
        DataContext = this;
    }

    public static async Task<ScanSettingsWindow> CreateLoadedAsync()
    {
        var doc = await new DeskSurfaceClient().FetchAsync("scan_settings", "crypto");
        return await Avalonia.Threading.Dispatcher.UIThread.InvokeAsync(() => new ScanSettingsWindow(doc));
    }

    private static string FiltersPath =>
        Path.Combine(ProfilePaths.DeviceRoot, "scanner_filters.json");

    private void LoadPrefs(JsonDocument? preloadedSurface)
    {
        _loadingPrefs = true;
        try
        {
            if (File.Exists(FiltersPath))
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(FiltersPath));
                var root = doc.RootElement;
                MinVolume = ReadDecimal(root, "min_volume_usd", "min_volume") ?? MinVolume;
                IntervalMinutes = ReadDecimal(root, "interval_minutes") ?? IntervalMinutes;
                Heatmap = ReadBool(root, "heatmap_enabled");
                RequireContinuous1h = !root.TryGetProperty("require_continuous_1h", out _)
                    || ReadBool(root, "require_continuous_1h", defaultValue: true);
                LoadExchanges(root);
            }
            else
            {
                LoadExchanges(default);
            }

            using var owned = preloadedSurface is null ? _surfaces.Fetch("scan_settings", "crypto") : null;
            var prefs = (preloadedSurface ?? owned)!.RootElement;
            MarketContext = ReadBool(prefs, "market_context_with_scan", defaultValue: true);
            SauceWithScan = ReadBool(prefs, "sauce_with_scan");
            SauceTopN = ReadDecimal(prefs, "sauce_top_n") ?? SauceTopN;
            OhlcvtPath = prefs.TryGetProperty("ohlcvt_path", out var op) ? op.GetString() ?? "" : "";
            OhlcvtAutoTip = ReadBool(prefs, "ohlcvt_auto_tip");
            SubhourMixNote = prefs.TryGetProperty("subhour_mix_note", out var mn)
                ? mn.GetString() ?? ""
                : "";
            BandsMixReady = ReadBool(prefs, "bands_mix_ready");
            LoadEta(prefs);
            LoadLaneSettings(prefs);
            if (prefs.TryGetProperty("results_view", out var rv) && rv.ValueKind == JsonValueKind.Object)
            {
                Heatmap = ReadBool(rv, "heatmap_enabled", defaultValue: Heatmap);
                PerfectOnly = ReadBool(rv, "perfect_only");
            }
            FillToggles(Timeframes, prefs, "timeframes");
            BuildTfBands(prefs);
            FillToggles(Strategies, prefs, "strategies");
            foreach (var row in Strategies)
                row.PropertyChanged += OnStrategyChanged;
            Strategies.CollectionChanged += OnStrategiesCollectionChanged;
            ApplyStrategyFilter();
            RefreshSummaries();
            Note = $"Loaded {Timeframes.Count} TFs · {Strategies.Count} strategies from scan_bt_prefs";
        }
        catch (Exception ex)
        {
            Note = $"Could not load prefs: {ex.Message}";
            BuildTfBandsFallback();
        }
        finally
        {
            _loadingPrefs = false;
            RecalculateLiveEta();
        }
    }

    private void LoadExchanges(JsonElement root)
    {
        Exchanges.Clear();
        var selected = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (root.ValueKind == JsonValueKind.Object
            && root.TryGetProperty("scan_exchanges", out var arr)
            && arr.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in arr.EnumerateArray())
            {
                var id = item.GetString();
                if (!string.IsNullOrWhiteSpace(id))
                    selected.Add(id!);
            }
        }
        foreach (var (id, _) in ExchangeCatalog)
        {
            Exchanges.Add(new PrefToggleRow
            {
                Id = id,
                Enabled = selected.Count == 0 || selected.Contains(id),
            });
        }
    }

    private void LoadLaneSettings(JsonElement prefs)
    {
        if (prefs.TryGetProperty("lane_prefs", out var lp) && lp.ValueKind == JsonValueKind.Object)
        {
            AutoScanCrypto = ReadBool(lp, "auto_scan_crypto", defaultValue: true);
            AutoScanTradfi = ReadBool(lp, "auto_scan_tradfi");
            AutoScanForex = ReadBool(lp, "auto_scan_forex");
        }
        if (prefs.TryGetProperty("lane_scan_filters", out var lsf)
            && lsf.TryGetProperty("tradfi", out var tf)
            && tf.ValueKind == JsonValueKind.Object)
        {
            TradfiAbsGain = ReadDecimal(tf, "min_abs_gain_pct") ?? TradfiAbsGain;
            TradfiRange = ReadDecimal(tf, "min_range_pct") ?? TradfiRange;
            TradfiTopN = ReadDecimal(tf, "top_n") ?? TradfiTopN;
            TradfiAdv = ReadDecimal(tf, "min_adv_usd") ?? TradfiAdv;
            TradfiPrice = ReadDecimal(tf, "min_price") ?? TradfiPrice;
        }
    }

    private void OnTradfiPreset(object? sender, RoutedEventArgs e)
    {
        if ((sender as Control)?.Tag is not string key || string.IsNullOrWhiteSpace(key))
            return;
        _pendingTradfiPreset = key;
        // Apply known defaults immediately for UX; server clamps on save.
        switch (key)
        {
            case "wide":
                TradfiAbsGain = 3; TradfiRange = 5; TradfiTopN = 200; TradfiAdv = 0;
                break;
            case "balanced":
                TradfiAbsGain = 5; TradfiRange = 8; TradfiTopN = 120; TradfiAdv = 0;
                break;
            case "tight":
                TradfiAbsGain = 8; TradfiRange = 12; TradfiTopN = 80; TradfiAdv = 0;
                break;
            case "strict":
                TradfiAbsGain = 12; TradfiRange = 18; TradfiTopN = 50; TradfiAdv = 0;
                break;
        }
        DataContext = null;
        DataContext = this;
    }

    private void LoadEta(JsonElement prefs)
    {
        if (!prefs.TryGetProperty("eta", out var eta) || eta.ValueKind != JsonValueKind.Object)
            return;
        ApplyEtaObject(eta);
    }

    private void ApplyEtaObject(JsonElement eta)
    {
        _etaCalc.LoadCalibration(eta);
        var baseTitle = eta.TryGetProperty("title", out var t) ? t.GetString() ?? "Estimated scan time" : "Estimated scan time";
        EtaTitle = string.IsNullOrWhiteSpace(_etaCalc.BenchmarkRanAt)
            ? baseTitle
            : $"{baseTitle} (Benchmark calibrated · {LocalTimeFormat.FormatTimestamp(_etaCalc.BenchmarkRanAt)})";
        EtaTotal = eta.TryGetProperty("total", out var tot) ? tot.GetString() ?? "" : "";
        EtaNote = eta.TryGetProperty("note", out var note) ? note.GetString() ?? "" : "";
        EtaOverrun = ReadBool(eta, "overrun");
        EtaWarning = eta.TryGetProperty("overrun_warning", out var ow) ? ow.GetString() ?? "" : "";
        RecommendedIntervalMinutes = ReadDecimal(eta, "recommended_interval_minutes") ?? RecommendedIntervalMinutes;
        if (eta.TryGetProperty("lines", out var lines) && lines.ValueKind == JsonValueKind.Array)
        {
            var parts = new List<string>();
            foreach (var line in lines.EnumerateArray())
            {
                var s = line.GetString();
                if (!string.IsNullOrWhiteSpace(s))
                    parts.Add(s!);
            }
            EtaLines = string.Join("\n", parts);
        }
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(string.Empty));
    }

    private void RecalculateLiveEta()
    {
        if (_loadingPrefs)
            return;
        var enabledTfs = Timeframes.Where(t => t.Enabled).ToList();
        var nTf = Math.Max(1, enabledTfs.Count);
        var nStrat = Math.Max(1, Strategies.Count(s => s.Enabled));
        var hadSub = enabledTfs.Any(t => IsSubhour(t.Id));
        var res = _etaCalc.Compute(
            nStrat,
            nTf,
            hadSub,
            (double)MinVolume,
            RequireContinuous1h,
            MarketContext,
            SauceWithScan,
            (int)SauceTopN,
            AutoScanCrypto,
            AutoScanTradfi,
            AutoScanForex,
            (int)TradfiTopN,
            (int)IntervalMinutes);
        EtaLines = res.Lines;
        EtaTotal = res.Total;
        EtaOverrun = res.Overrun;
        EtaWarning = res.Warning;
        RecommendedIntervalMinutes = res.RecommendedIntervalMinutes;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(EtaLines)));
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(EtaTotal)));
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(EtaOverrun)));
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(EtaWarning)));
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(RecommendedIntervalMinutes)));
    }

    private void OnAutoAdjustInterval(object? sender, RoutedEventArgs e)
    {
        IntervalMinutes = RecommendedIntervalMinutes;
        EtaOverrun = false;
        EtaWarning = "";
        Note = $"Auto-scan interval adjusted to {IntervalMinutes}m (click Save to apply).";
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(string.Empty));
    }

    private async void OnRunBenchmark(object? sender, RoutedEventArgs e)
    {
        if (sender is Button btn)
            btn.IsEnabled = false;
        Note = "Running real-data 3-asset benchmark (1 coin · 1 stock · 1 FX + Secret Sauce)…";
        try
        {
            var win = new BenchmarkWindow(runLive: true);
            await win.ShowDialog(this);
            if (win.LastEtaDoc is { } etaDoc)
            {
                using (etaDoc)
                    ApplyEtaObject(etaDoc.RootElement);
                RecalculateLiveEta();
            }
            if (!win.BenchmarkSucceeded)
                Note = "Benchmark did not complete successfully — check Benchmark Results.";
            else
                Note = EtaOverrun
                    ? "Benchmark done — schedule overrun detected (click Auto-adjust interval)."
                    : "Benchmark done — ETA calibrated.";
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(string.Empty));
        }
        catch (Exception ex)
        {
            Note = $"Benchmark failed: {ex.Message}";
        }
        finally
        {
            if (sender is Button b)
                b.IsEnabled = true;
        }
    }

    private async void OnOpenBenchmarkResults(object? sender, RoutedEventArgs e)
    {
        var win = new BenchmarkWindow();
        win.LoadSavedResults();
        await win.ShowDialog(this);
    }

    private void BuildTfBands(JsonElement prefs)
    {
        TfBands.Clear();
        var enabled = Timeframes.ToDictionary(t => t.Id, t => t.Enabled, StringComparer.OrdinalIgnoreCase);
        var mixNote = prefs.TryGetProperty("subhour_mix_note", out var noteEl)
            ? noteEl.GetString() ?? ""
            : "";

        if (prefs.TryGetProperty("tf_bands", out var bands) && bands.ValueKind == JsonValueKind.Array
            && bands.GetArrayLength() > 0)
        {
            var list = bands.EnumerateArray().ToList();
            for (var i = 0; i < list.Count; i++)
            {
                var band = list[i];
                var id = band.TryGetProperty("id", out var idEl) ? idEl.GetString() ?? "" : "";
                var title = band.TryGetProperty("title", out var titleEl) ? titleEl.GetString() ?? id : id;
                var ids = new List<string>();
                if (band.TryGetProperty("timeframes", out var tfs) && tfs.ValueKind == JsonValueKind.Array)
                {
                    foreach (var tf in tfs.EnumerateArray())
                    {
                        var tfId = tf.ValueKind == JsonValueKind.String ? tf.GetString() : null;
                        if (!string.IsNullOrWhiteSpace(tfId))
                            ids.Add(tfId!);
                    }
                }
                AddBand(id, title, ids, enabled, mixNote, showSep: i < list.Count - 1);
            }
        }
        else
        {
            BuildTfBandsFallback(enabled, mixNote);
        }

        SyncTimeframesFromBands();
    }

    private void BuildTfBandsFallback(
        IReadOnlyDictionary<string, bool>? enabled = null,
        string mixNote = "")
    {
        TfBands.Clear();
        enabled ??= new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
        AddBand("subhour", "Sub-hour", SubhourFallback, enabled, mixNote, showSep: true);
        AddBand(
            "hours",
            "Hours (1h–24h) · live 30-day window",
            HoursFallback,
            enabled,
            mixNote: "",
            showSep: false);
        SyncTimeframesFromBands();
    }

    private void SyncTimeframesFromBands()
    {
        Timeframes.Clear();
        foreach (var band in TfBands)
        foreach (var row in band.Rows)
            Timeframes.Add(row);
    }

    private void AddBand(
        string id,
        string title,
        IEnumerable<string> tfIds,
        IReadOnlyDictionary<string, bool> enabled,
        string mixNote,
        bool showSep)
    {
        var group = new TfBandGroup
        {
            Id = id,
            Title = title,
            Note = mixNote,
            ShowNote = id == "subhour" && !string.IsNullOrWhiteSpace(mixNote),
            ShowSeparatorAfter = showSep,
        };
        foreach (var tf in tfIds)
        {
            var on = enabled.TryGetValue(tf, out var en) ? en : id == "hours";
            var row = new PrefToggleRow { Id = tf, Enabled = on };
            row.PropertyChanged += OnTfChanged;
            group.Rows.Add(row);
        }
        TfBands.Add(group);
    }

    private void OnTfChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName != nameof(PrefToggleRow.Enabled) || _suppressTfExclusivity)
            return;
        if (sender is PrefToggleRow { Enabled: true } row && !BandsMixReady)
            ClearOtherBand(row.Id);
        RefreshSummaries();
    }

    private void ClearOtherBand(string enabledId)
    {
        var sub = IsSubhour(enabledId);
        _suppressTfExclusivity = true;
        try
        {
            foreach (var band in TfBands)
            {
                var bandIsSub = band.Id == "subhour";
                if (bandIsSub == sub) continue;
                foreach (var row in band.Rows)
                    row.Enabled = false;
            }
        }
        finally
        {
            _suppressTfExclusivity = false;
        }
    }

    private static bool IsSubhour(string id) =>
        id.EndsWith("m", StringComparison.OrdinalIgnoreCase);

    private void OnBandAll(object? sender, RoutedEventArgs e)
    {
        if ((sender as Control)?.Tag is not TfBandGroup band) return;
        if (!BandsMixReady)
            ClearOtherBand(band.Rows.FirstOrDefault()?.Id ?? (band.Id == "subhour" ? "1m" : "1h"));
        _suppressTfExclusivity = true;
        try
        {
            foreach (var row in band.Rows) row.Enabled = true;
        }
        finally
        {
            _suppressTfExclusivity = false;
        }
        RefreshSummaries();
    }

    private void OnBandNone(object? sender, RoutedEventArgs e)
    {
        if ((sender as Control)?.Tag is not TfBandGroup band) return;
        _suppressTfExclusivity = true;
        try
        {
            foreach (var row in band.Rows) row.Enabled = false;
        }
        finally
        {
            _suppressTfExclusivity = false;
        }
        RefreshSummaries();
    }

    private void OnStrategiesCollectionChanged(object? sender, NotifyCollectionChangedEventArgs e)
    {
        if (e.NewItems is null) return;
        foreach (PrefToggleRow row in e.NewItems)
            row.PropertyChanged += OnStrategyChanged;
    }

    private void OnStrategyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName is nameof(PrefToggleRow.Enabled) or nameof(PrefToggleRow.Visible))
            RefreshSummaries();
    }

    private void ApplyStrategyFilter()
    {
        var q = StrategyFilter.Trim();
        VisibleStrategies.Clear();
        foreach (var row in Strategies)
        {
            row.Visible = string.IsNullOrEmpty(q)
                || row.Id.Contains(q, StringComparison.OrdinalIgnoreCase);
            if (row.Visible)
                VisibleStrategies.Add(row);
        }
        RefreshSummaries();
    }

    private void RefreshSummaries()
    {
        TfSummary = $"{Timeframes.Count(t => t.Enabled)}/{Timeframes.Count} on";
        StratSummary = $"{Strategies.Count(s => s.Enabled)}/{Strategies.Count} on";
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(TfSummary)));
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(StratSummary)));
        RecalculateLiveEta();
    }

    private void OnStratAll(object? sender, RoutedEventArgs e)
    {
        foreach (var row in VisibleStrategies) row.Enabled = true;
        RefreshSummaries();
    }

    private void OnStratNone(object? sender, RoutedEventArgs e)
    {
        foreach (var row in VisibleStrategies) row.Enabled = false;
        RefreshSummaries();
    }

    private async void OnBrowseOhlcvt(object? sender, RoutedEventArgs e)
    {
        var files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "Kraken OHLCVT ZIP",
            AllowMultiple = false,
            FileTypeFilter =
            [
                new FilePickerFileType("ZIP") { Patterns = ["*.zip"] },
                new FilePickerFileType("All") { Patterns = ["*.*"] },
            ],
        });
        if (files.Count > 0)
        {
            OhlcvtPath = files[0].TryGetLocalPath() ?? OhlcvtPath;
            DataContext = null;
            DataContext = this;
        }
    }

    private void OnCancel(object? sender, RoutedEventArgs e) => Close(false);

    private void OnSave(object? sender, RoutedEventArgs e)
    {
        try
        {
            if (!Timeframes.Any(t => t.Enabled))
            {
                Note = "Select at least one timeframe.";
                return;
            }
            if (!Strategies.Any(s => s.Enabled))
            {
                Note = "Select at least one strategy.";
                return;
            }

            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            MergeJson(FiltersPath, obj =>
            {
                obj["min_volume_usd"] = (double)MinVolume;
                obj["interval_minutes"] = (int)IntervalMinutes;
                obj["heatmap_enabled"] = Heatmap;
                obj["require_continuous_1h"] = RequireContinuous1h;
                var exchanges = new JsonArray();
                foreach (var row in Exchanges.Where(e => e.Enabled))
                    exchanges.Add(row.Id);
                obj["scan_exchanges"] = exchanges;
            });

            var payload = new JsonObject
            {
                ["market_context_with_scan"] = MarketContext,
                ["sauce_with_scan"] = SauceWithScan,
                ["sauce_top_n"] = (int)SauceTopN,
                ["ohlcvt_path"] = OhlcvtPath ?? "",
                ["ohlcvt_auto_tip"] = OhlcvtAutoTip,
                ["timeframes"] = ToToggleArray(Timeframes),
                ["strategies"] = ToToggleArray(Strategies),
                ["lane_prefs"] = new JsonObject
                {
                    ["auto_scan_crypto"] = AutoScanCrypto,
                    ["auto_scan_tradfi"] = AutoScanTradfi,
                    ["auto_scan_forex"] = AutoScanForex,
                },
                ["lane_scan_filters"] = new JsonObject
                {
                    ["tradfi"] = new JsonObject
                    {
                        ["min_abs_gain_pct"] = (double)TradfiAbsGain,
                        ["min_range_pct"] = (double)TradfiRange,
                        ["top_n"] = (int)TradfiTopN,
                        ["min_adv_usd"] = (double)TradfiAdv,
                        ["min_price"] = (double)TradfiPrice,
                        ["preset"] = _pendingTradfiPreset,
                    },
                },
                ["results_view"] = new JsonObject
                {
                    ["heatmap_enabled"] = Heatmap,
                    ["perfect_only"] = PerfectOnly,
                },
            };
            _pendingTradfiPreset = "";
            var tmp = Path.Combine(Path.GetTempPath(), $"trendalgo-scan-settings-{Guid.NewGuid():N}.json");
            File.WriteAllText(tmp, JsonNodeWrite.ToCompact(payload));
            try
            {
                using var result = _surfaces.ApplyScanSettings(tmp);
                if (result.RootElement.TryGetProperty("ok", out var ok) && ok.ValueKind == JsonValueKind.True)
                {
                    Close(true);
                    return;
                }
                var err = result.RootElement.TryGetProperty("error", out var errEl)
                    ? errEl.GetString()
                    : "apply_failed";
                Note = $"Save refused: {err}";
            }
            finally
            {
                try { File.Delete(tmp); } catch { /* ignore */ }
            }
        }
        catch (Exception ex)
        {
            Note = $"Save failed: {ex.Message}";
        }
    }

    private static JsonArray ToToggleArray(IEnumerable<PrefToggleRow> rows)
    {
        var arr = new JsonArray();
        foreach (var row in rows)
            arr.Add(new JsonObject { ["id"] = row.Id, ["enabled"] = row.Enabled });
        return arr;
    }

    private static void FillToggles(ObservableCollection<PrefToggleRow> dest, JsonElement root, string key)
    {
        dest.Clear();
        if (!root.TryGetProperty(key, out var arr) || arr.ValueKind != JsonValueKind.Array)
            return;
        foreach (var row in arr.EnumerateArray())
        {
            var id = row.TryGetProperty("id", out var idEl) ? idEl.GetString() ?? "" : "";
            if (string.IsNullOrWhiteSpace(id)) continue;
            var enabled = !row.TryGetProperty("enabled", out var en) || en.ValueKind != JsonValueKind.False;
            dest.Add(new PrefToggleRow { Id = id, Enabled = enabled });
        }
    }

    private static void MergeJson(string path, Action<JsonObject> edit)
    {
        JsonObject obj;
        if (File.Exists(path))
            obj = JsonNode.Parse(File.ReadAllText(path)) as JsonObject ?? new JsonObject();
        else
            obj = new JsonObject();
        edit(obj);
        File.WriteAllText(path, JsonNodeWrite.ToIndented(obj));
    }

    private static decimal? ReadDecimal(JsonElement root, params string[] keys)
    {
        foreach (var key in keys)
        {
            if (!root.TryGetProperty(key, out var p))
                continue;
            if (p.TryGetDecimal(out var d))
                return d;
            if (p.TryGetDouble(out var dbl))
                return (decimal)dbl;
            if (p.TryGetInt32(out var i))
                return i;
        }
        return null;
    }

    private static bool ReadBool(JsonElement root, string key, bool defaultValue = false)
    {
        if (!root.TryGetProperty(key, out var p))
            return defaultValue;
        return p.ValueKind switch
        {
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            _ => defaultValue,
        };
    }
}
