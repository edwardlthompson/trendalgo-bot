using System.Text.Json;

namespace TrendAlgo.Shell.Services;

/// <summary>Instant in-memory ETA calculation matching scan_settings_eta.py.</summary>
public sealed class ScanSettingsEtaCalculator
{
    public double MeanLoad1hS { get; private set; } = 2.0;
    public double MeanLoad1mS { get; private set; } = 45.0;
    public double MeanPerStratTfS { get; private set; } = 0.08;
    public double MeanMcS { get; private set; } = 0.9;
    public double MeanSauceS { get; private set; } = 45.0;
    public int FallbackCryptoCoins { get; private set; } = 40;
    public int ForexCoins { get; private set; } = 20;

    private int _funnelListed;
    private int _funnelAfterVol;
    private int _funnelAfterAct;
    private int _funnelQualified;
    private double _funnelLastVol;
    private bool _hasFunnel;

    private sealed record LaneCalibration(
        double Load1hS, double Load1mS, double PerStratTfS, double McS, double SauceS, double BarsOverheadS);

    private readonly Dictionary<string, LaneCalibration> _laneCal = new(StringComparer.OrdinalIgnoreCase);

    public string BenchmarkRanAt { get; private set; } = "";

    public sealed record Result(
        string Lines,
        string Total,
        bool Overrun,
        string Warning,
        decimal RecommendedIntervalMinutes);

    public void LoadCalibration(JsonElement eta)
    {
        if (!eta.TryGetProperty("calibration", out var cal) || cal.ValueKind != JsonValueKind.Object)
            return;
        MeanLoad1hS = Dbl(cal, "mean_load_1h_s", MeanLoad1hS);
        MeanLoad1mS = Dbl(cal, "mean_load_1m_s", MeanLoad1mS);
        MeanPerStratTfS = Dbl(cal, "mean_per_strat_tf_s", MeanPerStratTfS);
        MeanMcS = Dbl(cal, "mean_mc_s", MeanMcS);
        MeanSauceS = Dbl(cal, "mean_sauce_s", MeanSauceS);
        FallbackCryptoCoins = Math.Max(1, Int(cal, "crypto_coins", FallbackCryptoCoins));
        ForexCoins = Math.Max(1, Int(cal, "forex_coins", ForexCoins));
        BenchmarkRanAt = cal.TryGetProperty("benchmark_ran_at", out var bra) ? bra.GetString() ?? "" : "";
        _laneCal.Clear();
        if (cal.TryGetProperty("lanes_calibration", out var lc) && lc.ValueKind == JsonValueKind.Object)
        {
            foreach (var prop in lc.EnumerateObject())
            {
                if (prop.Value.ValueKind != JsonValueKind.Object)
                    continue;
                _laneCal[prop.Name] = new LaneCalibration(
                    Dbl(prop.Value, "mean_load_1h_s", MeanLoad1hS),
                    Dbl(prop.Value, "mean_load_1m_s", MeanLoad1mS),
                    Dbl(prop.Value, "mean_per_strat_tf_s", MeanPerStratTfS),
                    Dbl(prop.Value, "mean_mc_s", MeanMcS),
                    Dbl(prop.Value, "mean_sauce_s", MeanSauceS),
                    Dbl(prop.Value, "bars_overhead_s", 2.0));
            }
        }
        if (cal.TryGetProperty("funnel", out var fn) && fn.ValueKind == JsonValueKind.Object)
        {
            _funnelListed = Math.Max(0, Int(fn, "listed_n", 0));
            _funnelAfterVol = Math.Max(0, Int(fn, "after_volume_n", 0));
            _funnelAfterAct = Math.Max(0, Int(fn, "after_activity_n", _funnelAfterVol));
            _funnelQualified = Math.Max(0, Int(fn, "qualified_n", 0));
            _funnelLastVol = Dbl(fn, "min_volume_usd", 0.0);
            _hasFunnel = _funnelListed > 0 || _funnelAfterVol > 0 || _funnelQualified > 0;
        }
    }

