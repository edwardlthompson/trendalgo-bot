using System.Globalization;
using System.Text;
using System.Text.Json;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

public static class StrategyResultMapper
{
    public static StrategyResultRow FromJson(JsonElement row)
    {
        var ind = Str(row, "indicator", "strategy", "strategy_id");
        var role = ind switch
        {
            "Oracle max" => "oracle",
            "B&H" => "bh",
            _ => "",
        };
        var isBh = role == "bh";
        var tf = Str(row, "timeframe", "tf");
        var paramsText = FormatParams(row, isBh);
        var net = Opt(row, "net_pct", "net", "return_pct");
        var fees = Opt(row, "fees_paid", "fees");
        var trades = Opt(row, "trades");
        var tslHits = Opt(row, "tsl_hits");
        var wins = Opt(row, "wins");
        var losses = Opt(row, "losses");
        var openTrades = Opt(row, "open_trades");
        var winPct = Opt(row, "win_pct", "win_rate", "wr");
        if (winPct is > 0 and <= 1)
            winPct *= 100.0;

        if (!isBh && trades is >= 0)
        {
            var totalTrades = (int)Math.Round(trades.Value);
            var openN = Math.Clamp((int)Math.Round(openTrades ?? 0.0), 0, totalTrades);
            openTrades ??= openN;
            var closed = Math.Max(0, totalTrades - openN);
            if (wins is null && winPct is { } wp)
                wins = closed > 0 ? Math.Clamp(Math.Round(wp / 100.0 * closed), 0, closed) : 0;
            if (wins is { } wVal && losses is null)
                losses = Math.Max(0, closed - (int)Math.Round(wVal));
            if (winPct is null && wins is { } w2 && closed > 0)
                winPct = w2 / closed * 100.0;
        }

        var tsl = Opt(row, "trailing_stop_loss_pct", "trailing_stop_pct", "tsl");
        double? tslHitPct = null;
        if (trades is > 0 && tslHits is { })
            tslHitPct = tslHits.Value / trades.Value * 100.0;
        var strength = isBh ? null : Opt(row, "strength");
        if (!isBh && strength is null && trades is > 0)
        {
            var totalTrades = (int)Math.Round(trades.Value);
            var openN = Math.Clamp((int)Math.Round(openTrades ?? 0.0), 0, totalTrades);
            var closed = Math.Max(0, totalTrades - openN);
            if (closed > 0)
            {
                var winN = Math.Clamp((int)Math.Round(wins ?? 0.0), 0, closed);
                var hits = Math.Clamp((int)Math.Round(tslHits ?? 0.0), 0, closed);
                strength = ComputeIndicatorStrength(closed, winN, hits);
            }
        }
        var skip = Str(row, "skip_reason");

        string openCell;
        string winsCell;
        string lossesCell;
        if (!string.IsNullOrWhiteSpace(skip) && (trades is null or 0))
        {
            openCell = "—";
            winsCell = $"0 ({skip})";
            lossesCell = "—";
        }
        else if (isBh || wins is null)
        {
            openCell = "—";
            winsCell = "—";
            lossesCell = "—";
        }
        else
        {
            openCell = openTrades?.ToString("0", CultureInfo.InvariantCulture) ?? "0";
            winsCell = wins.Value.ToString("0", CultureInfo.InvariantCulture);
            lossesCell = losses?.ToString("0", CultureInfo.InvariantCulture) ?? "—";
        }

        string tslCell;
        if (isBh || tsl is null)
            tslCell = "—";
        else if (Math.Abs(tsl.Value) < 1e-9)
            tslCell = "0% (signal)";
        else
            tslCell = $"{TslDisplayPct(tsl.Value)}%";

        var label = role switch
        {
            "oracle" => "Oracle max",
            "bh" => "B&H — buy & hold",
            _ => ind,
        };

        var ev = Str(row, "events_label", "events");
        return new StrategyResultRow
        {
            Indicator = label,
            Timeframe = string.IsNullOrWhiteSpace(tf) ? "—" : tf,
            Params = paramsText,
            ParamsText = paramsText,
            NetPctText = DashPct(net),
            FeesText = FeesCell(fees),
            OpenText = openCell,
            WinsText = winsCell,
            LossesText = lossesCell,
            WinPctText = isBh ? "—" : DashPct(winPct),
            TslText = tslCell,
            TslHitsText = isBh || tslHits is null ? "—" : tslHits.Value.ToString("0", CultureInfo.InvariantCulture),
            TslHitPctText = isBh ? "—" : DashPct(tslHitPct),
            StrengthText = strength is null ? "—" : strength.Value.ToString("0.0", CultureInfo.InvariantCulture),
            EventsText = string.IsNullOrWhiteSpace(ev) ? "·" : ev,
            Role = role,
            NetPct = net,
            FeesPaid = fees,
            OpenTrades = openTrades,
            Wins = wins,
            Losses = losses,
            WinPct = winPct,
            TslPct = tsl,
            TslHits = tslHits,
            TslHitPct = tslHitPct,
            Strength = strength,
        };
    }

