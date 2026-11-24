using System.Text.Json;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    private DispatcherTimer? _hostPoll;

    [RelayCommand]
    private void BotsReload()
    {
        BotRows.Clear();
        try
        {
            using var doc = _surfaces.Fetch("bots", "crypto");
            HostBadge = doc.RootElement.TryGetProperty("host_badge", out var hb)
                ? hb.ToString()
                : "local";
            if (doc.RootElement.TryGetProperty("host_badge_label", out var hbl)
                && hbl.ValueKind == JsonValueKind.String
                && !string.IsNullOrWhiteSpace(hbl.ToString()))
                HostBadgeLabel = hbl.ToString();
            else
                HostBadgeLabel = HostBadge == "linked" ? "Host linked" : "No host linked";
            var cards = doc.RootElement.TryGetProperty("cards", out var cArr)
                && cArr.ValueKind == JsonValueKind.Array
                && cArr.GetArrayLength() > 0
                ? cArr
                : doc.RootElement.TryGetProperty("rows", out var rows) ? rows : default;
            if (cards.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in cards.EnumerateArray())
                {
                    var id = S(r, "id");
                    var enabled = r.TryGetProperty("enabled", out var en) && en.ValueKind == JsonValueKind.True;
                    BotRows.Add(new BotPlanRow
                    {
                        Id = id,
                        Name = S(r, "name"),
                        Pair = S(r, "pair"),
                        Strategy = S(r, "strategy"),
                        Timeframe = S(r, "timeframe"),
                        Stake = S(r, "stake"),
                        State = S(r, "state"),
                        Enabled = enabled,
                        CanToggle = !string.IsNullOrWhiteSpace(id),
                        Source = S(r, "source"),
                    });
                }
            }
            HostSafetyLights = $"Safety: {HostBadge} · flatten=idle · journal=ok · bots={BotRows.Count}";
            var note = string.IsNullOrWhiteSpace(BotsPrefillNote)
                ? ""
                : $" · {BotsPrefillNote}";
            var live = BotRows.Count(b => b.CanToggle);
            StatusText = $"Bots hub · host={HostBadge} · {BotRows.Count} cards ({live} live){note}";
        }
        catch (Exception ex)
        {
            StatusText = $"Bots reload failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void BotsFabAdd()
    {
        Navigate("bots");
        if (string.IsNullOrWhiteSpace(PlanDraftPair))
            PlanDraftPair = "BTC/USD";
        if (string.IsNullOrWhiteSpace(PlanDraftStrategy))
            PlanDraftStrategy = "RSI";
        StatusText = "FAB · focus plan draft — fill name/pair/strategy then Save plan draft";
    }

    [RelayCommand]
    private void BotsResume(BotPlanRow? row)
    {
        if (row is null || !row.CanToggle)
        {
            StatusText = "Resume needs a live bots.db card (not plan-only)";
            return;
        }
        BotsSetEnabled(row.Id, true);
    }

    [RelayCommand]
    private void BotsPause(BotPlanRow? row)
    {
        if (row is null || !row.CanToggle)
        {
            StatusText = "Pause needs a live bots.db card (not plan-only)";
            return;
        }
        BotsSetEnabled(row.Id, false);
    }

    private void BotsSetEnabled(string botId, bool enabled)
    {
        try
        {
            using var doc = _surfaces.BotsSetEnabled(botId, enabled);
            var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            StatusText = ok
                ? $"Bot {botId} → {(enabled ? "running" : "paused")}"
                : $"Bot toggle failed: {(doc.RootElement.TryGetProperty("error", out var e) ? e.ToString() : "error")}";
            if (ok)
                BotsReload();
        }
        catch (Exception ex)
        {
            StatusText = $"Bot toggle failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void BotsToggleHostPoll()
    {
        _hostPoll ??= new DispatcherTimer { Interval = TimeSpan.FromSeconds(15) };
        if (_hostPoll.IsEnabled)
        {
            _hostPoll.Stop();
            HostPollCaption = "Host poll: off";
            StatusText = HostPollCaption;
            return;
        }
        _hostPoll.Tick -= OnHostPollTick;
        _hostPoll.Tick += OnHostPollTick;
        _hostPoll.Start();
        HostPollCaption = "Host poll: 15s";
        BotsReload();
        StatusText = HostPollCaption;
    }

    private void OnHostPollTick(object? sender, EventArgs e)
    {
        if (ShowBots)
            BotsReload();
    }

    [RelayCommand]
    private void BotsPanic()
    {
        try
        {
            using var doc = _surfaces.BotsPanic();
            var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            var paused = doc.RootElement.TryGetProperty("paused", out var p) ? p.ToString() : "?";
            var linked = doc.RootElement.TryGetProperty("host_linked", out var hl)
                && hl.ValueKind == JsonValueKind.True;
            var flatten = doc.RootElement.TryGetProperty("host_flatten_calls", out var fc)
                ? fc.ToString()
                : "0";
            if (!ok)
            {
                StatusText =
                    $"Panic refused: {(doc.RootElement.TryGetProperty("error", out var e) ? e.ToString() : "error")}";
                return;
            }
            StatusText = linked
                ? $"Panic: paused {paused} bots · host flatten calls={flatten}"
                : $"Panic: paused {paused} bots (local only — host not linked)";
            HostSafetyLights = linked
                ? $"Safety: linked · flatten={flatten} · journal=ok · bots={BotRows.Count}"
                : $"Safety: local · flatten=idle · journal=ok · bots={BotRows.Count}";
            BotsReload();
        }
        catch (Exception ex)
        {
            StatusText = $"Panic failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task BotsJournal() => await OpenBotsOpsSurfaceAsync("bots_journal", "Journal");

    [RelayCommand]
    private async Task BotsPerformance() => await OpenBotsOpsSurfaceAsync("bots_perf", "Performance");

    private async Task OpenBotsOpsSurfaceAsync(string surface, string title)
    {
        try
        {
            using var doc = _surfaces.Fetch(surface, "crypto");
            var rows = new List<SurfaceGridRow>();
            if (doc.RootElement.TryGetProperty("rows", out var arr) && arr.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in arr.EnumerateArray())
                {
                    if (surface == "bots_perf")
                    {
                        rows.Add(new SurfaceGridRow
                        {
                            Col1 = S(r, "label"),
                            Col2 = S(r, "pair"),
                            Col3 = S(r, "strategy"),
                            Col4 = S(r, "pnl"),
                            Col5 = S(r, "trades"),
                        });
                    }
                    else
                    {
                        rows.Add(new SurfaceGridRow
                        {
                            Col1 = S(r, "at"),
                            Col2 = S(r, "pair"),
                            Col3 = S(r, "side"),
                            Col4 = S(r, "pnl"),
                            Col5 = S(r, "bot_id"),
                        });
                    }
                }
            }
            var win = new DeskSurfaceWindow();
            win.Bind(
                $"Bots — {title}",
                rows,
                rows.Count == 0 ? $"No {title.ToLowerInvariant()} rows yet" : $"{rows.Count} rows from device DBs",
                headers: surface == "bots_perf"
                    ? ("Bot", "Pair", "Strategy", "PnL", "Trades")
                    : ("When", "Pair", "Side", "PnL", "Bot"),
                enableFilter: true);
            if (Avalonia.Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime
                {
                    MainWindow: { } owner
                })
                await win.ShowDialog(owner);
            else
                win.Show();
            StatusText = $"Opened bots {title.ToLowerInvariant()}";
        }
        catch (Exception ex)
        {
            StatusText = $"{title} failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void BotsSavePlanDraft()
    {
        var pair = string.IsNullOrWhiteSpace(PlanDraftPair) ? "BTC/USD" : PlanDraftPair.Trim().ToUpperInvariant();
        var strategy = string.IsNullOrWhiteSpace(PlanDraftStrategy) ? "RSI" : PlanDraftStrategy.Trim();
        try
        {
            using var created = _surfaces.CreateBot(pair, strategy);
            var name = created.RootElement.TryGetProperty("name", out var n) ? n.ToString() : strategy;
            if (!string.IsNullOrWhiteSpace(PlanDraftName))
                name = PlanDraftName.Trim();
            BotsPrefillNote =
                $"Plan draft saved · {name} ({pair} · {strategy} · {PlanDraftTimeframe} · stake={PlanDraftStake})";
            StatusText = BotsPrefillNote + " — send-to-host still botd";
            BotsReload();
        }
        catch (Exception ex)
        {
            StatusText = $"Plan draft failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void BotsSendToHost()
    {
        try
        {
            using var doc = _surfaces.BotsPublishPlan();
            var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (ok)
            {
                var version = doc.RootElement.TryGetProperty("version", out var v) ? v.ToString() : "?";
                var digest = doc.RootElement.TryGetProperty("digest", out var d) ? d.ToString() : "";
                var bots = doc.RootElement.TryGetProperty("bots", out var b) ? b.ToString() : "?";
                StatusText = $"Plan sent to host · v{version} · {bots} bots · {digest}";
                BotsPrefillNote = StatusText;
                BotsReload();
                return;
            }
            var err = doc.RootElement.TryGetProperty("error", out var e) ? e.ToString() : "unknown";
            StatusText = err switch
            {
                "no_host" => "Send to host failed — link host in Settings → Connection first",
                "needs_owner" => "Send to host failed — owner id missing (complete pairing)",
                "plan_check" => "Send to host failed — plan validation errors",
                "host_unreachable" => "Send to host failed — host unreachable",
                "plan_stale" => "Send to host failed — plan stale (reload / bump version)",
                "plan_refused" => "Send to host failed — plan refused",
                _ => $"Send to host failed: {err}",
            };
        }
        catch (Exception ex)
        {
            StatusText = $"Send to host failed: {ex.Message}";
        }
    }

    private static string S(JsonElement row, string key) =>
        row.TryGetProperty(key, out var p) ? p.ToString() : "";
}
