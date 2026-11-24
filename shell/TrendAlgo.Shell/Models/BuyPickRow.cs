namespace TrendAlgo.Shell.Models;

/// <summary>Market Context row — 9 columns match BuyPicksPane headers.</summary>
public sealed class BuyPickRow
{
    public string Pair { get; init; } = "";
    public string Signal { get; init; } = "Neutral";
    public double Score { get; init; }
    public double Confidence { get; init; }
    public string? NearestSr { get; init; }
    public double? RrR1 { get; init; }
    public int Confluence { get; init; }
    public string? Regime { get; init; }
    public double? BotBestNet { get; init; }
    public string? BotBestLabel { get; init; }

    public string ConfidenceText => ((int)Confidence).ToString();
    public string ScoreText => Score.ToString("0.00");
    public string NearestSrText => string.IsNullOrWhiteSpace(NearestSr) ? "—" : NearestSr;
    public string RrText => RrR1 is { } rr ? rr.ToString("0.00") : "—";
    public string LevelsText => Confluence.ToString();
    public string TaText
    {
        get
        {
            if (BotBestNet is not { } best)
                return "—";
            var ta = $"+{best:0.0}%";
            return string.IsNullOrWhiteSpace(BotBestLabel) ? ta : $"{ta} ({BotBestLabel})";
        }
    }
}
