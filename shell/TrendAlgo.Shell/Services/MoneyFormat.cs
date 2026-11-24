using System.Globalization;

namespace TrendAlgo.Shell.Services;

/// <summary>Compact USD / volume display — mirrors <c>lts_scan_model.dash(money=True)</c> / <c>volume_display</c>.</summary>
public static class MoneyFormat
{
    public static string Usd(double? value)
    {
        if (value is null || double.IsNaN(value.Value))
            return "—";
        var number = value.Value;
        if (number >= 1_000_000)
            return $"${number / 1_000_000:0.0}M";
        if (number >= 1_000)
            return $"${number / 1_000:0}K";
        return $"${number.ToString("0", CultureInfo.InvariantCulture)}";
    }

    public static string UsdPrecise(double? value)
    {
        if (value is null || double.IsNaN(value.Value))
            return "—";
        return $"${value.Value.ToString("0.00", CultureInfo.InvariantCulture)}";
    }

    /// <summary>USD notional for crypto/TradFi; Forex tick/range volume without $.</summary>
    public static string Volume(double value, string? volumeUnit, string? exchangeId)
    {
        if (double.IsNaN(value) || Math.Abs(value) < 1e-12)
            return "—";
        var unit = (volumeUnit ?? "").Trim().ToLowerInvariant();
        var eid = (exchangeId ?? "").Trim().ToLowerInvariant();
        if (unit is "ticks" or "range" || eid == "forex")
        {
            if (value >= 1_000_000)
                return $"{value / 1_000_000:0.0}M";
            if (value >= 1_000)
                return $"{value / 1_000:0}K";
            return value.ToString("0", CultureInfo.InvariantCulture);
        }
        return Usd(value);
    }
}