    public Result Compute(
        int nStrategies,
        int nTimeframes,
        bool hadSubhour,
        double minVolumeUsd,
        bool requireContinuous1h,
        bool marketContext,
        bool sauceWithScan,
        int sauceTopN,
        bool autoCrypto,
        bool autoTradfi,
        bool autoForex,
        int tradfiTopN,
        int intervalMinutes)
    {
        var cryptoN = ProjectCryptoCoins(minVolumeUsd, requireContinuous1h);
        var tradfiN = tradfiTopN > 0 ? tradfiTopN : 40;
        var lanes = new (string Name, int Coins, bool AutoOn)[]
        {
            ("Crypto", cryptoN, autoCrypto),
            ("TradFi", tradfiN, autoTradfi),
            ("Forex", ForexCoins, autoForex),
        };
        var lines = new List<string>(3);
        var grand = 0.0;
        foreach (var (name, coins, autoOn) in lanes)
        {
            var cal = _laneCal.TryGetValue(name, out var lc)
                ? lc
                : new LaneCalibration(MeanLoad1hS, MeanLoad1mS, MeanPerStratTfS, MeanMcS, MeanSauceS, name == "TradFi" ? 35.0 : 2.0);
            var load = hadSubhour ? cal.Load1mS : cal.Load1hS;
            var per = Math.Max(0.5, load + Math.Max(0, nStrategies) * Math.Max(0, nTimeframes) * cal.PerStratTfS);
            var catalog = per * coins;
            var mc = marketContext ? Math.Max(0.0, cal.McS) * coins : 0.0;
            var sCoins = sauceWithScan ? Math.Max(0, Math.Min(sauceTopN, coins)) : 0;
            var sauce = Math.Max(0.0, cal.SauceS) * sCoins;
            var total = catalog + mc + sauce;
            var mcText = marketContext ? $"MC ~{FmtS(mc)} (~{FmtS(cal.McS)}/coin)" : "MC off";
            var sauceText = sauceWithScan && sauceTopN > 0
                ? $"Sauce ~{FmtS(sauce)} (top {sCoins} × ~{FmtS(cal.SauceS)})"
                : "Sauce off";
            lines.Add(
                $"{name}: Est. ~{FmtS(per)} catalog/coin · ~{FmtS(total)} total for {coins} coin{(coins != 1 ? "s" : "")}"
                + $" · {mcText} · {sauceText}");
            if (autoOn)
                grand += total + cal.BarsOverheadS;
        }
        var iv = Math.Max(15, intervalMinutes);
        var overrun = grand > iv * 60.0 * 0.85;
        var rec = (decimal)Math.Clamp((int)(Math.Ceiling((grand / 60.0) * 1.25 / 15.0) * 15), 15, 1440);
        var warn = overrun
            ? $"Estimated auto-scan (~{FmtDur(grand)}) risks overlapping your {iv}m schedule. Raise interval to {rec}m or reduce timeframes/strategies."
            : "";
        var totalStr = grand <= 0.0
            ? "Grand total (auto-scan on): 0s (no auto-scan desks enabled)"
            : $"Grand total (auto-scan on): ~{FmtDur(grand)}";
        return new Result(string.Join("\n", lines), totalStr, overrun, warn, rec);
    }

    private int ProjectCryptoCoins(double minVolumeUsd, bool requireContinuous1h)
    {
        if (!_hasFunnel)
            return FallbackCryptoCoins;
        var listed = Math.Max(Math.Max(_funnelListed, _funnelAfterVol), Math.Max(_funnelAfterAct, Math.Max(_funnelQualified, 1)));
        var afterVol = Math.Min(listed, Math.Max(_funnelAfterVol, Math.Max(_funnelAfterAct, _funnelQualified)));
        var afterAct = Math.Min(afterVol, Math.Max(_funnelAfterAct, _funnelQualified));
        var volP = ScaleVol(afterVol, listed, _funnelLastVol, minVolumeUsd);
        var actP = Math.Min(volP, ScaleVol(afterAct, listed, _funnelLastVol, minVolumeUsd));
        return Math.Max(1, Math.Min(listed, requireContinuous1h ? actP : volP));
    }

    private static int ScaleVol(int n, int listed, double lastVol, double newVol)
    {
        var l = Math.Max(lastVol, 1.0);
        var nv = Math.Max(newVol, 1.0);
        if (Math.Abs(l - nv) < 1e-9)
            return Math.Max(1, Math.Min(listed, n));
        var scaled = (int)Math.Round(n * Math.Pow(l / nv, 0.4));
        return Math.Max(1, Math.Min(listed, scaled));
    }

    private static string FmtS(double s) =>
        s < 60 ? $"{s:0}s" : (s / 60.0 < 60 ? $"{s / 60.0:0.0}m" : $"{s / 3600.0:0.0}h");

    private static string FmtDur(double s) =>
        s < 90 ? $"{s:0}s" : (s < 3600 ? $"{s / 60.0:0.0}m" : $"{s / 3600.0:0.0}h");

    private static double Dbl(JsonElement e, string k, double fb) =>
        e.TryGetProperty(k, out var p) && p.TryGetDouble(out var v) ? v : fb;

    private static int Int(JsonElement e, string k, int fb) =>
        e.TryGetProperty(k, out var p) && p.TryGetInt32(out var v) ? v : fb;
}
