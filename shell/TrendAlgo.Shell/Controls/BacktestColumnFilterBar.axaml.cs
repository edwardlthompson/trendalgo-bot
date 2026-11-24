using Avalonia.Controls;

namespace TrendAlgo.Shell.Controls;

public partial class BacktestColumnFilterBar : UserControl
{
    public BacktestColumnFilterBar()
    {
        InitializeComponent();
    }

    /// <summary>Lock each filter slot to the matching Results DataGrid column width.</summary>
    public void SyncToColumns(DataGrid grid)
    {
        if (grid.Columns.Count == 0)
            return;
        var slots = new Control?[]
        {
            SlotIndicator, SlotTimeframe, SlotParams, SlotNet, SlotFees, SlotOpen, SlotWins,
            SlotLosses, SlotWinPct, SlotTsl, SlotTslHits, SlotTslHitPct, SlotStrength, SlotEvents,
            SlotBot,
        };
        var n = Math.Min(slots.Length, grid.Columns.Count);
        for (var i = 0; i < n; i++)
        {
            if (slots[i] is not Control slot)
                continue;
            var px = grid.Columns[i].ActualWidth;
            if (px <= 1)
                px = grid.Columns[i].Width.IsAbsolute ? grid.Columns[i].Width.Value : slot.Width;
            if (px > 1 && Math.Abs(slot.Width - px) > 0.5)
                slot.Width = px;
        }
    }
}
