using System.Text;
using System.Text.Json;
using Avalonia.Controls;
using Avalonia.Interactivity;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.Views;

public partial class WizardWindow : Window
{
    private readonly string[] _steps;
    private readonly WindowsCredManStore _vault = new();
    private readonly DeskSurfaceClient _surfaces = new();
    private int _index;
    private string _setupKind = "ack";
    private string[] _permissionNames = [];

    public WizardWindow() : this("setup")
    {
    }

    public WizardWindow(string kind)
    {
        InitializeComponent();
        Kind = (kind ?? "setup").Trim().ToLowerInvariant();
        Title = Kind switch
        {
            "telegram" => "Telegram wizard",
            "alpaca" => "Alpaca wizard",
            "calendar" => "Calendar wizard",
            _ => "TrendAlgo setup wizard",
        };
        _steps = Kind switch
        {
            "telegram" =>
            [
                "Welcome — store Telegram bot token + chat id in Windows CredMan.",
                "Enter bot token and chat id below (same targets as TrendAlgo Bot).",
                "Enable Telegram kinds under Settings → notify.",
                "Use Alerts → Test Telegram to verify delivery.",
            ],
            "alpaca" =>
            [
                "Welcome — TradFi/Forex need Alpaca paper keys.",
                "Enter API key id + secret (TrendAlgo/alpaca-* targets).",
                "TradFi/Forex desk CTA clears when both secrets are present.",
                "Run a TradFi/Forex scan to verify bars.",
            ],
            "calendar" =>
            [
                "Welcome — coin events use CoinMarketCal / Coindar keys.",
                "Enter CMC key and/or Coindar token (optional either).",
                "Dashboard Events reads the calendar cache after sync.",
                "Reload board Events after the next calendar sync.",
            ],
            _ => [],
        };
        if (Kind == "setup")
        {
            BenchmarkBtn.IsVisible = true;
            LoadSetupSurface();
        }
        else
            RenderStep();
    }

    public string Kind { get; }

    private void LoadSetupSurface()
    {
        try
        {
            using var doc = _surfaces.Fetch("wizard", "crypto");
            ApplySetupDoc(doc.RootElement);
        }
        catch (Exception ex)
        {
            StatusText.Text = $"Wizard load failed: {ex.Message}";
            ContinueBtn.IsVisible = false;
            BackBtn.IsEnabled = false;
        }
    }

