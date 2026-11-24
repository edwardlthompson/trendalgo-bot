using Avalonia.Media;

namespace TrendAlgo.Shell.Models;

public sealed class ExchangeKeyRow
{
    public string Id { get; init; } = "";
    public string Brand { get; init; } = "";
    public string Tier { get; init; } = "";
    public string QuoteCurrency { get; init; } = "USD";
    public bool UsRetail { get; init; }
    public bool NeedsPassphrase { get; init; }
    public bool PemHint { get; init; }
    public bool Configured { get; init; }
    public string Scope { get; init; } = "query";
    public string VerifiedLocal { get; init; } = "";
    public int RateUsed { get; init; }
    public int RateMax { get; init; }

    public string StatusBadge => !Configured
        ? "Not set"
        : string.IsNullOrWhiteSpace(VerifiedLocal)
            ? "Saved (unverified)"
            : $"✓ Verified {VerifiedLocal}";

    public IBrush StatusBrush => !Configured
        ? new SolidColorBrush(Color.Parse("#64748B"))
        : string.IsNullOrWhiteSpace(VerifiedLocal)
            ? new SolidColorBrush(Color.Parse("#F59E0B"))
            : new SolidColorBrush(Color.Parse("#3DDC97"));

    public string ScopeDisplay => Configured ? Scope.ToUpperInvariant() : "—";
    public string RateDisplay => Configured ? $"{RateUsed}/{RateMax}/m" : "—";
    public string DisplayLabel => $"{Brand} (Tier {Tier} · {QuoteCurrency})";
}
