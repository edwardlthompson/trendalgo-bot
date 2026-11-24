using System.ComponentModel;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Threading;
using Avalonia.VisualTree;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.ViewModels;

namespace TrendAlgo.Shell.Views;

public partial class MainWindow : Window
{
    private ShellTray? _tray;
    private bool _syncingNav;
    private MainViewModel? _boundVm;
    private string? _lastSortKey;
    private bool _restoringSort;
    private bool _updatingOverflow;
    private readonly Dictionary<Control, double> _stripWidths = new();

    public MainWindow()
    {
        InitializeComponent();
        Opened += OnOpenedRestoreGeometry;
        Closing += OnClosingSaveGeometry;
        Loaded += (_, _) => SyncNavHighlight();
        DataContextChanged += OnDataContextChanged;
        BoardDataGrid.AddHandler(PointerPressedEvent, OnBoardGridPointerPressed, RoutingStrategies.Tunnel, handledEventsToo: true);
    }

    public void SetTray(ShellTray tray) => _tray = tray;

    private void OnDataContextChanged(object? sender, EventArgs e)
    {
        if (_boundVm is not null)
        {
            _boundVm.PropertyChanged -= OnVmPropertyChanged;
            _boundVm.BoardReloaded -= OnVmBoardReloaded;
        }
        _boundVm = DataContext as MainViewModel;
        if (_boundVm is not null)
        {
            _boundVm.PropertyChanged += OnVmPropertyChanged;
            _boundVm.BoardReloaded += OnVmBoardReloaded;
        }
        SyncNavHighlight();
    }

    private void OnVmBoardReloaded() =>
        Dispatcher.UIThread.Post(RestoreBoardSort, DispatcherPriority.Background);