    private void ApplySetupDoc(JsonElement root)
    {
        NextBtn.IsVisible = false;
        FinishBtn.IsVisible = false;
        ContinueBtn.IsVisible = true;
        TitleText.Text = Title ?? "Setup wizard";
        var complete = root.TryGetProperty("complete", out var c) && c.ValueKind == JsonValueKind.True;
        StepLabel.Text = root.TryGetProperty("progress", out var p) ? p.ToString() : "";
        if (complete)
        {
            BodyText.Text = JoinBody(root);
            SourcesText.Text = "";
            HideSetupPanels();
            ContinueBtn.IsVisible = false;
            BackBtn.IsEnabled = root.TryGetProperty("can_back", out var cb) && cb.ValueKind == JsonValueKind.True;
            HintText.Text = "All W0–W5 steps are saved. Live trading still needs the go-live checklist.";
            StatusText.Text = "Setup complete";
            return;
        }

        _setupKind = root.TryGetProperty("kind", out var k) ? k.ToString() : "ack";
        BodyText.Text = JoinBody(root);
        SourcesText.Text = FormatSources(root);
        AckBox.Content = root.TryGetProperty("ack_label", out var al) ? al.ToString() : "I have read this step.";
        AckBox.IsChecked = false;
        PermissionHelp.Text = root.TryGetProperty("permission_help", out var ph) ? ph.ToString() : "";
        WithdrawOff.Content = root.TryGetProperty("withdraw_label", out var wl) ? wl.ToString() : "";
        PracticeNote.Text = root.TryGetProperty("practice_note", out var pn) ? pn.ToString() : "";
        PairNote.Text = root.TryGetProperty("pair_note", out var pairN) ? pairN.ToString() : "";
        PairHostLabel.Text = root.TryGetProperty("pair_host_label", out var phl) ? phl.ToString() : "Host";
        PairSecretLabel.Text = root.TryGetProperty("pair_secret_label", out var psl) ? psl.ToString() : "Secret";
        PairSecretHelp.Text = root.TryGetProperty("pair_secret_help", out var psh) ? psh.ToString() : "";
        PairCodeLabel.Text = root.TryGetProperty("pair_code_label", out var pcl) ? pcl.ToString() : "Code";
        PairCodeHelp.Text = root.TryGetProperty("pair_code_help", out var pch) ? pch.ToString() : "";
        CapacityHelp.Text = root.TryGetProperty("capacity_help", out var ch) ? ch.ToString() : "";
        PairHostBox.Text = root.TryGetProperty("host_url", out var hu) ? hu.ToString() : "";

        if (root.TryGetProperty("permissions", out var perms) && perms.ValueKind == JsonValueKind.Array)
        {
            _permissionNames = perms.EnumerateArray().Select(x => x.ToString()).ToArray();
            var boxes = new[] { Perm0, Perm1, Perm2, Perm3, Perm4 };
            for (var i = 0; i < boxes.Length; i++)
            {
                if (i < _permissionNames.Length)
                {
                    boxes[i].Content = _permissionNames[i];
                    boxes[i].IsVisible = true;
                    boxes[i].IsChecked = false;
                }
                else
                {
                    boxes[i].IsVisible = false;
                }
            }
        }

        HideSetupPanels();
        AckBox.IsVisible = _setupKind == "ack";
        KeysPanel.IsVisible = _setupKind == "keys";
        PracticePanel.IsVisible = _setupKind == "practice";
        PairPanel.IsVisible = _setupKind == "pair";
        CapacityHelp.IsVisible = root.TryGetProperty("step_id", out var sid)
            && sid.ToString() == "W3";
        BackBtn.IsEnabled = root.TryGetProperty("can_back", out var canBack)
            && canBack.ValueKind == JsonValueKind.True;
        ContinueBtn.Content = root.TryGetProperty("continue_label", out var cl)
            ? cl.ToString()
            : "Continue";
        BackBtn.Content = root.TryGetProperty("back_label", out var bl) ? bl.ToString() : "Back";
        HintText.Text = _setupKind switch
        {
            "keys" => "Confirm Kraken permissions — secrets stay in Settings → keys / CredMan.",
            "practice" => "Continue starts a loopback practice host and runs four checks.",
            "pair" => "This build pairs with the practice host on 127.0.0.1 only.",
            _ => "Acknowledge each step. Progress saves to wizard.json under the device profile.",
        };
        StatusText.Text = "";
    }

    private static string JoinBody(JsonElement root)
    {
        if (!root.TryGetProperty("body", out var body) || body.ValueKind != JsonValueKind.Array)
            return "";
        var sb = new StringBuilder();
        foreach (var para in body.EnumerateArray())
        {
            if (sb.Length > 0)
                sb.AppendLine().AppendLine();
            sb.Append(para.ToString());
        }
        return sb.ToString();
    }

    private static string FormatSources(JsonElement root)
    {
        if (!root.TryGetProperty("sources", out var sources) || sources.ValueKind != JsonValueKind.Array)
            return "";
        var sb = new StringBuilder("Official sources:");
        foreach (var s in sources.EnumerateArray())
        {
            var label = s.TryGetProperty("label", out var l) ? l.ToString() : "";
            var url = s.TryGetProperty("url", out var u) ? u.ToString() : "";
            var checkedAt = s.TryGetProperty("checked", out var c) ? c.ToString() : "";
            sb.AppendLine().Append($"• {label} ({url}), checked {checkedAt}");
        }
        return sb.ToString();
    }

    private void HideSetupPanels()
    {
        AckBox.IsVisible = false;
        KeysPanel.IsVisible = false;
        PracticePanel.IsVisible = false;
        PairPanel.IsVisible = false;
        CapacityHelp.IsVisible = false;
        Field1Label.IsVisible = false;
        Field1Box.IsVisible = false;
        Field2Label.IsVisible = false;
        Field2Box.IsVisible = false;
    }

