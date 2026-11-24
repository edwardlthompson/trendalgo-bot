using System.Text.Json;
using System.Text.Json.Nodes;
using CommunityToolkit.Mvvm.ComponentModel;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    private AutoScanSchedulerService? _autoScheduler;

    [ObservableProperty] private string _scheduleStatusText = "Schedule: every 60m on the hour";
    [ObservableProperty] private decimal _lanesIntervalMinutes = 60m;

    private void StartAutoScanScheduler()
    {
        _autoScheduler?.Dispose();
        _autoScheduler = new AutoScanSchedulerService(OnScheduledBoundaryDue, s => ScheduleStatusText = s);
        LanesIntervalMinutes = _autoScheduler.CurrentConfig.IntervalMinutes;
    }

    private void RefreshAutoScanScheduler()
    {
        _autoScheduler?.RefreshSchedule();
        if (_autoScheduler is not null)
        {
            LanesIntervalMinutes = _autoScheduler.CurrentConfig.IntervalMinutes;
            ScheduleStatusText = _autoScheduler.FormatStatus();
        }
    }

    private void OnScheduledBoundaryDue(IReadOnlyList<string> lanes, DateTimeOffset boundaryUtc)
    {
        if (ScanBusy || lanes.Count == 0)
            return;
        try
        {
            var local = boundaryUtc.ToLocalTime();
            if (lanes.Count >= 2)
                EnqueueDesk("run_all_scans", busy: true, lanes: lanes);
            else
            {
                _desk.Enqueue("run_scan", lanes[0]);
                ScanBusy = true;
                _desk.StartDeskOnce(dryRun: PreferDeskDry());
                _scanPoll ??= new DeskScanPoller(
                    _results, DeskLane, () =>
                    {
                        ReloadBoard();
                        RefreshDeskLoadPct();
                    }, ApplyScanBusyFromPoller);
                _scanPoll.Start();
            }
            var summary = $"Auto-scan fired at {local:HH:mm:ss} ({string.Join(", ", lanes)})";
            StatusText = summary;
            AppendTimingLog("scheduled_scan", string.Join(",", lanes), 0, summary);
        }
        catch (Exception ex)
        {
            StatusText = $"Scheduled scan failed: {ex.Message}";
        }
    }

    private static void SaveIntervalMinutesToFilters(int intervalMinutes)
    {
        var clamped = Math.Clamp(intervalMinutes, 60, 1440);
        var path = Path.Combine(ProfilePaths.DeviceRoot, "scanner_filters.json");
        Directory.CreateDirectory(ProfilePaths.DeviceRoot);
        JsonObject obj;
        if (File.Exists(path))
            obj = JsonNode.Parse(File.ReadAllText(path)) as JsonObject ?? new JsonObject();
        else
            obj = new JsonObject();
        obj["interval_minutes"] = clamped;
        File.WriteAllText(path, JsonNodeWrite.ToIndented(obj));
    }
}
