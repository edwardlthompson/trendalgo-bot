using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Threading;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.Views;

public partial class ScanProgressWindow : Window, INotifyPropertyChanged
{
    private readonly DeskSurfaceClient _surfaces;
    private readonly Func<string> _lane;
    private readonly DispatcherTimer _timer;
    private string _phase = "Idle";
    private string _pairGlance = "Pair: —";
    private string _etaLabel = "ETA: —";
    private string _pairsLabel = "";
    private double _percent;
    private string _percentLabel = "0%";
    private string _logText = "";

    public new event PropertyChangedEventHandler? PropertyChanged;

    public string Phase
    {
        get => _phase;
        set => SetField(ref _phase, value);
    }

    public string PairGlance
    {
        get => _pairGlance;
        set => SetField(ref _pairGlance, value);
    }

    public string EtaLabel
    {
        get => _etaLabel;
        set => SetField(ref _etaLabel, value);
    }

    public string PairsLabel
    {
        get => _pairsLabel;
        set => SetField(ref _pairsLabel, value);
    }

    public double Percent
    {
        get => _percent;
        set => SetField(ref _percent, value);
    }

    public string PercentLabel
    {
        get => _percentLabel;
        set => SetField(ref _percentLabel, value);
    }

    public string LogText
    {
        get => _logText;
        set => SetField(ref _logText, value);
    }

    public ScanProgressWindow()
        : this(new DeskSurfaceClient(), () => "crypto")
    {
    }

    public ScanProgressWindow(DeskSurfaceClient surfaces, Func<string> lane)
    {
        _surfaces = surfaces;
        _lane = lane;
        InitializeComponent();
        DataContext = this;
        _timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(400) };
        _timer.Tick += (_, _) => RefreshFromSurface();
        Opened += (_, _) =>
        {
            RefreshFromSurface();
            _timer.Start();
        };
        Closed += (_, _) => _timer.Stop();
    }

    public void RefreshFromSurface()
    {
        try
        {
            using var doc = _surfaces.Fetch("progress", _lane());
            ApplyJson(doc.RootElement);
        }
        catch (Exception ex)
        {
            Phase = "Progress error";
            LogText = ex.Message;
        }
    }

    public void ApplyJson(JsonElement root)
    {
        var phase = root.TryGetProperty("phase", out var p) ? p.ToString() : "";
        var pct = 0.0;
        if (root.TryGetProperty("percent", out var pc) && pc.ValueKind == JsonValueKind.Number
            && pc.TryGetDouble(out var pv))
            pct = pv;
        else if (root.TryGetProperty("pct", out var pc2) && pc2.ValueKind == JsonValueKind.Number
                 && pc2.TryGetDouble(out var pv2))
            pct = pv2;

        var lines = new List<string>();
        if (root.TryGetProperty("lines", out var arr) && arr.ValueKind == JsonValueKind.Array)
        {
            foreach (var ln in arr.EnumerateArray())
                lines.Add(ln.ToString());
        }

        var pair = root.TryGetProperty("current_pair", out var cp) ? cp.ToString() : "—";
        var eta = root.TryGetProperty("eta_label", out var et) ? et.ToString() : "—";
        var pairs = root.TryGetProperty("pairs_label", out var pl) ? pl.ToString() : "";
        var busy = root.TryGetProperty("busy", out var b) && b.ValueKind == JsonValueKind.True;

        Phase = string.IsNullOrWhiteSpace(phase)
            ? (busy ? "Scanning…" : (lines.Count > 0 ? lines[^1] : "Idle"))
            : phase;
        PairGlance = string.IsNullOrWhiteSpace(pair) ? "Pair: —" : $"Pair: {pair}";
        EtaLabel = string.IsNullOrWhiteSpace(eta) || eta == "—" ? "ETA: —" : $"ETA: {eta}";
        PairsLabel = pairs;
        Percent = Math.Clamp(pct, 0, 100);
        PercentLabel = $"{Percent:0}%";
        LogText = lines.Count > 0
            ? string.Join('\n', lines.TakeLast(120))
            : (string.IsNullOrWhiteSpace(phase) ? "Waiting for scan progress…" : phase);
    }

    private void OnClose(object? sender, RoutedEventArgs e) => Close();

    private void SetField<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return;
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
    }
}
