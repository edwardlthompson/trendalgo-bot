using Avalonia.Controls;

namespace TrendAlgo.Shell.Controls;

public partial class BoardColumnFilterBar : UserControl
{
    public BoardColumnFilterBar()
    {
        InitializeComponent();
    }

    /// <summary>Lock each filter slot to the matching board DataGrid column width.</summary>
    public void SyncToColumns(DataGrid grid)
    {
        if (grid.Columns.Count == 0)
            return;
        // Column order must match MainWindow BoardDataGrid.
        var slots = new Control?[]
        {
            SlotLogo, SlotName, SlotGain7, SlotSpark7, SlotGain30, SlotSpark30,
            SlotBestBt, SlotBestTa, SlotBotVsBh, SlotHealth, SlotHv, SlotMaxDd, SlotVolDelta,
            SlotExchange, SlotVol24, SlotEvents,
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
