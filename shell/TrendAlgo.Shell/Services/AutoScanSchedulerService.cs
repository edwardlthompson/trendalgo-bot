using System.Text.Json;
using Avalonia.Threading;

namespace TrendAlgo.Shell.Services;

/// <summary>Wall-clock aligned auto-scan scheduler (60m fires at local HH:00:00).</summary>
public sealed class AutoScanSchedulerService : IDisposable
{
    public sealed record ScheduleConfig(
        int IntervalMinutes,
        bool Crypto,
        bool TradFi,
        bool Forex)
    {
        public IReadOnlyList<string> EnabledLanes()
        {
            var lanes = new List<string>(3);
            if (Crypto) lanes.Add("crypto");
            if (TradFi) lanes.Add("tradfi");
            if (Forex) lanes.Add("forex");
            return lanes;
        }
    }

    private readonly Action<IReadOnlyList<string>, DateTimeOffset> _onDue;
    private readonly Action<string> _onStatus;
    private readonly CancellationTokenSource _cts = new();
    private ScheduleConfig _config;
    private DateTimeOffset _nextBoundaryUtc;

    public AutoScanSchedulerService(
        Action<IReadOnlyList<string>, DateTimeOffset> onDue,
        Action<string> onStatus)
    {
        _onDue = onDue;
        _onStatus = onStatus;
        _config = LoadConfig();
        _nextBoundaryUtc = NextAlignedBoundaryUtc(DateTimeOffset.UtcNow, _config.IntervalMinutes);
        _ = RunLoopAsync(_cts.Token);
    }

    public ScheduleConfig CurrentConfig => _config;
    public DateTimeOffset NextBoundaryUtc => _nextBoundaryUtc;

    public void RefreshSchedule()
    {
        _config = LoadConfig();
        _nextBoundaryUtc = NextAlignedBoundaryUtc(DateTimeOffset.UtcNow, _config.IntervalMinutes);
        PublishStatus();
    }

    public string FormatStatus()
    {
        var lanes = _config.EnabledLanes();
        if (lanes.Count == 0)
            return "Schedule: paused (no auto-scan lanes enabled)";
        var nextLocal = _nextBoundaryUtc.ToLocalTime();
        var when = _config.IntervalMinutes == 60
            ? $"every 60m on the hour · next {nextLocal:HH:mm}"
            : $"every {_config.IntervalMinutes}m · next {nextLocal:HH:mm}";
        return $"Schedule: {when} ({string.Join(", ", lanes)})";
    }

    public static DateTimeOffset NextAlignedBoundaryUtc(
        DateTimeOffset nowUtc,
        int intervalMinutes,
        TimeZoneInfo? localTz = null)
    {
        var minutes = Math.Clamp(intervalMinutes, 60, 1440);
        var tz = localTz ?? TimeZoneInfo.Local;
        var localNow = TimeZoneInfo.ConvertTime(nowUtc, tz);
        var midnight = new DateTime(localNow.Year, localNow.Month, localNow.Day, 0, 0, 0, DateTimeKind.Unspecified);
        var elapsed = (int)Math.Floor((localNow.DateTime - midnight).TotalMinutes);
        var nextSlot = ((elapsed / minutes) + 1) * minutes;
        var nextLocal = midnight.AddMinutes(nextSlot);
        if (tz.IsInvalidTime(nextLocal))
            nextLocal = nextLocal.AddHours(1);
        var offset = tz.GetUtcOffset(nextLocal);
        var nextDto = new DateTimeOffset(nextLocal, offset).ToUniversalTime();
        if (nextDto <= nowUtc)
            nextDto = NextAlignedBoundaryUtc(nowUtc.AddMinutes(1), minutes, tz);
        return nextDto;
    }

    public static ScheduleConfig LoadConfig()
    {
        var interval = 60;
        var crypto = true;
        var tradfi = false;
        var forex = false;
        try
        {
            var filtersPath = Path.Combine(ProfilePaths.DeviceRoot, "scanner_filters.json");
            if (File.Exists(filtersPath))
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(filtersPath));
                if (doc.RootElement.TryGetProperty("interval_minutes", out var iv)
                    && iv.TryGetInt32(out var mins))
                    interval = Math.Clamp(mins, 60, 1440);
            }
            var lanePrefsPath = Path.Combine(ProfilePaths.DeviceRoot, "lane_prefs.json");
            var settingsPath = Path.Combine(ProfilePaths.DeviceRoot, "settings.json");
            var laneFile = File.Exists(lanePrefsPath) ? lanePrefsPath : settingsPath;
            if (File.Exists(laneFile))
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(laneFile));
                var root = doc.RootElement;
                if (root.TryGetProperty("auto_scan_crypto", out var c))
                    crypto = c.ValueKind == JsonValueKind.True;
                if (root.TryGetProperty("auto_scan_tradfi", out var t))
                    tradfi = t.ValueKind == JsonValueKind.True;
                if (root.TryGetProperty("auto_scan_forex", out var f))
                    forex = f.ValueKind == JsonValueKind.True;
            }
        }
        catch
        {
            /* keep defaults */
        }
        return new ScheduleConfig(interval, crypto, tradfi, forex);
    }

    private void PublishStatus()
    {
        var text = FormatStatus();
        Dispatcher.UIThread.Post(() => _onStatus(text));
    }

    private async Task RunLoopAsync(CancellationToken ct)
    {
        PublishStatus();
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(5));
        try
        {
            while (await timer.WaitForNextTickAsync(ct))
            {
                var now = DateTimeOffset.UtcNow;
                if (now < _nextBoundaryUtc)
                    continue;
                var firedAt = _nextBoundaryUtc;
                _config = LoadConfig();
                _nextBoundaryUtc = NextAlignedBoundaryUtc(now.AddSeconds(1), _config.IntervalMinutes);
                PublishStatus();
                var lanes = _config.EnabledLanes();
                if (lanes.Count > 0)
                    Dispatcher.UIThread.Post(() => _onDue(lanes, firedAt));
            }
        }
        catch (OperationCanceledException)
        {
            /* shutdown */
        }
    }

    public void Dispose()
    {
        _cts.Cancel();
        _cts.Dispose();
    }
}
