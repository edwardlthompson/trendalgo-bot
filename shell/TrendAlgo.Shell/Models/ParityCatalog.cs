namespace TrendAlgo.Shell.Models;

/// <summary>Inventory §12 P0 surfaces (docs/PRODUCT_SURFACE_INVENTORY.md).</summary>
public static class ParityCatalog
{
    public static IReadOnlyList<NavDestination> Primary { get; } =
    [
        new("dashboard", "Dashboard", "portfolio"),
        new("crypto", "Crypto", "scanner"),
        new("tradfi", "TradFi", "tradfi"),
        new("forex", "Forex", "forex"),
        new("backtest", "Backtest", "backtest"),
        new("bots", "Bots", "bot"),
        new("logs", "Logs", "logs"),
        new("settings", "Settings", "settings"),
    ];

    public static IReadOnlyList<(string Id, string Label)> SettingsSubItems { get; } =
    [
        ("settings:notify", "↳ Notifications & Telegram"),
        ("settings:lanes", "↳ Desks, Schedule & Venue"),
        ("settings:keys", "↳ API Keys & Connection"),
        ("settings:appearance", "↳ Appearance & Layout"),
        ("settings:data", "↳ Data, Export & Privacy"),
        ("settings:about", "↳ System & About"),
    ];

    public static IReadOnlyList<NavDestination> More { get; } =
    [
        new("glossary", "Glossary", "glossary", true),
        new("export", "Export", "export", true),
        new("billing", "Billing", "billing", true),
        new("settings", "Settings", "settings", true),
        new("logs", "Logs", "logs", true),
        new("debug", "Debug", "debug", true),
        new("workbook", "Results Workbook", "workbook", true),
        new("sauce", "Sauce / Study", "sauce", true),
        new("wizards", "Wizards", "wizards", true),
        new("query", "Query bar (P1)", "query", true),
        new("palette", "Command palette (P1)", "palette", true),
        new("plugins", "Plugin hooks (P2)", "plugins", true),
        new("replay", "Replay scrubber (P2)", "replay", true),
        new("dial", "Job dial (P2)", "dial", true),
        new("themes", "Theme packs (P2)", "themes", true),
    ];

    public static string Title(string id) => id switch
    {
        "dashboard" => "Dashboard",
        "alerts" => "Alerts",
        "crypto" => "Crypto desk",
        "tradfi" => "TradFi desk",
        "forex" => "Forex desk",
        "backtest" => "Backtest",
        "bots" => "Bots hub",
        "settings" => "Settings (10 sections)",
        "workbook" => "Results Workbook",
        "sauce" => "Secret Sauce / Study",
        "poolwatch" => "Crypto · Pool watch",
        "dex" => "DEX pool watch",
        "wizards" => "Setup / Telegram / Alpaca / Calendar",
        "glossary" => "Glossary",
        "export" => "Export",
        "billing" => "Billing",
        "logs" => "Execution & Timing Logs",
        "debug" => "Debug",
        "query" => "Query bar (P1)",
        "palette" => "Command palette (P1)",
        "plugins" => "Plugin UI hooks (P2)",
        "replay" => "Replay scrubber (P2)",
        "dial" => "Hardware job dial (P2)",
        "themes" => "Theme + density packs (P2)",
        _ => id,
    };

    public static string Body(string id) => id switch
    {
        "workbook" or "crypto" or "tradfi" or "forex" or "backtest" => "",
        "sauce" => "Sauce Lab / Study entry — jobs stay in Python engine.",
        "poolwatch" => "Research only — Uniswap v3 / Base DEX liquidity pools. DEX liquidity can vanish.",
        "dex" => "Uniswap/Base pool watch surface (disclaimer + rows from engine).",
        "wizards" => "Setup, Telegram, Alpaca, Calendar wizards — CredMan targets frozen; write UI AV-P1h.",
        "settings" => "connection, appearance, keys, venue, lanes, dashboard, privacy, data, notify, about.",
        "bots" => "Status + Plan builder + performance (host poll via engine/botd).",
        "dashboard" => "Portfolio module catalog + Sync/Customize/Export — live widgets still PySide.",
        "alerts" => "Logs / Entered / Left / Trades; Telegram remains engine channel.",
        "logs" => "Execution timing breakdown for scans, backtests, benchmarks, and startup.",
        "query" => "P1: expression filters over results.db.",
        "palette" => "P1: Ctrl+K command palette.",
        "plugins" => "P2: trusted C# view modules only.",
        "replay" => "P2: timeline over stored runs.",
        "dial" => "P2: worker caps without catalog cull.",
        "themes" => "P2: compact/comfortable + light/dark.",
        _ => "P0 parity surface — see docs/PRODUCT_SURFACE_INVENTORY.md §12.",
    };

    public static bool ShowsWorkbook(string id) =>
        id is "workbook" or "crypto" or "tradfi" or "forex" or "sauce";

    public static bool ShowsDeskStrip(string id) =>
        id is "crypto" or "tradfi" or "forex";

    public static bool ShowsPoolWatch(string id) => id == "crypto";
}
