using System.Text.Json;
using Avalonia.Controls;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.Services;

public static class DeskSurfacePresenter
{
    public static Window Build(string surface, string pair, JsonElement root, string lane = "crypto")
    {
        return surface switch
        {
            "chart" => BuildChart(pair, root),
            "dex" => BuildDex(root),
            "events" => BuildEvents(pair, root),
            "sauce" => BuildSauce(pair, root),
            _ => BuildResults(pair, root, lane),
        };
    }

    private static Window BuildChart(string pair, JsonElement root)
    {
        var closes = new List<double>();
        if (root.TryGetProperty("closes", out var arr) && arr.ValueKind == JsonValueKind.Array)
        {
            foreach (var c in arr.EnumerateArray())
            {
                if (c.TryGetDouble(out var v))
                    closes.Add(v);
            }
        }
        var ohlc = new List<(double O, double H, double L, double C)>();
        if (root.TryGetProperty("ohlc", out var ohlcArr) && ohlcArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var c in ohlcArr.EnumerateArray())
            {
                if (c.TryGetProperty("o", out var o) && o.TryGetDouble(out var ov)
                    && c.TryGetProperty("h", out var h) && h.TryGetDouble(out var hv)
                    && c.TryGetProperty("l", out var l) && l.TryGetDouble(out var lv)
                    && c.TryGetProperty("c", out var cl) && cl.TryGetDouble(out var cv))
                    ohlc.Add((ov, hv, lv, cv));
            }
        }
        var trades = new List<(string Side, double Price, int Index)>();
        if (root.TryGetProperty("trades", out var trArr) && trArr.ValueKind == JsonValueKind.Array)
        {
            var i = 0;
            foreach (var t in trArr.EnumerateArray())
            {
                var side = Str(t, "side");
                if (t.TryGetProperty("price", out var p) && p.TryGetDouble(out var price))
                    trades.Add((side, price, Math.Min(i, Math.Max(0, ohlc.Count - 1))));
                i++;
            }
        }
        var rows = new List<SurfaceGridRow>();
        if (root.TryGetProperty("candles", out var candles) && candles.ValueKind == JsonValueKind.Array)
        {
            foreach (var c in candles.EnumerateArray())
                rows.Add(Row(Str(c, "i"), Str(c, "close"), Fmt(Str(c, "from_high_pct")), "", ""));
        }
        else
        {
            for (var i = 0; i < closes.Count; i++)
                rows.Add(Row((i + 1).ToString(), closes[i].ToString("G6"), "", "", ""));
        }
        var stats =
            $"bars={Str(root, "bars")} last={Str(root, "last")} high={Str(root, "high")} low={Str(root, "low")} Δ%={Fmt(Str(root, "change_pct"))} ohlc={ohlc.Count} trades={trades.Count}";
        var note = ohlc.Count >= 2
            ? "OHLC candles from chart_ohlc_1h; blue=entry · amber=exit markers."
            : "Close sparkline fallback — OHLC fills when lane enrich stores chart_ohlc_1h.";
        var cleanPair = pair.Contains('|') ? pair.Split('|')[0] : pair;
        var winLabel = Str(root, "window");
        if (string.IsNullOrWhiteSpace(winLabel))
            winLabel = pair.EndsWith("|7d", StringComparison.OrdinalIgnoreCase) ? "7D" : "30D";
        var win = new ChartSurfaceWindow();
        win.Bind($"{cleanPair} — {winLabel} Chart", stats, note, rows, closes, ohlc, trades);
        return win;
    }

    private static Window BuildDex(JsonElement root)
    {
        var rows = new List<SurfaceGridRow>();
        foreach (var r in RowsOf(root))
        {
            var liq = OptMoney(r, "liquidity_usd");
            var vol = OptMoney(r, "volume_proxy_usd");
            rows.Add(Row(
                Str(r, "pair"),
                liq,
                Num(r, "price_change_24h_pct"),
                vol,
                Str(r, "source")));
        }
        var win = new DeskSurfaceWindow();
        win.Bind("DEX pool watch", rows, $"{rows.Count} pools from dex_watch_rows.json",
            "Research only — not investment advice. DEX liquidity can vanish.",
            ("Pair", "Liquidity", "24h %", "Vol proxy", "Source"),
            enableFilter: true);
        return win;
    }

    private static Window BuildEvents(string pair, JsonElement root)
    {
        var closes = new List<double>();
        if (root.TryGetProperty("closes", out var arr) && arr.ValueKind == JsonValueKind.Array)
        {
            foreach (var c in arr.EnumerateArray())
            {
                if (c.TryGetDouble(out var v))
                    closes.Add(v);
            }
        }
        var rows = new List<CoinEventRow>();
        foreach (var r in RowsOf(root))
        {
            double? frac = null;
            if (r.TryGetProperty("marker_frac", out var mf) && mf.TryGetDouble(out var fv))
                frac = fv;
            var idx = 0;
            if (r.TryGetProperty("index", out var ix) && ix.TryGetInt32(out var iv))
                idx = iv;
            rows.Add(new CoinEventRow
            {
                Index = idx,
                Date = Str(r, "date", "displayed_date"),
                Title = Str(r, "title"),
                Source = Str(r, "source", "category"),
                Note = Str(r, "note"),
                Url = Str(r, "url"),
                MarkerFrac = frac,
            });
        }
        var title = Str(root, "title");
        if (string.IsNullOrWhiteSpace(title))
            title = $"{pair} — Events";
        var hint = Str(root, "hint");
        if (string.IsNullOrWhiteSpace(hint))
            hint = "Calendar cache only (CMC / Coindar / macro)";
        var empty = Str(root, "empty");
        var win = new CoinEventsTimelineWindow();
        win.Bind(title, hint, empty, rows, closes);
        return win;
    }

    private static Window BuildSauce(string pair, JsonElement root)
    {
        var rows = new List<SurfaceGridRow>();
        if (root.TryGetProperty("dossier", out var dos) && dos.ValueKind == JsonValueKind.Object)
        {
            foreach (var p in dos.EnumerateObject())
                rows.Add(Row(p.Name, p.Value.ToString(), "", "", ""));
        }
        var win = new DeskSurfaceWindow();
        win.Bind($"Secret Sauce study — {pair}", rows,
            rows.Count == 0
                ? "Empty until Sauce job fills heartbeat_dossier"
                : $"{rows.Count} dossier fields",
            headers: ("Field", "Value", "", "", ""),
            enableFilter: true);
        return win;
    }

    private static Window BuildResults(string pair, JsonElement root, string lane = "crypto")
    {
        var rows = new List<StrategyResultRow>();
        foreach (var r in RowsOf(root))
            rows.Add(StrategyResultMapper.FromJson(r));
        StrategyResultMapper.ApplyHeat(rows);

        var signal = "";
        var levels = "";
        var risk = "";
        var structure = "";
        if (root.TryGetProperty("market_context_summary", out var sum)
            && sum.ValueKind == JsonValueKind.Object)
        {
            signal = Str(sum, "signal");
            levels = Str(sum, "levels");
            risk = Str(sum, "risk");
            structure = Str(sum, "structure");
        }

        JsonElement? marketCtx = root.TryGetProperty("market_context", out var mcEl)
            && mcEl.ValueKind == JsonValueKind.Object
            ? mcEl
            : null;
        var deskLane = string.IsNullOrWhiteSpace(lane) ? "crypto" : lane;
        var win = new ResultsSurfaceWindow();
        win.Bind(
            $"{pair} — All-TA Results",
            rows,
            $"{rows.Count} strategies · Oracle/B&H pinned",
            signal,
            levels,
            risk,
            structure,
            marketContext: marketCtx,
            onGlossary: async selected =>
            {
                var term = selected?.Indicator ?? "";
                var clean = term.Split('—')[0].Trim();
                if (clean.EndsWith(" *", StringComparison.Ordinal))
                    clean = clean[..^2].Trim();
                var popup = new GlossaryPopupWindow();
                try
                {
                    if (string.IsNullOrWhiteSpace(clean))
                    {
                        popup.Bind("Glossary", "Results",
                            "Select a strategy row, then Glossary — or open the Glossary page.");
                    }
                    else
                    {
                        using var doc = new DeskSurfaceClient().Fetch("glossary", deskLane, clean);
                        BindGlossaryPopup(popup, doc.RootElement, clean);
                    }
                }
                catch (Exception ex)
                {
                    popup.Bind(clean, "Results", $"Glossary lookup failed: {ex.Message}");
                }
                await popup.ShowDialog(win);
            },
            onSharePng: async () =>
            {
                try
                {
                    var safe = pair.Replace('/', '-');
                    var suggested = $"strategy-{safe}-{DateTime.Now:yyyy-MM-dd}.png";
                    var dest = await SharePngPicker.PickAsync(win, suggested);
                    if (dest is null)
                    {
                        win.BindNote("Share PNG cancelled");
                        return;
                    }
                    using var doc = new DeskSurfaceClient().SharePng(
                        "strategy", deskLane, pair, dest);
                    var path = Str(doc.RootElement, "path", "png", "file");
                    win.BindNote(string.IsNullOrWhiteSpace(path)
                        ? $"Share PNG exported for {pair}"
                        : $"Share PNG → {path}");
                }
                catch (Exception ex)
                {
                    win.BindNote($"Share PNG failed: {ex.Message}");
                }
            },
            onChart: async windowKey =>
            {
                try
                {
                    using var doc = await LoadingWindow.RunAsync(
                        win,
                        $"Loading {pair} {windowKey.ToUpperInvariant()} chart…",
                        () => new DeskSurfaceClient().FetchAsync("chart", deskLane, $"{pair}|{windowKey}"));
                    var chartWin = Build("chart", $"{pair}|{windowKey}", doc.RootElement, deskLane);
                    await chartWin.ShowDialog(win);
                }
                catch (Exception ex)
                {
                    win.BindNote($"Chart failed: {ex.Message}");
                }
            },
            onEvents: async () =>
            {
                try
                {
                    using var doc = await LoadingWindow.RunAsync(
                        win,
                        $"Loading {pair} events…",
                        () => new DeskSurfaceClient().FetchAsync("events", deskLane, pair));
                    var evWin = Build("events", pair, doc.RootElement, deskLane);
                    await evWin.ShowDialog(win);
                }
                catch (Exception ex)
                {
                    win.BindNote($"Events failed: {ex.Message}");
                }
            },
            onCreateBot: async selected =>
            {
                var ind = selected?.Indicator ?? "";
                if (string.IsNullOrWhiteSpace(ind)
                    || ind.StartsWith("Oracle", StringComparison.OrdinalIgnoreCase)
                    || ind.StartsWith("B&H", StringComparison.Ordinal))
                {
                    win.BindNote("Pick a non-Oracle / non-B&H strategy row, then Create Bot.");
                    return;
                }
                var clean = ind.Split('—')[0].Trim();
                try
                {
                    using var created = new DeskSurfaceClient().CreateBot(pair, clean);
                    var name = Str(created.RootElement, "name");
                    win.BindNote(string.IsNullOrWhiteSpace(name)
                        ? $"Create Bot queued for {pair} · {clean}"
                        : $"Created bot «{name}» · {pair} · {clean}");
                }
                catch (Exception ex)
                {
                    win.BindNote($"Create Bot failed: {ex.Message}");
                }
                await Task.CompletedTask;
            });
        return win;
    }

    internal static void BindGlossaryPopup(GlossaryPopupWindow popup, JsonElement root, string query)
    {
        if (root.TryGetProperty("found", out var found) && found.ValueKind == JsonValueKind.True
            && root.TryGetProperty("entry", out var entry) && entry.ValueKind == JsonValueKind.Object)
        {
            popup.Bind(
                Str(entry, "title"),
                Str(entry, "subtitle", "category"),
                Str(entry, "long"),
                Str(entry, "formula"),
                Str(entry, "formula_label"));
            return;
        }
        var missTitle = Str(root, "miss_title");
        var missBody = Str(root, "miss_body");
        popup.Bind(
            string.IsNullOrWhiteSpace(missTitle) ? "No glossary entry" : missTitle,
            "TA glossary",
            string.IsNullOrWhiteSpace(missBody)
                ? $"No bundled glossary item matched {query}."
                : missBody);
    }

    private static SurfaceGridRow Row(string a, string b, string c, string d, string e) =>
        new() { Col1 = a, Col2 = b, Col3 = c, Col4 = d, Col5 = e };

    private static IEnumerable<JsonElement> RowsOf(JsonElement root)
    {
        if (root.TryGetProperty("rows", out var rows) && rows.ValueKind == JsonValueKind.Array)
            return rows.EnumerateArray();
        return Array.Empty<JsonElement>();
    }

    private static string Str(JsonElement row, params string[] keys)
    {
        foreach (var k in keys)
        {
            if (row.TryGetProperty(k, out var p))
                return p.ToString();
        }
        return "";
    }

    private static string Num(JsonElement row, params string[] keys) => Str(row, keys);

    private static string OptMoney(JsonElement row, params string[] keys)
    {
        foreach (var k in keys)
        {
            if (!row.TryGetProperty(k, out var p) || p.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined)
                continue;
            if (p.ValueKind == JsonValueKind.Number && p.TryGetDouble(out var n))
                return MoneyFormat.Usd(n);
            if (p.ValueKind == JsonValueKind.String
                && double.TryParse(p.GetString(), System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out var s))
                return MoneyFormat.Usd(s);
        }
        return "—";
    }

    private static string Fmt(string raw)
    {
        if (double.TryParse(raw, out var v))
            return v.ToString("0.##");
        return raw;
    }
}
