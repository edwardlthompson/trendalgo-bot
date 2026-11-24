using System.Collections.ObjectModel;
using System.Text.Json;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    public ObservableCollection<ExchangeKeyRow> ExchangeKeyRows { get; } = new();
    public IReadOnlyList<string> ExchangeScopeChoices { get; } =
    [
        "query",
        "trade",
    ];

    [ObservableProperty] private ExchangeKeyRow? _selectedExchangeOption;
    [ObservableProperty] private string _exchangeKeyScope = "query";
    [ObservableProperty] private string _exchangeApiKeyInput = "";
    [ObservableProperty] private string _exchangeApiSecretInput = "";
    [ObservableProperty] private string _exchangePassphraseInput = "";
    [ObservableProperty] private bool _selectedExchangeNeedsPassphrase;
    [ObservableProperty] private string _selectedExchangeHint = "Select an exchange, paste your read-only Query keys, and click Save & Verify Live.";
    [ObservableProperty] private string _exchangeKeysStatusText = "";
    [ObservableProperty] private bool _isVerifyingExchangeKey;

    partial void OnSelectedExchangeOptionChanged(ExchangeKeyRow? value)
    {
        if (value is null)
        {
            SelectedExchangeNeedsPassphrase = false;
            return;
        }
        SelectedExchangeNeedsPassphrase = value.NeedsPassphrase;
        ExchangeKeyScope = string.IsNullOrWhiteSpace(value.Scope) ? "query" : value.Scope;
        if (value.PemHint)
            SelectedExchangeHint = "Coinbase Advanced CDP: paste the API Key Name and full EC Private Key PEM (newlines preserved).";
        else if (value.NeedsPassphrase)
            SelectedExchangeHint = "OKX requires API Key, API Secret, and the API Passphrase you created.";
        else
            SelectedExchangeHint = $"{value.Brand}: read-only Query permission is sufficient for live Portfolio Dashboard sync.";
    }

    [RelayCommand]
    private void ExchangeKeysReload()
    {
        var previousId = SelectedExchangeOption?.Id;
        ExchangeKeyRows.Clear();
        try
        {
            using var doc = _surfaces.Fetch("exchange_keys", "crypto");
            var root = doc.RootElement;
            if (root.TryGetProperty("exchanges", out var arr) && arr.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in arr.EnumerateArray())
                {
                    ExchangeKeyRows.Add(new ExchangeKeyRow
                    {
                        Id = PropG(item, "id"),
                        Brand = PropG(item, "brand"),
                        Tier = PropG(item, "tier"),
                        QuoteCurrency = PropG(item, "quote_currency"),
                        UsRetail = item.TryGetProperty("us_retail", out var ur) && ur.ValueKind == JsonValueKind.True,
                        NeedsPassphrase = item.TryGetProperty("needs_passphrase", out var np) && np.ValueKind == JsonValueKind.True,
                        PemHint = item.TryGetProperty("pem_hint", out var ph) && ph.ValueKind == JsonValueKind.True,
                        Configured = item.TryGetProperty("configured", out var cf) && cf.ValueKind == JsonValueKind.True,
                        Scope = PropG(item, "scope"),
                        VerifiedLocal = PropG(item, "verified_local"),
                        RateUsed = item.TryGetProperty("rate_used", out var ru) && ru.TryGetInt32(out var rui) ? rui : 0,
                        RateMax = item.TryGetProperty("rate_max", out var rm) && rm.TryGetInt32(out var rmi) ? rmi : 15,
                    });
                }
            }
            SelectedExchangeOption = (!string.IsNullOrEmpty(previousId)
                ? ExchangeKeyRows.FirstOrDefault(r => r.Id == previousId)
                : null) ?? ExchangeKeyRows.FirstOrDefault();

            var count = root.TryGetProperty("configured_count", out var cc) ? cc.ToString() : "0";
            var alpacaSet = root.TryGetProperty("alpaca", out var al)
                && al.TryGetProperty("configured", out var ac)
                && ac.ValueKind == JsonValueKind.True;
            ExchangeKeysStatusText = $"{count} CEX key(s) configured · Alpaca: {(alpacaSet ? "configured" : "not set")}";
        }
        catch (Exception ex)
        {
            ExchangeKeysStatusText = $"Could not load exchange keys inventory: {ex.Message}";
        }
    }

    [RelayCommand]
    private void SaveOnlyExchangeKey()
    {
        if (!WriteSelectedExchangeCreds(out var exchangeId, out var brand))
            return;
        ExchangeKeysStatusText = $"Saved {brand} keys to Windows CredMan (unverified).";
        ExchangeKeysReload();
        CredmanReload();
    }

    [RelayCommand]
    private async Task SaveAndVerifyExchangeKey()
    {
        if (!WriteSelectedExchangeCreds(out var exchangeId, out var brand))
            return;
        IsVerifyingExchangeKey = true;
        ExchangeKeysStatusText = $"Verifying {brand} keys live…";
        try
        {
            using var doc = await _surfaces.VerifyExchangeKeyAsync(exchangeId);
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            var msg = root.TryGetProperty("message", out var m) ? m.ToString() : (ok ? "Verified" : "Verify failed");
            await Dispatcher.UIThread.InvokeAsync(() =>
            {
                ExchangeKeysStatusText = ok ? $"✓ {msg}" : $"✗ {msg}";
                StatusText = ExchangeKeysStatusText;
                ExchangeKeysReload();
                CredmanReload();
            });
            if (ok)
                await DashboardSync();
        }
        catch (Exception ex)
        {
            ExchangeKeysStatusText = $"Verify failed: {ex.Message}";
        }
        finally
        {
            IsVerifyingExchangeKey = false;
        }
    }

    [RelayCommand]
    private async Task VerifyExchangeRow(string? exchangeId)
    {
        if (string.IsNullOrWhiteSpace(exchangeId))
            return;
        IsVerifyingExchangeKey = true;
        ExchangeKeysStatusText = $"Verifying {exchangeId}…";
        try
        {
            using var doc = await _surfaces.VerifyExchangeKeyAsync(exchangeId);
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            var msg = root.TryGetProperty("message", out var m) ? m.ToString() : "";
            ExchangeKeysStatusText = ok ? $"✓ {msg}" : $"✗ {msg}";
            StatusText = ExchangeKeysStatusText;
            ExchangeKeysReload();
        }
        catch (Exception ex)
        {
            ExchangeKeysStatusText = $"Verify failed: {ex.Message}";
        }
        finally
        {
            IsVerifyingExchangeKey = false;
        }
    }

    [RelayCommand]
    private void DeleteExchangeRow(string? exchangeId)
    {
        if (string.IsNullOrWhiteSpace(exchangeId))
            return;
        try
        {
            _credMan.Delete(CredManTargets.ExchangeTarget(exchangeId, "key"));
            _credMan.Delete(CredManTargets.ExchangeTarget(exchangeId, "secret"));
            _credMan.Delete(CredManTargets.ExchangeTarget(exchangeId, "meta"));
            _credMan.Delete(CredManTargets.ExchangePassphrase(exchangeId));
            ExchangeKeysStatusText = $"Removed {exchangeId} keys from Windows CredMan.";
            ExchangeKeysReload();
            CredmanReload();
        }
        catch (Exception ex)
        {
            ExchangeKeysStatusText = $"Delete failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task VerifyAlpacaKeys()
    {
        IsVerifyingExchangeKey = true;
        ExchangeKeysStatusText = "Verifying Alpaca keys…";
        try
        {
            using var doc = await _surfaces.VerifyExchangeKeyAsync("alpaca");
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            var msg = root.TryGetProperty("message", out var m) ? m.ToString() : "";
            ExchangeKeysStatusText = ok ? $"✓ {msg}" : $"✗ {msg}";
            StatusText = ExchangeKeysStatusText;
        }
        catch (Exception ex)
        {
            ExchangeKeysStatusText = $"Alpaca verify failed: {ex.Message}";
        }
        finally
        {
            IsVerifyingExchangeKey = false;
        }
    }

    [RelayCommand]
    private void OpenExchangeKeysSettings()
    {
        NavigateCommand.Execute("settings");
        SelectSettingsSectionCommand.Execute("keys");
    }

    private bool WriteSelectedExchangeCreds(out string exchangeId, out string brand)
    {
        exchangeId = SelectedExchangeOption?.Id ?? "";
        brand = SelectedExchangeOption?.Brand ?? exchangeId;
        if (string.IsNullOrWhiteSpace(exchangeId))
        {
            ExchangeKeysStatusText = "Select an exchange first.";
            return false;
        }
        var key = ExchangeApiKeyInput.Trim();
        var secret = ExchangeApiSecretInput.Trim();
        var pass = ExchangePassphraseInput.Trim();
        if (string.IsNullOrEmpty(key) || string.IsNullOrEmpty(secret))
        {
            ExchangeKeysStatusText = $"Both API Key and API Secret are required for {brand}.";
            return false;
        }
        if (SelectedExchangeNeedsPassphrase && string.IsNullOrEmpty(pass))
        {
            ExchangeKeysStatusText = $"{brand} requires an API Passphrase.";
            return false;
        }
        var scope = ExchangeKeyScope == "trade" ? "trade" : "query";
        _credMan.Write(CredManTargets.ExchangeTarget(exchangeId, "key"), key);
        _credMan.Write(CredManTargets.ExchangeTarget(exchangeId, "secret"), secret);
        _credMan.Write(CredManTargets.ExchangeTarget(exchangeId, "meta"), $"{{\"scope\":\"{scope}\",\"verified_at\":null}}");
        if (!string.IsNullOrEmpty(pass))
            _credMan.Write(CredManTargets.ExchangePassphrase(exchangeId), pass);
        else
            _credMan.Delete(CredManTargets.ExchangePassphrase(exchangeId));

        ExchangeApiKeyInput = "";
        ExchangeApiSecretInput = "";
        ExchangePassphraseInput = "";
        return true;
    }
}
