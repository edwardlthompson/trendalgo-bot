namespace TrendAlgo.Shell.Models;

public sealed class DashboardModuleRow
{
    public string Id { get; init; } = "";
    public string Title { get; init; } = "";
    public string Category { get; init; } = "";
    public string Span { get; init; } = "";
    public string Value { get; init; } = "";
    public string Detail { get; init; } = "";
    public double PixelLeft { get; init; }
    public double PixelTop { get; init; }
    public double PixelWidth { get; init; } = 120;
    public double PixelHeight { get; init; } = 80;
}
