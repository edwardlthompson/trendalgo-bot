using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel : ViewModelBase
{
    private readonly ResultsDbReader _results = new();
    private readonly DeskCommandClient _desk = new();
    private readonly DeskSurfaceClient _surfaces = new();
    private DeskScanPoller? _scanPoll;
    private Action<string, string, string?>? _trayToast;
    private bool _filterPersistReady;
    private CancellationTokenSource? _filterDebounce;
    private string? _boardSortKey;
    private bool _boardSortAscending = true;
    private bool _surfaceBusy;
    private readonly HashSet<string> _expandedDesks = new(StringComparer.OrdinalIgnoreCase);

    public event Action? BoardReloaded;

    private static string WatchlistFiltersPath =>
        Path.Combine(ProfilePaths.DeviceRoot, "shell_watchlist_filters.json");

    public ObservableCollection<NavDestination> PrimaryNav { get; } = new();
    public ObservableCollection<NavDestination> MoreNav { get; } = new(ParityCatalog.More);
    public ObservableCollection<StrategyRow> StrategyRows { get; } = new();
    public ObservableCollection<OpportunityBoardRow> BoardRows { get; } = new();
    public BoardColumnFilterState QualifiedFilters { get; } = new();
    public BoardColumnFilterState WatchlistFilters { get; } = new();
    public BoardColumnFilterState BoardFilters =>
        BoardTab == "watchlist" ? WatchlistFilters : QualifiedFilters;
    public BacktestFilterState BacktestFilters { get; } = new();
    public string? BoardSortKey => _boardSortKey;
    public bool BoardSortAscending => _boardSortAscending;
    public bool ShowBoardColumnFilters => ShowBoard && BoardTab is not "logs";
    public bool ShowBacktestColumnFilters => ShowBacktestStrip && !BacktestEmpty;

    partial void OnShowBoardChanged(bool value) =>
        OnPropertyChanged(nameof(ShowBoardColumnFilters));

    partial void OnBoardTabChanged(string value)
    {
        OnPropertyChanged(nameof(ShowBoardColumnFilters));
        OnPropertyChanged(nameof(BoardFilters));
    }

    partial void OnShowBacktestStripChanged(bool value) =>
        OnPropertyChanged(nameof(ShowBacktestColumnFilters));

    partial void OnBacktestEmptyChanged(bool value) =>
        OnPropertyChanged(nameof(ShowBacktestColumnFilters));
    public ObservableCollection<DashboardModuleRow> DashboardModules { get; } = new();
    public ObservableCollection<DashboardMinRow> DashboardMinRows { get; } = new();
    public ObservableCollection<AlertRow> AlertRows { get; } = new();
    public ObservableCollection<BotPlanRow> BotRows { get; } = new();
    public ObservableCollection<BuyPickRow> BuyPickRows { get; } = new();
    public ObservableCollection<GlossaryRow> GlossaryRows { get; } = new();
    public ObservableCollection<NotifyKindRow> NotifyKinds { get; } = new();
    public ObservableCollection<SettingsLayoutRow> SettingsLayoutRows { get; } = new();
    public ObservableCollection<string> SettingsSections { get; } = new(
    [
        "connection", "appearance", "keys", "venue", "lanes",
        "dashboard", "privacy", "data", "notify", "about",
    ]);

    [ObservableProperty] private string _selectedNavId = "workbook";
    [ObservableProperty] private string _statusText = "TrendAlgo Shell — ADR-0021 dual-runtime";
    [ObservableProperty] private string _handshakeText = "No engine_ipc.json yet";
    [ObservableProperty] private string _pageTitle = "Results Workbook";
    [ObservableProperty] private string _pageBody = "Parity port — inventory §12.";
    [ObservableProperty] private bool _showWorkbook;
    [ObservableProperty] private bool _showSettings;
    [ObservableProperty] private bool _showDeskStrip;
    [ObservableProperty] private bool _showBoard;
    [ObservableProperty] private bool _showPoolWatch = true;
    [ObservableProperty] private bool _autoScan;
    [ObservableProperty] private bool _scanBusy;
    [ObservableProperty] private string _boardTab = "qualified";
    [ObservableProperty] private string _runId = "";
    [ObservableProperty] private int _rowCount;
    [ObservableProperty] private string _queryText = "";
    [ObservableProperty] private int _jobWorkers = 4;
    [ObservableProperty] private string _themeDensity = "comfortable";
    [ObservableProperty] private string _themeMode = "system";
    [ObservableProperty] private string _accentColor = "";
    [ObservableProperty] private OpportunityBoardRow? _selectedBoardRow;
    [ObservableProperty] private bool _showAlpacaCta;
    [ObservableProperty] private string _alpacaCtaText =
        "TradFi/Forex need Alpaca paper keys for live bars.";
    [ObservableProperty] private bool _showBacktestStrip;
    [ObservableProperty] private bool _showDashboard;
    [ObservableProperty] private bool _showAlerts;
    [ObservableProperty] private bool _showBots;
    [ObservableProperty] private string _alertTab = "logs";
    [ObservableProperty] private string _hostBadge = "local";
    [ObservableProperty] private string _hostBadgeLabel = "No host linked";
    [ObservableProperty] private string _backtestPair = "BTC/USD";
    [ObservableProperty] private bool _showBuyPicks;
    [ObservableProperty] private string _boardFilter = "";
    [ObservableProperty] private bool _showScanProgress;
    [ObservableProperty] private string _scanProgressText = "";
    [ObservableProperty] private bool _showGlossary;
    [ObservableProperty] private bool _showLogs;
    [ObservableProperty] private bool _showPoolWatchPage;
    [ObservableProperty] private bool _showDebug;
    public ObservableCollection<ExecutionLogRow> ExecutionLogRows { get; } = new();
    public ObservableCollection<SurfaceGridRow> PoolWatchRows { get; } = new();
    [ObservableProperty] private string _glossaryQuery = "";
    [ObservableProperty] private string _debugLogText = "";
    [ObservableProperty] private string _notifyRibbonText = "Notify: Windows toasts + Telegram stay on device path";
    [ObservableProperty] private bool _showForceFresh =
        string.Equals(
            Environment.GetEnvironmentVariable("TRENDALGO_DEBUG_SCAN"),
            "1",
            StringComparison.Ordinal);
    [ObservableProperty] private bool _showBilling;
    [ObservableProperty] private string _billingTitle = "Billing";
    [ObservableProperty] private string _billingBody = "";
    [ObservableProperty] private string _billingSettleHelp = "";
    [ObservableProperty] private string _aboutText = "";
    [ObservableProperty] private string _marketContextText = "";
    [ObservableProperty] private bool _buyPicksExpanded = true;
    [ObservableProperty] private string _buyPicksSubtitle =
        "Consensus scores for every pair on the filtered board — plus top TA gain when All-TA ran";
    [ObservableProperty] private string _botsPrefillNote = "";
    private Views.ScanProgressWindow? _progressWin;
    [ObservableProperty] private string _deskLoadPct = "";
    [ObservableProperty] private string _lastScanText = "Last scan: Never";
    [ObservableProperty] private string _poolWatchLastScanText = "Last scan: Never";
    [ObservableProperty] private string _dashboardRange = "1M";
    [ObservableProperty] private bool _dashboardDemo;
    [ObservableProperty] private string _dashboardPageTitle = "Main";
    [ObservableProperty] private string _dashboardCalendarCta = "Calendar setup — wire ICS keys for Events module";
    [ObservableProperty] private double _dashboardCanvasHeight = 480;
    [ObservableProperty] private double _dashboardCanvasWidth = 960;
    [ObservableProperty] private string _hostPollCaption = "Host poll: off";
    [ObservableProperty] private string _hostSafetyLights = "Safety: local · flatten=idle · journal=idle";
    [ObservableProperty] private string _settingsSection = "notify";
    [ObservableProperty] private bool _showNotifyMatrix;
    [ObservableProperty] private bool _showDashboardMins;
    [ObservableProperty] private bool _showVenueEditor;
    [ObservableProperty] private bool _showKeysEditor;
    [ObservableProperty] private string _venueChoice = "host";
    [ObservableProperty] private bool _venueAck;
    [ObservableProperty] private bool _venueAckLocked;
    [ObservableProperty] private string _venueDisclosure = "";
    [ObservableProperty] private bool _showLanesEditor;
    [ObservableProperty] private string _lanesHint = "";
    [ObservableProperty] private string _lanesAlpacaHint = "";
    [ObservableProperty] private bool _lanesAlpacaKeyed;
    [ObservableProperty] private bool _laneAutoCrypto = true;
    [ObservableProperty] private bool _laneAutoTradfi;
    [ObservableProperty] private bool _laneAutoForex;
    [ObservableProperty] private bool _showAppearanceEditor;
    public string[] AppearanceThemeChoices { get; } = ShellTheme.ThemeChoices;
    public string[] AppearanceAccentChoices { get; } = ShellTheme.AccentPresets;
    [ObservableProperty] private bool _showConnectionEditor;
    [ObservableProperty] private string _connectionOwnerId = "";
    [ObservableProperty] private string _connectionHostUrl = "";
    [ObservableProperty] private string _connectionCertPin = "";
    [ObservableProperty] private string _connectionHelp = "";
    [ObservableProperty] private bool _connectionFirstRun;
    [ObservableProperty] private bool _settingsLayoutEdit;
    [ObservableProperty] private bool _showSettingsLayout;
    [ObservableProperty] private string _settingsLayoutHelp = "";
    [ObservableProperty] private string _settingsNoSecret = "";
    [ObservableProperty] private SettingsLayoutRow? _selectedSettingsLayoutRow;
    [ObservableProperty] private bool _showPrivacyEditor;
    [ObservableProperty] private bool _privacySaveCrashes;
    [ObservableProperty] private string _privacyLabel = "";
    [ObservableProperty] private string _privacyHelp = "";
    [ObservableProperty] private bool _showDataEditor;
    [ObservableProperty] private string _dataHelp = "";
    [ObservableProperty] private string _dataExportDir = "";
    [ObservableProperty] private bool _dataUseUtc;
    [ObservableProperty] private string _dataUseUtcLabel = "";
    [ObservableProperty] private string _dataUseUtcHelp = "";
    [ObservableProperty] private string _dataProfileRoot = "";
    [ObservableProperty] private bool _showUpdatesEditor;
    [ObservableProperty] private string _updatesVersionLine = "";
    [ObservableProperty] private string _updatesSupport = "";
    [ObservableProperty] private string _updatesStatus = "";
    [ObservableProperty] private string _updatesChangelogUrl = "";
    [ObservableProperty] private string _updatesLastSeen = "";
    [ObservableProperty] private bool _showExportHub;
    [ObservableProperty] private string _exportHubTitle = "Export";
    [ObservableProperty] private string _exportHubSubtitle = "";
    [ObservableProperty] private string _exportHubFolder = "";
    [ObservableProperty] private string _exportHubFolderHelp = "";
    [ObservableProperty] private string _exportHubStatus = "";
    [ObservableProperty] private string _exportJournalLabel = "Export journal (CSV)";
    [ObservableProperty] private string _exportPlanLabel = "Export plan (JSON)";
    [ObservableProperty] private string _exportScanLabel = "Export latest scan (JSON)";
    [ObservableProperty] private bool _backtestEmpty;
    [ObservableProperty] private string _backtestEmptyTitle = "No pair scan yet";
    [ObservableProperty] private string _backtestEmptyBody = "";
    [ObservableProperty] private string _backtestStrategyCaption = "Strategy results";
    [ObservableProperty] private bool _backtestPerfectOnly;
    [ObservableProperty] private string _backtestPerfectLabel = "Perfect Strategies";
    [ObservableProperty] private string _backtestRunLabel = "Scan";
    [ObservableProperty] private string _backtestRefreshLabel = "Refresh prices";
    [ObservableProperty] private string _backtestStatusLabel = "Scan status";
    [ObservableProperty] private bool _backtestMarketCtxCollapsed;
    [ObservableProperty] private string _notifyHelp = "";
    [ObservableProperty] private bool _notifyAutostart = true;
    [ObservableProperty] private string _notifyGrokHelp = "";
    [ObservableProperty] private string _planDraftName = "";
    [ObservableProperty] private string _planDraftPair = "BTC/USD";
    [ObservableProperty] private string _planDraftStrategy = "RSI";
    [ObservableProperty] private string _planDraftTimeframe = "1h";
    [ObservableProperty] private string _planDraftStake = "25";
    [ObservableProperty] private string _settingsEditorBody = "";
    [ObservableProperty] private string _settingsEditorNote = "";

    public MainViewModel()
    {
        var sw = Stopwatch.StartNew();
        BoardColumnFilterStore.Load(QualifiedFilters);
        BoardColumnFilterStore.Load(WatchlistFilters, WatchlistFiltersPath);
        var savedSort = BoardSortStore.Load();
        if (savedSort is not null)
        {
            _boardSortKey = savedSort.ColumnKey;
            _boardSortAscending = savedSort.Ascending;
        }
        QualifiedFilters.PropertyChanged += OnBoardFiltersPropertyChanged;
        WatchlistFilters.PropertyChanged += OnBoardFiltersPropertyChanged;
        _filterPersistReady = true;
        LoadBuyPicksCollapsedPref();
        var (theme, accent) = ShellTheme.LoadFromSettings();
        ThemeMode = theme;
        AccentColor = accent;
        RefreshHandshake();
        RefreshHostBadge();
        var savedNav = ShellNavStore.Load();
        var startId = savedNav?.NavId;
        if (string.IsNullOrWhiteSpace(startId)
            || (startId != "poolwatch"
                && !ParityCatalog.Primary.Concat(ParityCatalog.More).Any(n => n.Id == startId)))
            startId = "crypto";
        if (!string.IsNullOrWhiteSpace(savedNav?.BoardTab))
            BoardTab = savedNav!.BoardTab == "logs" ? "qualified" : savedNav!.BoardTab;
        if (ParityCatalog.ShowsDeskStrip(startId))
            _expandedDesks.Add(startId);
        else
            _expandedDesks.Add("crypto");
        InitPrimaryNav();
        UpdatePrimaryNavExpansion();
        Navigate(startId);
        StartAutoScanScheduler();
        sw.Stop();
    }

    private void InitPrimaryNav()
    {
        PrimaryNav.Clear();
        foreach (var item in ParityCatalog.Primary)
        {
            PrimaryNav.Add(item);
            if (item.Id == "settings")
            {
                foreach (var (subId, subLabel) in ParityCatalog.SettingsSubItems)
                    PrimaryNav.Add(new(subId, subLabel, "settings", isSubItem: true, parentDesk: "settings"));
                continue;
            }
            if (!ParityCatalog.ShowsDeskStrip(item.Id))
                continue;
            PrimaryNav.Add(new($"{item.Id}:qualified", "↳ Qualified", "qualified", isSubItem: true, parentDesk: item.Id));
            PrimaryNav.Add(new($"{item.Id}:watchlist", "↳ Watchlist", "watchlist", isSubItem: true, parentDesk: item.Id));
            if (item.Id == "crypto")
                PrimaryNav.Add(new("crypto:poolwatch", "↳ Pool watch", "poolwatch", isSubItem: true, parentDesk: "crypto"));
        }
    }

    private void UpdatePrimaryNavExpansion()
    {
        foreach (var item in PrimaryNav)
        {
            if (ParityCatalog.ShowsDeskStrip(item.Id))
                item.SetDeskHeaderLabel(
                    _expandedDesks.Contains(item.Id),
                    ParseDeskLoadPercent(_results.JobState($"scan:{item.Id}")));
            else if (item.Id == "settings")
                item.SetDeskHeaderLabel(_expandedDesks.Contains("settings"), null);
            else if (item.ParentDesk is not null)
                item.IsVisible = _expandedDesks.Contains(item.ParentDesk);
        }
    }

    public void SaveBoardSort(string columnKey, bool ascending)
    {
        _boardSortKey = columnKey;
        _boardSortAscending = ascending;
        BoardSortStore.Save(columnKey, ascending);
    }

    public void SetBoardSort(string columnKey, bool ascending)
    {
        _boardSortKey = columnKey;
        _boardSortAscending = ascending;
        BoardSortStore.Save(columnKey, ascending);
        if (BoardRows.Count == 0)
            return;
        var sorted = BoardRowSorter.Sort(BoardRows, columnKey, ascending);
        BoardRows.Clear();
        foreach (var row in sorted)
            BoardRows.Add(row);
    }

    private void OnBoardFiltersPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (!_filterPersistReady)
            return;
        // Option sync fields also raise PropertyChanged — debounce covers those.
        _filterDebounce?.Cancel();
        _filterDebounce = new CancellationTokenSource();
        var token = _filterDebounce.Token;
        _ = DebouncedPersistFiltersAsync(token);
    }

    private async Task DebouncedPersistFiltersAsync(CancellationToken token)
    {
        try
        {
            await Task.Delay(350, token);
            BoardColumnFilterStore.Save(QualifiedFilters);
            BoardColumnFilterStore.Save(WatchlistFilters, WatchlistFiltersPath);
            if (ShowBoard && BoardTab is not "logs")
                ReloadBoard();
        }
        catch (TaskCanceledException)
        {
            /* newer edit */
        }
    }

    public void AttachTrayToast(Action<string, string, string?> toast) =>
        _trayToast = toast;

    public void Toast(string title, string body, string? kind = null) =>
        _trayToast?.Invoke(title, body, kind);

    [RelayCommand]
    private void Navigate(string? id)
    {
        if (string.IsNullOrWhiteSpace(id))
            return;
        if (id is "crypto:poolwatch" or "poolwatch")
        {
            _expandedDesks.Add("crypto");
            id = "poolwatch";
            UpdatePrimaryNavExpansion();
        }
        else if (id == "alerts")
        {
            _expandedDesks.Add("settings");
            UpdatePrimaryNavExpansion();
            SettingsSection = "notify";
            id = "settings";
        }
        else if (id.StartsWith("settings:", StringComparison.OrdinalIgnoreCase))
        {
            var sec = NormalizeSettingsSection(id["settings:".Length..]);
            _expandedDesks.Add("settings");
            UpdatePrimaryNavExpansion();
            SettingsSection = sec;
            id = "settings";
        }
        else if (id == "settings")
        {
            if (SelectedNavId is "settings" or "billing" or "glossary" or "debug")
            {
                if (!_expandedDesks.Remove("settings"))
                    _expandedDesks.Add("settings");
                UpdatePrimaryNavExpansion();
                OnPropertyChanged(nameof(SelectedNavId));
                return;
            }
            _expandedDesks.Add("settings");
            UpdatePrimaryNavExpansion();
        }
        else if (id.Contains(':', StringComparison.Ordinal))
        {
            var parts = id.Split(':', 2);
            var lane = parts[0];
            var tab = parts[1];
            _expandedDesks.Add(lane);
            BoardTab = tab;
            id = lane;
            UpdatePrimaryNavExpansion();
        }
        else if (ParityCatalog.ShowsDeskStrip(id))
        {
            var sameDesk = SelectedNavId == id && ShowBoard
                || (id == "crypto" && SelectedNavId == "poolwatch");
            if (sameDesk)
            {
                if (!_expandedDesks.Remove(id))
                    _expandedDesks.Add(id);
                UpdatePrimaryNavExpansion();
                OnPropertyChanged(nameof(SelectedNavId));
                return;
            }
            _expandedDesks.Add(id);
            if (BoardTab is not "qualified" and not "watchlist")
                BoardTab = "qualified";
            UpdatePrimaryNavExpansion();
        }
        SelectedNavId = id;
        ShellNavStore.Save(id, BoardTab);
        ShowWorkbook = ParityCatalog.ShowsWorkbook(id) && !ParityCatalog.ShowsDeskStrip(id);
        ShowSettings = id == "settings";
        ShowDeskStrip = ParityCatalog.ShowsDeskStrip(id);
        ShowBoard = ParityCatalog.ShowsDeskStrip(id);
        ShowBacktestStrip = id == "backtest";
        ShowDashboard = id == "dashboard";
        ShowAlerts = id == "alerts";
        ShowBots = id == "bots";
        ShowGlossary = id == "glossary";
        ShowLogs = id == "logs";
        ShowPoolWatchPage = id == "poolwatch";
        ShowDebug = id == "debug";
        ShowBilling = id == "billing";
        ShowPoolWatch = ParityCatalog.ShowsPoolWatch(id);
        PageTitle = ParityCatalog.Title(id);
        PageBody = ParityCatalog.Body(id);
        RefreshHostBadge();
        if (ShowBoard)
        {
            RefreshAlpacaCta();
            ReloadBoard();
        }
        else
        {
            ShowAlpacaCta = false;
            if (ShowBots)
                BotsReload();
            else if (ShowAlerts)
                AlertsReload();
            else if (ShowDashboard)
                DashboardReload();
            else if (ShowBacktestStrip)
                BacktestReload();
            else if (ShowWorkbook)
                ReloadWorkbook();
            else if (ShowGlossary)
                GlossarySearch();
            else if (ShowLogs)
                LogsReload();
            else if (ShowPoolWatchPage)
                PoolWatchReload();
            else if (ShowDebug)
                DebugReload();
            else if (ShowBilling)
                BillingReload();
            else if (id == "settings")
            {
                AboutReload();
                NotifyReload();
                SettingsLayoutReload();
                SelectSettingsSection(SettingsSection);
            }
            else if (id == "export")
                ExportHubReload();
            else if (id == "wizards")
                MoreSurfaceNote();
        }
        ShowExportHub = id == "export" || (id == "settings" && SettingsSection == "data");
    }

    [RelayCommand]
    private void OpenAlpacaWizard()
    {
        Navigate("wizards");
        StatusText = "Alpaca wizard — full CredMan UI lands with AV-G10; use device Settings for now.";
    }

    private void RefreshHostBadge()
    {
        try
        {
            var settingsPath = Path.Combine(ProfilePaths.DeviceRoot, "settings.json");
            var hostUrl = "";
            if (File.Exists(settingsPath))
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(settingsPath));
                if (doc.RootElement.TryGetProperty("host_url", out var hu))
                    hostUrl = hu.GetString()?.Trim() ?? "";
            }
            var hasSecret = !string.IsNullOrEmpty(
                new WindowsCredManStore().Read("TrendAlgo/owner-secret"));
            var linked = !string.IsNullOrEmpty(hostUrl) && hasSecret;
            HostBadge = linked ? "linked" : "local";
            HostBadgeLabel = linked ? "Host linked" : "No host linked";
        }
        catch
        {
            HostBadge = "local";
            HostBadgeLabel = "No host linked";
        }
    }

    private void RefreshAlpacaCta()
    {
        var lane = DeskLane();
        if (lane == "crypto")
        {
            ShowAlpacaCta = false;
            return;
        }
        try
        {
            var vault = new WindowsCredManStore();
            var hasKey = !string.IsNullOrEmpty(vault.Read(CredManTargets.AlpacaKey));
            var hasSec = !string.IsNullOrEmpty(vault.Read(CredManTargets.AlpacaSecret));
            ShowAlpacaCta = !(hasKey && hasSec);
            AlpacaCtaText = lane == "forex"
                ? "Forex: add Alpaca keys (or rely on AlgoSpecial H1). Bot vs B&H uses Bars src column."
                : "TradFi: connect Alpaca paper keys to scan equities on this desk.";
        }
        catch
        {
            ShowAlpacaCta = false;
        }
    }

    [RelayCommand]
    private void SelectBoardTab(string? tab)
    {
        if (string.IsNullOrWhiteSpace(tab))
            return;
        BoardTab = tab.Trim().ToLowerInvariant();
        ShellNavStore.Save(SelectedNavId, BoardTab);
        ReloadBoard();
    }

    [RelayCommand]
    private void ReloadBoard()
    {
        var sw = Stopwatch.StartNew();
        BoardRows.Clear();
        OnPropertyChanged(nameof(ShowBoardColumnFilters));
        if (BoardTab == "logs")
            BoardTab = "qualified";
        var rows = LaneBoardLoader.Load(DeskLane(), BoardTab);
        IEnumerable<OpportunityBoardRow> filtered = BoardColumnFilter.Apply(rows, BoardFilters);
        if (!string.IsNullOrWhiteSpace(BoardFilter))
        {
            var needle = BoardFilter.Trim();
            filtered = filtered.Where(r =>
                r.Pair.Contains(needle, StringComparison.OrdinalIgnoreCase)
                || r.Exchange.Contains(needle, StringComparison.OrdinalIgnoreCase)
                || r.Health.Contains(needle, StringComparison.OrdinalIgnoreCase));
        }
        foreach (var row in BoardRowSorter.Sort(filtered, _boardSortKey, _boardSortAscending))
            BoardRows.Add(row);
        RowCount = BoardRows.Count;
        sw.Stop();
        var job = _results.JobState($"scan:{DeskLane()}") ?? "idle";
        StatusText = $"{DeskLane()} / {BoardTab}: {RowCount} rows · {sw.ElapsedMilliseconds}ms · job={job}";
        RefreshDeskLoadPct();
        RefreshLastScanText();
        if (BoardTab == "qualified")
            _ = ReloadBuyPicksAsync();
        else
            ShowBuyPicks = false;
        RefreshHandshake();
        BoardReloaded?.Invoke();
    }

    [RelayCommand]
    private void PoolWatchReload()
    {
        PoolWatchRows.Clear();
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "dex_watch_rows.json");
            if (!File.Exists(path))
            {
                PoolWatchLastScanText = "Last scan: Never";
                StatusText = "Pool watch: 0 pools (click Scan pools)";
                return;
            }
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            DateTimeOffset? savedAt = null;
            if (doc.RootElement.ValueKind == JsonValueKind.Object
                && doc.RootElement.TryGetProperty("saved_at", out var sa)
                && LocalTimeFormat.TryParseToLocal(sa.GetString(), out var parsedAt))
            {
                savedAt = parsedAt;
            }
            else
            {
                savedAt = new DateTimeOffset(File.GetLastWriteTimeUtc(path), TimeSpan.Zero);
            }
            PoolWatchLastScanText = LocalTimeFormat.FormatLastScan(savedAt);
            JsonElement rowsEl;
            if (doc.RootElement.ValueKind == JsonValueKind.Array)
                rowsEl = doc.RootElement;
            else if (doc.RootElement.TryGetProperty("rows", out var r) && r.ValueKind == JsonValueKind.Array)
                rowsEl = r;
            else
                return;

            foreach (var r in rowsEl.EnumerateArray())
            {
                var pair = r.TryGetProperty("pair", out var pe) ? pe.ToString() : "";
                var liq = r.TryGetProperty("liquidity_usd", out var le) && le.TryGetDouble(out var lv)
                    ? MoneyFormat.Usd(lv) : "—";
                var chg = r.TryGetProperty("price_change_24h_pct", out var ce) ? ce.ToString() : "—";
                var vol = r.TryGetProperty("volume_proxy_usd", out var ve) && ve.TryGetDouble(out var vv)
                    ? MoneyFormat.Usd(vv) : "—";
                var src = r.TryGetProperty("source", out var se) ? se.ToString() : "";
                PoolWatchRows.Add(new SurfaceGridRow { Col1 = pair, Col2 = liq, Col3 = chg, Col4 = vol, Col5 = src });
            }
            StatusText = $"Pool watch: {PoolWatchRows.Count} pools";
        }
        catch (Exception ex)
        {
            StatusText = $"Pool watch load failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task PoolWatchScan()
    {
        StatusText = "Scanning DEX pools…";
        try
        {
            await Task.Run(() =>
            {
                _desk.Enqueue("pool_watch", "crypto");
                var psi = EngineProcessRunner.CreateResultsStorePsi(
                    EngineProcessRunner.FindRepoRoot(), redirectOutput: true);
                psi.ArgumentList.Add("--desk-once");
                psi.ArgumentList.Add("--lane");
                psi.ArgumentList.Add("crypto");
                using var proc = System.Diagnostics.Process.Start(psi);
                proc?.WaitForExit(45_000);
            });
            PoolWatchReload();
        }
        catch (Exception ex)
        {
            StatusText = $"Pool watch scan failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void LogsReload()
    {
        ExecutionLogRows.Clear();
        try
        {
            var collected = new List<(string SortKey, ExecutionLogRow Row)>();
            var path = Path.Combine(ProfilePaths.DeviceRoot, "execution_logs.jsonl");
            if (File.Exists(path))
            {
                var lines = File.ReadAllLines(path);
                var keptLines = new List<string>(lines.Length);
                var pruned = false;
                for (var i = lines.Length - 1; i >= 0 && collected.Count < 300; i--)
                {
                    var line = lines[i].Trim();
                    if (line.Length == 0)
                        continue;
                    try
                    {
                        using var doc = JsonDocument.Parse(line);
                        var r = doc.RootElement;
                        var kind = r.TryGetProperty("kind", out var ke) ? ke.ToString() : "";
                        if (kind is "board_load" or "startup" or "nav" or "menu")
                        {
                            pruned = true;
                            continue;
                        }
                        keptLines.Add(line);
                        var iso = r.TryGetProperty("iso", out var ie) ? ie.ToString() : "";
                        long? unixTs = r.TryGetProperty("ts", out var tse) && tse.TryGetInt64(out var tv0)
                            ? tv0
                            : null;
                        var timeText = unixTs is > 946_684_800
                            ? LocalTimeFormat.FormatFromUnixSeconds(unixTs.Value)
                            : LocalTimeFormat.FormatTimestamp(iso);
                        var sortKey = LocalTimeFormat.SortKeyUtc(iso, unixTs);
                        var lane = r.TryGetProperty("lane", out var le) ? le.ToString() : "";
                        var pair = r.TryGetProperty("pair", out var pe) ? pe.ToString() : "";
                        var scope = string.IsNullOrWhiteSpace(pair) ? lane : $"{lane} · {pair}";
                        var sec = r.TryGetProperty("total_s", out var te) && te.TryGetDouble(out var tv) ? tv : 0;
                        var dur = sec <= 0 ? "—" : sec < 1.0 ? $"{sec * 1000:0}ms" : sec < 90.0 ? $"{sec:0.0}s" : $"{sec / 60.0:0.0}m";
                        var stages = "";
                        if (r.TryGetProperty("stages", out var st) && st.ValueKind == JsonValueKind.Object)
                        {
                            stages = string.Join(" · ", st.EnumerateObject()
                                .Select(p => $"{p.Name}={p.Value}"));
                        }
                        var summary = r.TryGetProperty("summary", out var se) ? se.ToString() : "";
                        collected.Add((sortKey, new ExecutionLogRow(timeText, kind, scope, dur, stages, summary)));
                    }
                    catch { /* skip malformed line */ }
                }
                if (pruned)
                {
                    try
                    {
                        keptLines.Reverse();
                        File.WriteAllLines(path, keptLines);
                    }
                    catch { /* best-effort cleanup */ }
                }
            }
            var alertsPath = Path.Combine(ProfilePaths.DeviceRoot, "scanner_alerts.json");
            if (File.Exists(alertsPath))
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(alertsPath));
                if (doc.RootElement.TryGetProperty("alerts", out var alerts) && alerts.ValueKind == JsonValueKind.Array)
                {
                    foreach (var a in alerts.EnumerateArray().Take(120))
                    {
                        var rawKind = a.TryGetProperty("kind", out var ke) ? ke.ToString() : "";
                        var displayKind = rawKind switch
                        {
                            "trade_alert" => "trade",
                            "qualified_enter" => "entered",
                            "watchlist_leave" => "left",
                            _ => "",
                        };
                        if (string.IsNullOrEmpty(displayKind))
                            continue;
                        var at = a.TryGetProperty("at", out var ae) ? ae.ToString() : "";
                        var pair = a.TryGetProperty("pair", out var pe) ? pe.ToString() : "";
                        if (string.IsNullOrWhiteSpace(pair))
                            pair = a.TryGetProperty("symbol", out var se) ? se.ToString() : "";
                        var reason = a.TryGetProperty("reason", out var re) ? re.ToString() : "";
                        var timeText = FormatAlertTime(at);
                        collected.Add((LocalTimeFormat.SortKeyUtc(at), new ExecutionLogRow(timeText, displayKind, pair, "—", "", reason)));
                    }
                }
                if (doc.RootElement.TryGetProperty("trades", out var trades) && trades.ValueKind == JsonValueKind.Array)
                {
                    foreach (var t in trades.EnumerateArray().TakeLast(50).Reverse())
                    {
                        var at = t.TryGetProperty("at", out var ae) ? ae.ToString() : "";
                        var pair = t.TryGetProperty("pair", out var pe) ? pe.ToString() : "";
                        var reason = t.TryGetProperty("reason", out var re) ? re.ToString() : "";
                        var timeText = FormatAlertTime(at);
                        collected.Add((LocalTimeFormat.SortKeyUtc(at), new ExecutionLogRow(timeText, "trade", pair, "—", "", reason)));
                    }
                }
            }
            foreach (var item in collected.OrderByDescending(x => x.SortKey, StringComparer.Ordinal))
                ExecutionLogRows.Add(item.Row);
            StatusText = $"Execution logs: {ExecutionLogRows.Count} entries";
        }
        catch (Exception ex)
        {
            StatusText = $"Logs load failed: {ex.Message}";
        }
    }

    private static string FormatAlertTime(string iso) => LocalTimeFormat.FormatTimestamp(iso);

    private static void AppendTimingLog(string kind, string lane, double totalSeconds, string summary)
    {
        try
        {
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var path = Path.Combine(ProfilePaths.DeviceRoot, "execution_logs.jsonl");
            var obj = new JsonObject
            {
                ["ts"] = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                ["iso"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                ["kind"] = kind,
                ["lane"] = lane,
                ["pair"] = "",
                ["total_s"] = Math.Round(totalSeconds, 4),
                ["stages"] = new JsonObject(),
                ["summary"] = summary,
            };
            File.AppendAllText(path, JsonNodeWrite.ToCompact(obj) + Environment.NewLine);
        }
        catch { /* telemetry best-effort */ }
    }

    partial void OnBuyPicksExpandedChanged(bool value) => PersistBuyPicksCollapsed(!value);

    private static void PersistBuyPicksCollapsed(bool collapsed)
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "results_view_prefs.json");
            JsonObject root;
            if (File.Exists(path))
            {
                root = JsonNode.Parse(File.ReadAllText(path)) as JsonObject ?? new JsonObject();
            }
            else
                root = new JsonObject();
            root["buy_picks_collapsed"] = collapsed;
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(path, JsonNodeWrite.ToIndented(root));
        }
        catch
        {
            /* prefs best-effort */
        }
    }

    private void LoadBuyPicksCollapsedPref()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "results_view_prefs.json");
            if (!File.Exists(path))
                return;
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            if (doc.RootElement.TryGetProperty("buy_picks_collapsed", out var p)
                && p.ValueKind is JsonValueKind.True or JsonValueKind.False)
            {
                BuyPicksExpanded = p.ValueKind != JsonValueKind.True;
            }
        }
        catch
        {
            /* ignore */
        }
    }

    [RelayCommand]
    private void DeskRunScan()
    {
        var checkedLanes = AutoScanSchedulerService.LoadConfig().EnabledLanes();
        if (checkedLanes.Count >= 2 || (checkedLanes.Count == 1 && checkedLanes[0] != DeskLane()))
            EnqueueDesk("run_all_scans", busy: true, lanes: checkedLanes);
        else
            EnqueueDesk("run_scan", busy: true);
    }

    [RelayCommand]
    private void DeskRunAllScans() =>
        EnqueueDesk("run_all_scans", busy: true, lanes: AutoScanSchedulerService.LoadConfig().EnabledLanes());

    [RelayCommand]
    private void DeskForceFresh()
    {
        if (!ShowForceFresh)
        {
            StatusText = "Force-fresh needs TRENDALGO_DEBUG_SCAN=1";
            return;
        }
        StatusText = "Force fresh scan: caches cleared. Starting live scan…";
        EnqueueDesk("run_scan", busy: true, forceFresh: true);
    }

    [RelayCommand]
    private void DeskCancel() => EnqueueDesk("cancel_scan", busy: false);

    [RelayCommand]
    private async Task DeskOpenSettings()
    {
        try
        {
            EnqueueDesk("open_settings");
            if (Avalonia.Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime
                {
                    MainWindow: { } owner
                })
            {
                StatusText = "Loading scan settings…";
                var dlg = await LoadingWindow.RunAsync(
                    owner, "Loading scan settings…", ScanSettingsWindow.CreateLoadedAsync);
                var saved = await dlg.ShowDialog<bool?>(owner);
                if (saved == true)
                    RefreshAutoScanScheduler();
                StatusText = saved == true
                    ? "Scan settings saved — ready to Run scan"
                    : "Scan settings closed";
            }
        }
        catch (Exception ex)
        {
            StatusText = $"Settings failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task DeskRunSauce()
    {
        EnqueueDesk("run_sauce");
        await OpenSurfaceAsync("sauce", SelectedBoardRow?.Pair ?? "");
    }

    [RelayCommand]
    private async Task DeskPoolWatch()
    {
        EnqueueDesk("pool_watch");
        await OpenSurfaceAsync("dex", "");
    }

    [RelayCommand]
    private async Task OpenBoardResults() =>
        await OpenSurfaceAsync("results", SelectedBoardRow?.Pair ?? FirstBoardPair());

    [RelayCommand]
    private async Task OpenBoardResultsForRow(OpportunityBoardRow? row)
    {
        if (row is not null)
            SelectedBoardRow = row;
        var pair = row?.Pair ?? SelectedBoardRow?.Pair ?? FirstBoardPair();
        await OpenSurfaceAsync("results", pair);
    }

    [RelayCommand]
    private async Task OpenBoardChart() => await OpenChartWindowAsync("30d");

    [RelayCommand]
    private async Task OpenBoardChart7d() => await OpenChartWindowAsync("7d");

    [RelayCommand]
    private async Task OpenBoardChart30d() => await OpenChartWindowAsync("30d");

    [RelayCommand]
    private async Task OpenBoardChartWindow(string? windowKey) =>
        await OpenChartWindowAsync(string.IsNullOrWhiteSpace(windowKey) ? "30d" : windowKey);

    private async Task OpenChartWindowAsync(string windowKey)
    {
        var pair = SelectedBoardRow?.Pair ?? FirstBoardPair();
        if (string.IsNullOrWhiteSpace(pair))
        {
            StatusText = "Select a board row to open chart";
            return;
        }
        await OpenSurfaceAsync("chart", $"{pair}|{windowKey}");
    }

    [RelayCommand]
    private async Task OpenBoardEvents() =>
        await OpenSurfaceAsync("events", SelectedBoardRow?.Pair ?? FirstBoardPair());

    [RelayCommand]
    private void DeskRefreshPrices() => EnqueueDesk("refresh_prices");

    [RelayCommand]
    private async Task DeskShare() => await ShareBoardPngAsync();

    /// <summary>
    /// Context share: Qualified/Watchlist → visible list PNG; Backtest → strategy sheet for pair.
    /// </summary>
    [RelayCommand]
    private async Task ShareStrategyPng()
    {
        if (ShowBoard && !ShowBacktestStrip)
        {
            await ShareBoardPngAsync();
            return;
        }
        await ShareStrategySheetPngAsync(
            string.IsNullOrWhiteSpace(BacktestPair) ? FirstBoardPair() : BacktestPair);
    }

    private async Task ShareBoardPngAsync()
    {
        string? filtersPath = null;
        try
        {
            EnqueueDesk("share_board");
            var visible = BoardRows
                .Select(r => r.Pair)
                .Where(p => !string.IsNullOrWhiteSpace(p))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();
            var tab = string.IsNullOrWhiteSpace(BoardTab) ? "qualified" : BoardTab;
            var title = $"Scanner · {visible.Count} pairs";
            if (!string.Equals(tab, "qualified", StringComparison.OrdinalIgnoreCase))
                title = $"{char.ToUpperInvariant(tab[0])}{tab[1..]} · {visible.Count} pairs";
            var suggested = $"scanner-{DeskLane()}-{tab}-{DateTime.Now:yyyy-MM-dd}.png";
            var dest = await SharePngPicker.PickFromMainAsync(suggested);
            if (dest is null)
            {
                StatusText = "Share board cancelled";
                return;
            }
            BoardColumnFilterStore.Save(BoardFilters);
            filtersPath = Path.Combine(Path.GetTempPath(), $"trendalgo-share-filters-{Guid.NewGuid():N}.json");
            File.WriteAllText(filtersPath, BoardFilters.ToShareFiltersJson(
                BoardFilter,
                BoardHeatRanker.HeatmapEnabled(),
                buyPicksCollapsed: !BuyPicksExpanded));
            using var doc = _surfaces.SharePng(
                "board",
                DeskLane(),
                dest: dest,
                pairs: visible,
                title: title,
                filtersJsonPath: filtersPath,
                includeMarketContext: BuyPicksExpanded && ShowBuyPicks);
            var path = doc.RootElement.TryGetProperty("path", out var p) ? p.ToString() : dest;
            StatusText = string.IsNullOrWhiteSpace(path)
                ? $"Share {tab} list PNG enqueued"
                : $"Share {tab} list → {path}";
        }
        catch (Exception ex)
        {
            StatusText = $"Share board failed: {ex.Message}";
        }
        finally
        {
            if (filtersPath is not null)
            {
                try { File.Delete(filtersPath); } catch { /* ignore */ }
            }
        }
    }

    private async Task ShareStrategySheetPngAsync(string? pair)
    {
        if (string.IsNullOrWhiteSpace(pair))
        {
            StatusText = "Select a pair to share strategy PNG";
            return;
        }
        try
        {
            var safe = pair.Replace('/', '-');
            var suggested = $"strategy-{safe}-{DateTime.Now:yyyy-MM-dd}.png";
            var dest = await SharePngPicker.PickFromMainAsync(suggested);
            if (dest is null)
            {
                StatusText = "Share strategy cancelled";
                return;
            }
            using var doc = _surfaces.SharePng("strategy", DeskLane(), pair, dest);
            var path = doc.RootElement.TryGetProperty("path", out var p) ? p.ToString() : dest;
            StatusText = $"Share strategy PNG → {path}";
        }
        catch (Exception ex)
        {
            StatusText = $"Share strategy failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void DeskScanStatus()
    {
        EnqueueDesk("scan_status");
        var pending = DeskCommandClient.PeekPendingAction() ?? "(none)";
        StatusText = $"Scan status — pending desk action: {pending}; busy={ScanBusy}";
    }

    [RelayCommand]
    private void DeskToggleAutoscan()
    {
        AutoScan = !AutoScan;
        try
        {
            var msg = _desk.Enqueue("set_autoscan", DeskLane(), AutoScan ? 1 : 0);
            StatusText = $"Autoscan {(AutoScan ? "on" : "off")} — {msg}";
        }
        catch (Exception ex)
        {
            StatusText = $"Autoscan enqueue failed: {ex.Message}";
        }
    }

    private void EnqueueDesk(
        string action,
        bool? busy = null,
        bool forceFresh = false,
        IReadOnlyList<string>? lanes = null)
    {
        try
        {
            var pair = action == "run_backtest" ? BacktestPair : null;
            var msg = _desk.Enqueue(action, DeskLane(), forceFresh: forceFresh, pair: pair, lanes: lanes);
            if (busy is not null)
                ScanBusy = busy.Value;
            StatusText = forceFresh ? $"Force-fresh · {msg}" : msg;
            var dry = PreferDeskDry();
            // Live engine work: board scan + All-TA backtest (OTH5). Other strip actions ack-only.
            var liveEngine = action is "run_scan" or "run_all_scans" or "run_backtest";
            if (action is "run_scan" or "run_all_scans" or "cancel_scan" or "run_sauce" or "pool_watch"
                or "refresh_prices" or "run_backtest" or "cancel_backtest" or "share_board")
            {
                _desk.StartDeskOnce(dryRun: dry || !liveEngine);
                if (action is "run_scan" or "run_all_scans")
                {
                    foreach (var ln in lanes is { Count: > 0 } ? lanes : [DeskLane()])
                        SeedScanProgressStarting(ln, $"{ln} scan");
                    _scanPoll ??= new DeskScanPoller(
                        _results, DeskLane, () =>
                        {
                            ReloadBoard();
                            RefreshDeskLoadPct();
                        }, ApplyScanBusyFromPoller);
                    _scanPoll.Start();
                    _ = OpenScanProgress();
                }
                if (action is "run_backtest")
                    _ = OpenScanProgress();
            }
            RefreshDeskLoadPct();
            RefreshHandshake();
        }
        catch (Exception ex)
        {
            StatusText = $"Desk {action} failed: {ex.Message}";
        }
    }

    private void RefreshDeskLoadPct()
    {
        var lane = DeskLane();
        var job = _results.JobState($"scan:{lane}") ?? "";
        if (job.StartsWith("running:", StringComparison.Ordinal)
            && job.Contains('/', StringComparison.Ordinal))
        {
            var frac = job["running:".Length..];
            DeskLoadPct = $"Desk load {frac}";
        }
        else if (job is "running" or "done" or "cancelled" or "error")
            DeskLoadPct = $"Desk {job}";
        else
            DeskLoadPct = string.IsNullOrWhiteSpace(job) ? "" : $"Desk {job}";

        foreach (var nav in PrimaryNav)
        {
            if (nav.Id is not ("crypto" or "tradfi" or "forex"))
                continue;
            nav.SetDeskHeaderLabel(
                _expandedDesks.Contains(nav.Id),
                ParseDeskLoadPercent(_results.JobState($"scan:{nav.Id}")));
        }
    }

    private void RefreshLastScanText()
    {
        try
        {
            var lane = DeskLane();
            var filterFile = lane == "crypto" ? "scanner_filters.json" : $"scanner_filters_{lane}.json";
            var rowsFile = lane == "crypto" ? "lts_scan_rows.json" : $"lts_scan_rows_{lane}.json";
            var filterPath = Path.Combine(ProfilePaths.DeviceRoot, filterFile);
            var rowsPath = Path.Combine(ProfilePaths.DeviceRoot, rowsFile);

            DateTimeOffset? stamp = null;
            if (File.Exists(filterPath))
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(filterPath));
                if (doc.RootElement.TryGetProperty("last_scan_finished_at", out var fin)
                    && LocalTimeFormat.TryParseToLocal(fin.GetString(), out var dto))
                    stamp = dto;
            }
            if (stamp is null && File.Exists(rowsPath))
            {
                using var rdoc = JsonDocument.Parse(File.ReadAllText(rowsPath));
                if (rdoc.RootElement.TryGetProperty("saved_at", out var sa)
                    && LocalTimeFormat.TryParseToLocal(sa.GetString(), out var dto))
                {
                    stamp = dto;
                }
                else if (rdoc.RootElement.TryGetProperty("rows", out var rowsEl)
                         && rowsEl.ValueKind == JsonValueKind.Array
                         && rowsEl.GetArrayLength() > 0)
                {
                    stamp = new DateTimeOffset(File.GetLastWriteTimeUtc(rowsPath), TimeSpan.Zero);
                }
            }
            LastScanText = LocalTimeFormat.FormatLastScan(stamp);
        }
        catch
        {
            LastScanText = "Last scan: —";
        }
    }

    /// <summary>Parse board-load % from job state (<c>running:3/10</c> → 30).</summary>
    internal static int? ParseDeskLoadPercent(string? job)
    {
        if (string.IsNullOrWhiteSpace(job))
            return null;
        if (!job.StartsWith("running:", StringComparison.Ordinal))
            return null;
        var frac = job["running:".Length..];
        var parts = frac.Split('/', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length != 2
            || !int.TryParse(parts[0], out var done)
            || !int.TryParse(parts[1], out var total)
            || total <= 0)
            return null;
        return Math.Clamp(100 * done / total, 0, 100);
    }

    private void ApplyScanBusyFromPoller(bool busy)
    {
        var wasBusy = ScanBusy;
        ScanBusy = busy;
        if (wasBusy && !busy)
        {
            var job = _results.JobState($"scan:{DeskLane()}") ?? "";
            var title = job.StartsWith("error", StringComparison.Ordinal) ? "Scan error" : "Scan done";
            var body = string.IsNullOrWhiteSpace(job) ? $"{DeskLane()} desk finished" : $"{DeskLane()} · {job}";
            Toast(title, body);
            RefreshLastScanText();
            AlertsReload();
        }
    }

    private static bool PreferDeskDry() =>
        Environment.GetEnvironmentVariable("TRENDALGO_DESK_DRY") == "1";

    private string FirstBoardPair() => BoardRows.FirstOrDefault()?.Pair ?? "";

    public void RequestBoardChart(OpportunityBoardRow row, string windowKey)
    {
        SelectedBoardRow = row;
        _ = OpenChartWindowAsync(string.IsNullOrWhiteSpace(windowKey) ? "30d" : windowKey);
    }

    public void RequestBoardResults(OpportunityBoardRow row)
    {
        SelectedBoardRow = row;
        _ = OpenSurfaceAsync("results", row.Pair);
    }

    public void RequestBoardEvents(OpportunityBoardRow row)
    {
        SelectedBoardRow = row;
        _ = OpenSurfaceAsync("events", row.Pair);
    }

    private async Task OpenSurfaceAsync(string surface, string pair)
    {
        if (_surfaceBusy)
            return;
        _surfaceBusy = true;
        try
        {
            var lane = DeskLane();
            var owner = LoadingWindow.MainOwner();
            var label = FormatLoadingLabel(surface, pair);
            StatusText = label;
            using var doc = await LoadingWindow.RunAsync(
                owner, label, () => _surfaces.FetchAsync(surface, lane, pair));
            Window win = DeskSurfacePresenter.Build(surface, pair, doc.RootElement, lane);
            if (owner is { IsVisible: true })
                await win.ShowDialog(owner);
            else
                win.Show();
            StatusText = $"Opened {surface}{(string.IsNullOrWhiteSpace(pair) ? "" : $" · {pair.Replace('|', ' ')}")}";
        }
        catch (Exception ex)
        {
            StatusText = $"Surface {surface} failed: {ex.Message}";
        }
        finally
        {
            _surfaceBusy = false;
        }
    }

    private static string FormatLoadingLabel(string surface, string pair)
    {
        var cleanPair = pair.Contains('|') ? pair.Split('|')[0] : pair;
        return surface switch
        {
            "chart" when pair.EndsWith("|7d", StringComparison.OrdinalIgnoreCase) => $"Loading {cleanPair} 7D chart…",
            "chart" => $"Loading {cleanPair} 30D chart…",
            "results" => $"Loading {cleanPair} strategy results…",
            "events" => $"Loading {cleanPair} events…",
            "sauce" => string.IsNullOrWhiteSpace(cleanPair) ? "Loading Secret Sauce…" : $"Loading Secret Sauce · {cleanPair}…",
            _ => $"Loading {surface}…",
        };
    }

    private string DeskLane() => SelectedNavId switch
    {
        "tradfi" => "tradfi",
        "forex" => "forex",
        _ => "crypto",
    };
}
