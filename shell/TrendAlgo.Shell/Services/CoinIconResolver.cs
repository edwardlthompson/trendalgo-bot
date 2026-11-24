using Avalonia.Media.Imaging;

namespace TrendAlgo.Shell.Services;

/// <summary>Resolve local coin/equity/FX logos (same folders as PySide coin_icons).</summary>
public static class CoinIconResolver
{
    private static readonly string[] Suffixes = [".png", ".PNG", ".jpg", ".jpeg", ".JPG", ".JPEG"];
    private static readonly Dictionary<string, Bitmap?> Cache = new(StringComparer.OrdinalIgnoreCase);
    private static readonly Dictionary<string, string?> PathCache = new(StringComparer.OrdinalIgnoreCase);

    // Mirrors src/trendalgo/icons/aliases.py (Kraken tickers -> icon file names).
    private static readonly Dictionary<string, string> Aliases = new(StringComparer.OrdinalIgnoreCase)
    {
        ["XBT"] = "BTC", ["XXBT"] = "BTC", ["XETH"] = "ETH", ["XXDG"] = "DOGE", ["XDG"] = "DOGE",
        ["XLTC"] = "LTC", ["XXRP"] = "XRP", ["XXLM"] = "XLM", ["XZEC"] = "ZEC", ["XXMR"] = "XMR",
        ["REPV2"] = "REP", ["TBTC"] = "BTC", ["WBTC"] = "BTC", ["MSOL"] = "SOL", ["BIT"] = "BTC",
        ["POL"] = "MATIC", ["LUNA2"] = "LUNA", ["WAXL"] = "AXL", ["LIGHTER"] = "LIT",
    };

    public static Bitmap? Load(string symbolOrPair, string? lane = null)
    {
        var path = ResolvePath(symbolOrPair, lane);
        if (path is null)
            return null;
        lock (Cache)
        {
            if (Cache.TryGetValue(path, out var hit))
                return hit;
            try
            {
                var bmp = new Bitmap(path);
                Cache[path] = bmp;
                return bmp;
            }
            catch
            {
                Cache[path] = null;
                return null;
            }
        }
    }

    public static string? ResolvePath(string symbolOrPair, string? lane = null)
    {
        var key = $"{lane ?? ""}|{symbolOrPair}";
        lock (PathCache)
        {
            if (PathCache.TryGetValue(key, out var cached))
                return cached;
        }
        var found = ResolvePathUncached(symbolOrPair, lane);
        lock (PathCache)
        {
            PathCache[key] = found;
        }
        return found;
    }

    private static string? ResolvePathUncached(string symbolOrPair, string? lane = null)
    {
        var baseSym = BaseSymbol(symbolOrPair);
        if (!string.IsNullOrEmpty(baseSym)
            && string.Equals(lane, "tradfi", StringComparison.OrdinalIgnoreCase))
        {
            var equity = Path.Combine(ProfilePaths.DeviceRoot, "icon_cache", $"eq_{baseSym}.png");
            if (File.Exists(equity))
                return equity;
        }

        foreach (var name in NamesFor(symbolOrPair, lane))
        {
            foreach (var dir in IconDirs())
            {
                foreach (var suffix in Suffixes)
                {
                    var candidate = Path.Combine(dir, name + suffix);
                    if (File.Exists(candidate))
                        return candidate;
                }
            }
        }
        return null;
    }

    public static string LogoGlyph(string symbolOrPair)
    {
        var baseSym = BaseSymbol(symbolOrPair);
        if (string.IsNullOrEmpty(baseSym))
            return "·";
        return baseSym.Length <= 4 ? baseSym : baseSym[..4];
    }

    private static IEnumerable<string> NamesFor(string symbolOrPair, string? lane)
    {
        var baseSym = BaseSymbol(symbolOrPair);
        if (string.IsNullOrEmpty(baseSym))
            yield break;
        yield return baseSym;
        if (Aliases.TryGetValue(baseSym, out var alias) && alias != baseSym)
            yield return alias;
        if (string.Equals(lane, "forex", StringComparison.OrdinalIgnoreCase)
            || string.Equals(lane, "tradfi", StringComparison.OrdinalIgnoreCase))
        {
            var compact = symbolOrPair.Replace("/", "", StringComparison.Ordinal).ToUpperInvariant();
            if (!string.IsNullOrEmpty(compact) && compact != baseSym)
                yield return compact;
        }
    }

    private static string BaseSymbol(string symbolOrPair)
    {
        var raw = (symbolOrPair ?? "").Trim().ToUpperInvariant();
        if (string.IsNullOrEmpty(raw))
            return "";
        return raw.Split('/')[0];
    }

    private static IEnumerable<string> IconDirs()
    {
        var env = Environment.GetEnvironmentVariable("TRENDALGO_COIN_ICONS");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            yield return env;

        var root = FindRepoRoot();
        foreach (var rel in new[]
                 {
                     Path.Combine("branding", "assets", "coins"),
                     Path.Combine("branding", "assets", "coins", "from-retired-web-backup"),
                     Path.Combine("branding", "assets", "currencies"),
                     Path.Combine("examples", "web", "public", "icons", "coins"),
                 })
        {
            var full = Path.Combine(root, rel);
            if (Directory.Exists(full))
                yield return full;
        }

        var deviceIcons = Path.Combine(ProfilePaths.DeviceRoot, "icons", "coins");
        if (Directory.Exists(deviceIcons))
            yield return deviceIcons;
    }

    private static string FindRepoRoot()
    {
        var env = Environment.GetEnvironmentVariable("TRENDALGO_ROOT");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            return env;
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "pyproject.toml"))
                && Directory.Exists(Path.Combine(dir.FullName, "shell")))
                return dir.FullName;
            dir = dir.Parent;
        }
        return Directory.GetCurrentDirectory();
    }
}