    private void RenderStep()
    {
        TitleText.Text = Title ?? "Wizard";
        StepLabel.Text = $"Step {_index + 1} / {_steps.Length}";
        BodyText.Text = _steps[_index];
        SourcesText.Text = "";
        HideSetupPanels();
        ContinueBtn.IsVisible = false;
        var secretStep = (Kind is "telegram" or "alpaca" or "calendar") && _index == 1;
        Field1Label.IsVisible = secretStep;
        Field1Box.IsVisible = secretStep;
        Field2Label.IsVisible = secretStep;
        Field2Box.IsVisible = secretStep;
        if (secretStep)
        {
            (Field1Label.Text, Field2Label.Text) = Kind switch
            {
                "telegram" => ("Bot token", "Chat id"),
                "alpaca" => ("API key id", "API secret"),
                _ => ("CoinMarketCal key", "Coindar token"),
            };
            (Field1Box.Text, Field2Box.Text) = Kind switch
            {
                "telegram" => (_vault.Read(CredManTargets.TelegramToken) ?? "", _vault.Read(CredManTargets.TelegramChat) ?? ""),
                "alpaca" => (_vault.Read(CredManTargets.AlpacaKey) ?? "", _vault.Read(CredManTargets.AlpacaSecret) ?? ""),
                _ => (_vault.Read(CredManTargets.CalendarCmc) ?? "", _vault.Read(CredManTargets.CalendarCoindar) ?? ""),
            };
            HintText.Text = "Writes frozen TrendAlgo/* CredMan targets — no re-entry in Bot.";
        }
        else
        {
            HintText.Text = "Finish saves secrets to the same Windows Credential Manager as Bot.";
        }
        BackBtn.IsEnabled = _index > 0;
        var last = _index >= _steps.Length - 1;
        NextBtn.IsVisible = !last;
        FinishBtn.IsVisible = last;
    }

    private void OnBack(object? sender, RoutedEventArgs e)
    {
        if (Kind == "setup")
        {
            try
            {
                using var doc = _surfaces.WizardBack();
                if (doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True)
                    ApplySetupDoc(doc.RootElement);
                else
                    StatusText.Text = "Back failed";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Back failed: {ex.Message}";
            }
            return;
        }
        if (_index > 0)
        {
            _index--;
            RenderStep();
        }
    }

    private void OnNext(object? sender, RoutedEventArgs e)
    {
        if (_index < _steps.Length - 1)
        {
            _index++;
            RenderStep();
        }
    }

