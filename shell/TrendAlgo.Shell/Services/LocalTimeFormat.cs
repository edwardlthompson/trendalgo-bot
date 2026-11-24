using System.Globalization;

namespace TrendAlgo.Shell.Services;

/// <summary>Formats UTC/ISO/Unix timestamps into the user's computer local time zone.</summary>
public static class LocalTimeFormat
{
    public static bool TryParseToLocal(string? raw, out DateTimeOffset local)
    {
        local = default;
        if (string.IsNullOrWhiteSpace(raw))
            return false;
        var text = raw.Trim();
        if (long.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out var unix)
            && unix > 946_684_800) // >= 2000-01-01
        {
            local = DateTimeOffset.FromUnixTimeSeconds(unix).ToLocalTime();
            return true;
        }
        if (DateTimeOffset.TryParse(
                text,
                CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeLocal | DateTimeStyles.AllowWhiteSpaces,
                out var dto))
        {
            local = dto.ToLocalTime();
            return true;
        }
        return false;
    }

    public static string FormatTimestamp(string? raw) =>
        TryParseToLocal(raw, out var local)
            ? local.ToString("yyyy-MM-dd h:mm:ss tt", CultureInfo.InvariantCulture)
            : raw ?? "";

    public static string FormatFromUnixSeconds(long unixSeconds) =>
        DateTimeOffset.FromUnixTimeSeconds(unixSeconds)
            .ToLocalTime()
            .ToString("yyyy-MM-dd h:mm:ss tt", CultureInfo.InvariantCulture);

    public static string FormatLastScan(DateTimeOffset? timestamp)
    {
        if (timestamp is null)
            return "Last scan: Never";
        var local = timestamp.Value.ToLocalTime();
        var age = DateTimeOffset.Now - local;
        string rel;
        if (age < TimeSpan.Zero || age.TotalMinutes < 1)
            rel = "just now";
        else if (age.TotalMinutes < 60)
            rel = $"{(int)age.TotalMinutes}m ago";
        else if (age.TotalHours < 24)
            rel = $"{(int)age.TotalHours}h {age.Minutes}m ago";
        else
            rel = $"{(int)age.TotalDays}d ago";
        var stamp = local.ToString("yyyy-MM-dd h:mm tt", CultureInfo.InvariantCulture);
        return $"Last scan: {stamp} ({rel})";
    }

    public static string SortKeyUtc(string? raw, long? unixSeconds = null)
    {
        if (unixSeconds is > 946_684_800)
            return DateTimeOffset.FromUnixTimeSeconds(unixSeconds.Value)
                .ToUniversalTime()
                .ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture);
        if (TryParseToLocal(raw, out var local))
            return local.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture);
        return raw ?? "";
    }
}
