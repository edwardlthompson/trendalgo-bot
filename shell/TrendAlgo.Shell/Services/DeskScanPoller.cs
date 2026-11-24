using Avalonia.Threading;

namespace TrendAlgo.Shell.Services;

/// <summary>Poll results.db job_control while a desk scan runs (AV-G3).</summary>
public sealed class DeskScanPoller
{
    private readonly ResultsDbReader _results;
    private readonly Func<string> _lane;
    private readonly Action _onTick;
    private readonly Action<bool> _setBusy;
    private DispatcherTimer? _timer;

    public DeskScanPoller(
        ResultsDbReader results,
        Func<string> lane,
        Action onTick,
        Action<bool> setBusy)
    {
        _results = results;
        _lane = lane;
        _onTick = onTick;
        _setBusy = setBusy;
    }

    public void Start()
    {
        _timer?.Stop();
        _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
        _timer.Tick += (_, _) =>
        {
            var state = _results.JobState($"scan:{_lane()}") ?? "";
            _onTick();
            if (state is "done" or "cancelled" or "error"
                || state.StartsWith("error", StringComparison.Ordinal))
            {
                _setBusy(false);
                _timer.Stop();
            }
            else if (!string.IsNullOrEmpty(state))
                _setBusy(true);
        };
        _timer.Start();
    }
}