    public static void ApplyHeat(IList<StrategyResultRow> rows)
    {
        Rank(rows, r => r.NetPct, invert: false, (r, h) => r.HeatNet = h);
        Rank(rows, r => r.FeesPaid, invert: true, (r, h) => r.HeatFees = h);
        Rank(rows, r => r.OpenTrades, invert: true, (r, h) => r.HeatOpen = h);
        Rank(rows, r => r.Wins, invert: false, (r, h) => r.HeatWins = h);
        Rank(rows, r => r.Losses, invert: true, (r, h) => r.HeatLosses = h);
        Rank(rows, r => r.WinPct, invert: false, (r, h) => r.HeatWinPct = h);
        Rank(rows, r => r.TslHits, invert: true, (r, h) => r.HeatTslHits = h);
        Rank(rows, r => r.TslHitPct, invert: true, (r, h) => r.HeatTslHitPct = h);
        Rank(rows, r => r.Strength, invert: false, (r, h) => r.HeatStrength = h);
    }

    private static void Rank(
        IList<StrategyResultRow> rows,
        Func<StrategyResultRow, double?> selector,
        bool invert,
        Action<StrategyResultRow, string?> assign)
    {
        var values = rows.Select(selector).ToList();
        var colors = BoardHeatRanker.Rank(values, invert: invert);
        for (var i = 0; i < rows.Count; i++)
            assign(rows[i], colors[i]);
    }

    private static string FormatParams(JsonElement row, bool isBh)
    {
        if (isBh)
            return "—";
        if (row.TryGetProperty("params", out var p) && p.ValueKind == JsonValueKind.Object)
        {
            var sb = new StringBuilder();
            foreach (var prop in p.EnumerateObject())
            {
                if (prop.Name is "heartbeat_dossier" or "coincidence_entry" or "coincidence_exit")
                    continue;
                if (sb.Length > 0)
                    sb.Append(", ");
                sb.Append(prop.Name).Append('=').Append(prop.Value.ToString());
            }
            var tsl = Opt(row, "trailing_stop_loss_pct", "trailing_stop_pct");
            if (tsl is { } t)
            {
                if (sb.Length > 0)
                    sb.Append(", ");
                sb.Append("tsl=").Append(TslDisplayPct(t)).Append('%');
            }
            return sb.Length == 0 ? "—" : sb.ToString();
        }
        var raw = Str(row, "params_text", "params");
        return string.IsNullOrWhiteSpace(raw) ? "—" : raw;
    }

    private static string DashPct(double? v) =>
        v is null ? "—" : $"{(v.Value >= 0 ? "+" : "")}{v.Value.ToString("0.0", CultureInfo.InvariantCulture)}%";

    private static string FeesCell(double? fees) => MoneyFormat.UsdPrecise(fees);

    private static int TslDisplayPct(double value)
    {
        if (value <= 0)
            return 0;
        if (value < 1.0)
            return Math.Max(1, (int)Math.Round(value * 100.0));
        return Math.Max(0, (int)Math.Round(value));
    }

    private static string Str(JsonElement row, params string[] keys)
    {
        foreach (var k in keys)
        {
            if (row.TryGetProperty(k, out var p) && p.ValueKind != JsonValueKind.Null)
                return p.ToString();
        }
        return "";
    }

    private static double? Opt(JsonElement row, params string[] keys)
    {
        foreach (var k in keys)
        {
            if (!row.TryGetProperty(k, out var p) || p.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined)
                continue;
            if (p.ValueKind == JsonValueKind.Number && p.TryGetDouble(out var n))
                return n;
            if (p.ValueKind == JsonValueKind.String
                && double.TryParse(p.GetString(), NumberStyles.Float, CultureInfo.InvariantCulture, out var s))
                return s;
        }
        return null;
    }

    private static double ComputeIndicatorStrength(int closedTrades, int wins, int tslHits)
    {
        if (closedTrades <= 0)
            return 0.0;
        const double z = 1.96;
        var p = (double)Math.Clamp(wins, 0, closedTrades) / closedTrades;
        var z2 = z * z;
        var denom = 1.0 + z2 / closedTrades;
        var centre = p + z2 / (2.0 * closedTrades);
        var margin = z * Math.Sqrt((p * (1.0 - p) + z2 / (4.0 * closedTrades)) / closedTrades);
        var wilson = Math.Clamp((centre - margin) / denom, 0.0, 1.0);
        var exitQuality = Math.Pow(1.0 - (double)Math.Clamp(tslHits, 0, closedTrades) / closedTrades, 1.5);
        return Math.Round(100.0 * wilson * exitQuality, 1);
    }
}
