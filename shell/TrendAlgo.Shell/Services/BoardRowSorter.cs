using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

public static class BoardRowSorter
{
    public static IReadOnlyList<OpportunityBoardRow> Sort(
        IEnumerable<OpportunityBoardRow> rows,
        string? columnKey,
        bool ascending)
    {
        if (string.IsNullOrWhiteSpace(columnKey))
            return rows.ToList();

        var key = columnKey.Trim();
        IOrderedEnumerable<OpportunityBoardRow> ordered = key switch
        {
            "Watch" => Order(rows, r => r.Watch, ascending),
            "Logo" => Order(rows, r => r.Logo, ascending),
            "Name" => Order(rows, r => r.Name, ascending),
            "Gain7d" => Order(rows, r => r.Gain7d, ascending),
            "ChartDist7dPct" => Order(rows, r => r.ChartDist7dPct ?? double.MaxValue, ascending),
            "Gain30d" => Order(rows, r => r.Gain30d, ascending),
            "ChartDist30dPct" => Order(rows, r => r.ChartDist30dPct ?? double.MaxValue, ascending),
            "BestBtPct" => Order(rows, r => r.BestBtPct, ascending),
            "BotBestLabel" => Order(rows, r => r.BotBestLabel, ascending),
            "BotVsBhPct" => Order(rows, r => r.BotVsBhPct ?? double.MinValue, ascending),
            "HealthScore" => Order(rows, r => r.HealthScore ?? double.MinValue, ascending),
            "Hv7d" => Order(rows, r => r.Hv7d, ascending),
            "MaxDd" => Order(rows, r => r.MaxDd, ascending),
            "VolDelta" => Order(rows, r => r.VolDelta, ascending),
            "Exchange" => Order(rows, r => r.Exchange, ascending),
            "Volume24h" => Order(rows, r => r.Volume24h, ascending),
            "Events" => Order(rows, r => r.Events, ascending),
            _ => Order(rows, r => r.Name, ascending),
        };
        return ordered.ToList();
    }

    private static IOrderedEnumerable<OpportunityBoardRow> Order<T>(
        IEnumerable<OpportunityBoardRow> rows,
        Func<OpportunityBoardRow, T> selector,
        bool ascending)
        where T : IComparable<T> =>
        ascending ? rows.OrderBy(selector) : rows.OrderByDescending(selector);
}
