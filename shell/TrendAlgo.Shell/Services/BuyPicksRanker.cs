using System.Text.Json;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

/// <summary>Synchronous in-memory Market Context (Buy Picks) ranker — mirrors device/buy_picks.py.</summary>
public static class BuyPicksRanker
{
    public static IReadOnlyList<BuyPickRow> FromBoardRows(IEnumerable<OpportunityBoardRow> boardRows)
    {
        var list = new List<BuyPickRow>();
        foreach (var row in boardRows)
        {
            if (string.IsNullOrWhiteSpace(row.PayloadJson))
                continue;
            try
            {
                using var doc = JsonDocument.Parse(row.PayloadJson);
                var root = doc.RootElement;
                if (!root.TryGetProperty("market_context", out var mc)
                    || mc.ValueKind != JsonValueKind.Object)
                    continue;
                if (!mc.TryGetProperty("ok", out var okEl) || okEl.ValueKind != JsonValueKind.True)
                    continue;

                var cons = mc.TryGetProperty("consensus", out var consEl)
                    && consEl.ValueKind == JsonValueKind.Object
                    ? consEl
                    : default;
                var structEl = mc.TryGetProperty("structure", out var stEl)
                    && stEl.ValueKind == JsonValueKind.Object
                    ? stEl
                    : default;
                var risk = mc.TryGetProperty("risk", out var rEl)
                    && rEl.ValueKind == JsonValueKind.Object
                    ? rEl
                    : default;

                var score = OptD(cons, "score") ?? 0.0;
                var conf = OptD(cons, "confidence") ?? 0.0;
                var signal = Str(cons, "signal");
                if (string.IsNullOrWhiteSpace(signal))
                    signal = "Neutral";
                var pair = Str(root, "pair");
                if (string.IsNullOrWhiteSpace(pair))
                    pair = row.Pair;

                list.Add(new BuyPickRow
                {
                    Pair = pair.Trim().ToUpperInvariant(),
                    Signal = signal,
                    Score = score,
                    Confidence = conf,
                    NearestSr = NullIfEmpty(Str(structEl, "nearest_sr_name")),
                    RrR1 = OptD(risk, "rr_to_r1"),
                    Confluence = (int)(OptD(structEl, "confluence") ?? 0.0),
                    Regime = NullIfEmpty(Str(mc, "regime_label")),
                    BotBestNet = OptD(root, "bot_best_net_pct"),
                    BotBestLabel = NullIfEmpty(Str(root, "bot_best_label")),
                });
            }
            catch
            {
                /* skip malformed row JSON */
            }
        }

        list.Sort((a, b) =>
        {
            var c = b.Score.CompareTo(a.Score);
            if (c != 0)
                return c;
            var ab = a.BotBestNet ?? double.NegativeInfinity;
            var bb = b.BotBestNet ?? double.NegativeInfinity;
            c = bb.CompareTo(ab);
            if (c != 0)
                return c;
            return b.Confidence.CompareTo(a.Confidence);
        });
        return list;
    }

    private static string Str(JsonElement el, string key)
    {
        if (el.ValueKind != JsonValueKind.Object)
            return "";
        return el.TryGetProperty(key, out var p) && p.ValueKind != JsonValueKind.Null
            ? p.ToString()
            : "";
    }

    private static string? NullIfEmpty(string value) =>
        string.IsNullOrWhiteSpace(value) ? null : value;

    private static double? OptD(JsonElement el, string key)
    {
        if (el.ValueKind != JsonValueKind.Object)
            return null;
        return el.TryGetProperty(key, out var p)
            && p.ValueKind == JsonValueKind.Number
            && p.TryGetDouble(out var v)
            ? v
            : null;
    }
}