    private void OnContinue(object? sender, RoutedEventArgs e)
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_wizard_advance.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(path, BuildAdvancePayload());
            using var doc = _surfaces.WizardAdvance(path);
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (!ok)
            {
                var problems = root.TryGetProperty("problems", out var p)
                    && p.ValueKind == JsonValueKind.Array
                    ? string.Join(" ", p.EnumerateArray().Select(x => x.ToString()))
                    : "validation failed";
                StatusText.Text = problems;
                // Still refresh view so practice note / fields stay in sync
                if (root.TryGetProperty("step_id", out _))
                    ApplySetupDoc(root);
                return;
            }
            ApplySetupDoc(root);
            StatusText.Text = root.TryGetProperty("complete", out var done) && done.ValueKind == JsonValueKind.True
                ? "Setup complete"
                : "Step saved";
        }
        catch (Exception ex)
        {
            StatusText.Text = $"Continue failed: {ex.Message}";
        }
    }

    private string BuildAdvancePayload()
    {
        var sb = new StringBuilder();
        sb.Append('{');
        if (_setupKind == "ack")
            sb.Append($"\"ack\":{(AckBox.IsChecked == true ? "true" : "false")}");
        else if (_setupKind == "keys")
        {
            sb.Append("\"permissions\":[");
            var boxes = new[] { Perm0, Perm1, Perm2, Perm3, Perm4 };
            var first = true;
            for (var i = 0; i < boxes.Length && i < _permissionNames.Length; i++)
            {
                if (boxes[i].IsChecked != true)
                    continue;
                if (!first)
                    sb.Append(',');
                first = false;
                sb.Append('"').Append(Escape(_permissionNames[i])).Append('"');
            }
            sb.Append($"],\"withdraw_off\":{(WithdrawOff.IsChecked == true ? "true" : "false")}");
        }
        else if (_setupKind == "practice")
            sb.Append("\"run_practice\":true");
        else if (_setupKind == "pair")
        {
            sb.Append($"\"host_url\":\"{Escape(PairHostBox.Text ?? "")}\",");
            sb.Append($"\"owner_secret\":\"{Escape(PairSecretBox.Text ?? "")}\",");
            sb.Append($"\"pairing_code\":\"{Escape(PairCodeBox.Text ?? "")}\"");
        }
        else
            sb.Append("\"ack\":false");
        sb.Append('}');
        return sb.ToString();
    }

    private static string Escape(string value) =>
        value.Replace("\\", "\\\\", StringComparison.Ordinal)
            .Replace("\"", "\\\"", StringComparison.Ordinal);

    private void OnFinish(object? sender, RoutedEventArgs e)
    {
        try
        {
            var a = Field1Box.Text?.Trim() ?? "";
            var b = Field2Box.Text?.Trim() ?? "";
            if (Kind == "telegram")
            {
                if (string.IsNullOrEmpty(a) || string.IsNullOrEmpty(b))
                {
                    StatusText.Text = "Token and chat id required.";
                    return;
                }
                _vault.Write(CredManTargets.TelegramToken, a);
                _vault.Write(CredManTargets.TelegramChat, b);
            }
            else if (Kind == "alpaca")
            {
                if (string.IsNullOrEmpty(a) || string.IsNullOrEmpty(b))
                {
                    StatusText.Text = "Key id and secret required.";
                    return;
                }
                _vault.Write(CredManTargets.AlpacaKey, a);
                _vault.Write(CredManTargets.AlpacaSecret, b);
            }
            else if (Kind == "calendar")
            {
                if (string.IsNullOrEmpty(a) && string.IsNullOrEmpty(b))
                {
                    StatusText.Text = "Enter at least one calendar key.";
                    return;
                }
                if (!string.IsNullOrEmpty(a))
                    _vault.Write(CredManTargets.CalendarCmc, a);
                if (!string.IsNullOrEmpty(b))
                    _vault.Write(CredManTargets.CalendarCoindar, b);
            }
            Close(true);
        }
        catch (Exception ex)
        {
            StatusText.Text = $"CredMan write failed: {ex.Message}";
        }
    }

    private void OnClose(object? sender, RoutedEventArgs e) => Close(false);

    private async void OnBenchmark(object? sender, RoutedEventArgs e)
    {
        BenchmarkBtn.IsEnabled = false;
        StatusText.Text = "Running onboarding benchmark (1 coin · 1 stock · 1 FX + Secret Sauce)…";
        try
        {
            var win = new BenchmarkWindow(runLive: true);
            await win.ShowDialog(this);
            if (!win.BenchmarkSucceeded)
            {
                StatusText.Text = "Benchmark did not complete.";
            }
            else if (win.LastEtaDoc is { } etaDoc)
            {
                using (etaDoc)
                {
                    var eta = etaDoc.RootElement;
                    var total = eta.TryGetProperty("total", out var t) ? t.GetString() ?? "" : "";
                    var warn = eta.TryGetProperty("overrun_warning", out var w) ? w.GetString() ?? "" : "";
                    StatusText.Text = string.IsNullOrWhiteSpace(warn)
                        ? $"Benchmark complete · {total}"
                        : $"Benchmark complete · {total}\n{warn}";
                }
            }
            else
                StatusText.Text = "Benchmark complete.";
        }
        catch (Exception ex)
        {
            StatusText.Text = $"Benchmark failed: {ex.Message}";
        }
        finally
        {
            BenchmarkBtn.IsEnabled = true;
        }
    }
}