    private void OnVmPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName is nameof(MainViewModel.SelectedNavId)
            or nameof(MainViewModel.BoardTab)
            or nameof(MainViewModel.SettingsSection)
            or null)
            SyncNavHighlight();
    }

    private void SyncNavHighlight()
    {
        if (DataContext is not MainViewModel vm)
            return;
        _syncingNav = true;
        try
        {
            var id = vm.SelectedNavId;
            if (id == "poolwatch")
            {
                var pw = vm.PrimaryNav.FirstOrDefault(n => n.Id == "crypto:poolwatch");
                PrimaryList.SelectedItem = pw is { IsVisible: true } ? pw : null;
                return;
            }
            if (id is "crypto" or "tradfi" or "forex")
            {
                var sub = vm.PrimaryNav.FirstOrDefault(n => n.Id == $"{id}:{vm.BoardTab}");
                PrimaryList.SelectedItem = sub is { IsVisible: true } ? sub : null;
                return;
            }
            if (id is "settings" or "billing" or "glossary" or "debug")
            {
                var sec = id == "settings" ? vm.SettingsSection : id;
                var sub = vm.PrimaryNav.FirstOrDefault(n => n.Id == $"settings:{sec}");
                if (sub is { IsVisible: true })
                {
                    PrimaryList.SelectedItem = sub;
                    return;
                }
                PrimaryList.SelectedItem = vm.PrimaryNav.FirstOrDefault(n => n.Id == "settings");
                return;
            }
            PrimaryList.SelectedItem = vm.PrimaryNav.FirstOrDefault(n => n.Id == id);
        }
        finally
        {
            _syncingNav = false;
        }
    }

    private void OnOpenedRestoreGeometry(object? sender, EventArgs e)
    {
        var geo = WindowGeometryStore.Load();
        if (geo is null)
            return;
        if (geo.Width >= MinWidth && geo.Height >= MinHeight)
        {
            Width = geo.Width;
            Height = geo.Height;
        }
        if (!double.IsNaN(geo.X) && !double.IsNaN(geo.Y))
            Position = new PixelPoint((int)geo.X, (int)geo.Y);
        if (Enum.TryParse<WindowState>(geo.State, out var state) && state != WindowState.Minimized)
            WindowState = state;
        SyncNavHighlight();
    }

    private void OnClosingSaveGeometry(object? sender, WindowClosingEventArgs e)
    {
        var bounds = Bounds;
        WindowGeometryStore.Save(new WindowGeometryStore.Geometry(
            Position.X,
            Position.Y,
            bounds.Width > 0 ? bounds.Width : Width,
            bounds.Height > 0 ? bounds.Height : Height,
            WindowState.ToString()));

        if (_tray is { CloseToTray: true })
        {
            e.Cancel = true;
            Hide();
            _tray.ShowHiddenMessage();
        }
    }

    private void OnNavSelectionChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (_syncingNav)
            return;
        if (DataContext is not MainViewModel vm)
            return;
        if (sender is not ListBox list || list.SelectedItem is not NavDestination dest)
            return;
        var targetId = dest.Id;
        Dispatcher.UIThread.Post(() =>
        {
            var isSameSub = targetId == $"{vm.SelectedNavId}:{vm.BoardTab}"
                || (targetId == "crypto:poolwatch" && vm.SelectedNavId == "poolwatch")
                || (targetId == $"settings:{vm.SettingsSection}" && vm.SelectedNavId == "settings")
                || (targetId.StartsWith("settings:", StringComparison.Ordinal)
                    && targetId["settings:".Length..] == vm.SelectedNavId);
            if (!isSameSub)
                vm.NavigateCommand.Execute(targetId);
        });
    }

    private void OnBuyPicksGridLoaded(object? sender, RoutedEventArgs e)
    {
        if (sender is not DataGrid grid)
            return;
        foreach (var col in grid.Columns)
        {
            var title = col.Header?.ToString() ?? "";
            if (col.Header is TextBlock existing)
            {
                existing.TextWrapping = Avalonia.Media.TextWrapping.NoWrap;
                existing.TextTrimming = Avalonia.Media.TextTrimming.CharacterEllipsis;
                continue;
            }
            col.Header = new TextBlock
            {
                Text = title,
                TextWrapping = Avalonia.Media.TextWrapping.NoWrap,
                TextTrimming = Avalonia.Media.TextTrimming.CharacterEllipsis,
            };
        }
    }

    private void OnDeskStripSizeChanged(object? sender, SizeChangedEventArgs e) =>
        UpdateDeskStripOverflow();

    private void UpdateDeskStripOverflow()
    {
        if (_updatingOverflow || DeskStripPanel is null)
            return;
        var available = DeskStripPanel.Bounds.Width;
        if (available <= 1)
            return;
        _updatingOverflow = true;
        try
        {
            double WidthOf(Control c, double fallback)
            {
                if (c.Bounds.Width > 1)
                    _stripWidths[c] = c.Bounds.Width + 6;
                return _stripWidths.TryGetValue(c, out var w) ? w : fallback;
            }

            var fixedW = WidthOf(DeskRunBtn, 86)
                + (DeskForceBtn.IsVisible ? WidthOf(DeskForceBtn, 165) : 0)
                + WidthOf(DeskLoadText, 95);
            var pairs = new (Button Btn, MenuItem Item, double Fallback)[]
            {
                (DeskCancelBtn, MoreCancelItem, 68),
                (DeskProgressBtn, MoreProgressItem, 78),
                (DeskReloadBtn, MoreReloadItem, 68),
                (DeskShareBtn, MoreShareItem, 88),
                (DeskSauceBtn, MoreSauceItem, 128),
                (DeskSettingsBtn, MoreSettingsItem, 76),
            };
            var total = fixedW + pairs.Sum(p => WidthOf(p.Btn, p.Fallback));
            if (total <= available)
            {
                foreach (var (btn, item, _) in pairs)
                {
                    btn.IsVisible = true;
                    item.IsVisible = false;
                }
                DeskMoreBtn.IsVisible = false;
                return;
            }
            var used = fixedW + 76; // reserve width for "More ▾"
            var overflow = false;
            foreach (var (btn, item, fb) in pairs)
            {
                var w = WidthOf(btn, fb);
                var fits = !overflow && used + w <= available;
                btn.IsVisible = fits;
                item.IsVisible = !fits;
                if (fits)
                    used += w;
                else
                    overflow = true;
            }
            DeskMoreBtn.IsVisible = overflow;
        }
        finally
        {
            _updatingOverflow = false;
        }
    }

    private void OnBoardContextMenuOpening(object? sender, CancelEventArgs e)
    {
        var watched = (BoardDataGrid.SelectedItem as OpportunityBoardRow)?.Watch == true;
        CtxWatchlistItem.Icon = watched
            ? new TextBlock { Text = "✓", FontWeight = Avalonia.Media.FontWeight.Bold }
            : null;
    }

    private void OnBoardGridPointerPressed(object? sender, PointerPressedEventArgs e)
    {
        if (!e.GetCurrentPoint(BoardDataGrid).Properties.IsRightButtonPressed)
            return;
        for (var v = e.Source as Visual; v is not null && !ReferenceEquals(v, BoardDataGrid); v = v.GetVisualParent())
        {
            if (v.DataContext is OpportunityBoardRow row)
            {
                BoardDataGrid.SelectedItem = row;
                CtxWatchlistItem.Icon = row.Watch
                    ? new TextBlock { Text = "✓", FontWeight = Avalonia.Media.FontWeight.Bold }
                    : null;
                break;
            }
        }
    }

    private void OnCellActionPointerPressed(object? sender, PointerPressedEventArgs e)
    {
        if (!e.GetCurrentPoint(sender as Visual).Properties.IsLeftButtonPressed)
            return;
        if (sender is Control { Tag: OpportunityBoardRow row } ctrl)
        {
            BoardDataGrid.SelectedItem = row;
            e.Pointer.Capture(ctrl);
            e.Handled = true;
        }
    }

    private void OnWatchStarPointerReleased(object? sender, PointerReleasedEventArgs e)
    {
        if (sender is Control ctrl && Equals(e.Pointer.Captured, ctrl))
            e.Pointer.Capture(null);
        if (e.InitialPressMouseButton != MouseButton.Left)
            return;
        if (sender is Control c && !new Rect(c.Bounds.Size).Contains(e.GetPosition(c)))
            return;
        if (DataContext is MainViewModel vm && (sender as Control)?.Tag is OpportunityBoardRow row)
        {
            Dispatcher.UIThread.Post(() => vm.ToggleWatchForRowCommand.Execute(row));
            e.Handled = true;
        }
    }

    private void OnBestTaPointerReleased(object? sender, PointerReleasedEventArgs e)
    {
        if (sender is Control ctrl && Equals(e.Pointer.Captured, ctrl))
            e.Pointer.Capture(null);
        if (e.InitialPressMouseButton != MouseButton.Left)
            return;
        if (sender is Control c && !new Rect(c.Bounds.Size).Contains(e.GetPosition(c)))
            return;
        if (DataContext is MainViewModel vm && (sender as Control)?.Tag is OpportunityBoardRow row)
        {
            Dispatcher.UIThread.Post(() => vm.RequestBoardResults(row));
            e.Handled = true;
        }
    }

    private void OnEventsPointerReleased(object? sender, PointerReleasedEventArgs e)
    {
        if (sender is Control ctrl && Equals(e.Pointer.Captured, ctrl))
            e.Pointer.Capture(null);
        if (e.InitialPressMouseButton != MouseButton.Left)
            return;
        if (sender is Control c && !new Rect(c.Bounds.Size).Contains(e.GetPosition(c)))
            return;
        if (DataContext is MainViewModel vm && (sender as Control)?.Tag is OpportunityBoardRow row)
        {
            Dispatcher.UIThread.Post(() => vm.RequestBoardEvents(row));
            e.Handled = true;
        }
    }

    private void OnBacktestCreateBotClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is MainViewModel vm && (sender as Control)?.Tag is StrategyRow row)
            vm.BacktestCreateBotForRowCommand.Execute(row);
    }

    private void OnBotResumeClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is MainViewModel vm && (sender as Control)?.Tag is BotPlanRow row)
            vm.BotsResumeCommand.Execute(row);
    }

    private void OnBotPauseClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is MainViewModel vm && (sender as Control)?.Tag is BotPlanRow row)
            vm.BotsPauseCommand.Execute(row);
    }

    private void OnBoardDataGridLoaded(object? sender, RoutedEventArgs e)
    {
        if (sender is not DataGrid grid)
            return;
        if (grid.Tag as string != "lts-tips")
        {
            var n = Math.Min(grid.Columns.Count, LtsBoardHeaders.Tips.Length);
            for (var i = 0; i < n; i++)
            {
                var title = i < LtsBoardHeaders.Titles.Length
                    ? LtsBoardHeaders.Titles[i]
                    : grid.Columns[i].Header?.ToString() ?? "";
                var header = new TextBlock
                {
                    Text = title,
                    TextWrapping = Avalonia.Media.TextWrapping.NoWrap,
                    TextTrimming = Avalonia.Media.TextTrimming.CharacterEllipsis,
                };
                ToolTip.SetTip(header, LtsBoardHeaders.Tips[i]);
                grid.Columns[i].Header = header;
            }
            grid.Tag = "lts-tips";
        }

        SyncBoardFilterWidths();
        grid.LayoutUpdated += OnBoardGridLayoutUpdated;
        Dispatcher.UIThread.Post(RestoreBoardSort, DispatcherPriority.Background);
    }

    private void OnBoardGridLayoutUpdated(object? sender, EventArgs e) => SyncBoardFilterWidths();

    private void OnBoardSorting(object? sender, DataGridColumnEventArgs e)
    {
        if (_restoringSort || DataContext is not MainViewModel)
            return;
        var col = e.Column;
        Dispatcher.UIThread.Post(() =>
        {
            if (_restoringSort || DataContext is not MainViewModel mvm)
                return;
            var desc = BoardDataGrid.CollectionView?.SortDescriptions.FirstOrDefault();
            var key = desc?.PropertyPath;
            if (string.IsNullOrWhiteSpace(key))
                key = ColumnKey(col);
            if (string.IsNullOrWhiteSpace(key))
                return;
            var asc = desc is null || desc.Direction == ListSortDirection.Ascending;
            _lastSortKey = key;
            mvm.SaveBoardSort(key, asc);
        }, DispatcherPriority.Background);
    }

    private void RestoreBoardSort()
    {
        if (BoardDataGrid is null || DataContext is not MainViewModel vm)
            return;
        var key = vm.BoardSortKey;
        if (string.IsNullOrWhiteSpace(key))
            return;
        _lastSortKey = key;
        DataGridColumn? match = null;
        foreach (var col in BoardDataGrid.Columns)
        {
            if (ColumnKey(col) == key)
            {
                match = col;
                break;
            }
        }
        if (match is null)
            return;
        _restoringSort = true;
        try
        {
            match.Sort(vm.BoardSortAscending
                ? ListSortDirection.Ascending
                : ListSortDirection.Descending);
        }
        catch
        {
            /* sort chrome optional */
        }
        finally
        {
            _restoringSort = false;
        }
    }

    private void SyncBoardFilterWidths()
    {
        if (BoardFiltersBar is null || BoardDataGrid is null)
            return;
        BoardFiltersBar.SyncToColumns(BoardDataGrid);
    }

    private static string? ColumnKey(DataGridColumn col)
    {
        if (!string.IsNullOrWhiteSpace(col.SortMemberPath))
            return col.SortMemberPath;
        return col.Header switch
        {
            TextBlock tb => tb.Text,
            string s => s,
            _ => col.Header?.ToString(),
        };
    }
}
