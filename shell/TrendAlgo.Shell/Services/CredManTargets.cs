namespace TrendAlgo.Shell.Services;

/// <summary>Frozen Windows CredMan TargetNames — must match Python vault modules.</summary>
public static class CredManTargets
{
    public const string TelegramToken = "TrendAlgo/telegram-bot-token";
    public const string TelegramChat = "TrendAlgo/telegram-chat-id";
    public const string AlpacaKey = "TrendAlgo/alpaca-key-id";
    public const string AlpacaSecret = "TrendAlgo/alpaca-secret";
    public const string CalendarCmc = "TrendAlgo/calendar-coinmarketcal";
    public const string CalendarCoindar = "TrendAlgo/calendar-coindar";
    public const string OwnerSecret = "TrendAlgo/owner-secret";
    public const string OwnerBearer = "TrendAlgo/owner-bearer";
    public const string PracticeSecret = "TrendAlgo/practice-secret";
    public const string ExchangePrefix = "TrendAlgo/exchange/";

    public const string AlgoSpecialNote =
        "AlgoSpecial Forex H1 is keyless (public feed); no CredMan migrate.";

    public static IReadOnlyList<(string Kind, string Target)> CoreTargets { get; } =
    [
        ("telegram:token", TelegramToken),
        ("telegram:chat", TelegramChat),
        ("alpaca:key", AlpacaKey),
        ("alpaca:secret", AlpacaSecret),
        ("calendar:cmc", CalendarCmc),
        ("calendar:coindar", CalendarCoindar),
        ("owner:secret", OwnerSecret),
        ("owner:bearer", OwnerBearer),
        ("owner:practice", PracticeSecret),
    ];

    public static string ExchangeTarget(string exchangeId, string which) =>
        $"{ExchangePrefix}{exchangeId}/{which}";
}
