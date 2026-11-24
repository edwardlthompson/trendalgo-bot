using Avalonia.Controls;
using Avalonia.Platform.Storage;

namespace TrendAlgo.Shell.Services;

/// <summary>Save-file picker for Share PNG (parity with PySide QFileDialog.getSaveFileName).</summary>
public static class SharePngPicker
{
    public static async Task<string?> PickAsync(TopLevel top, string suggestedFileName)
    {
        var safe = string.IsNullOrWhiteSpace(suggestedFileName) ? "export.png" : suggestedFileName;
        if (!safe.EndsWith(".png", StringComparison.OrdinalIgnoreCase))
            safe += ".png";

        var file = await top.StorageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = "Share PNG",
            SuggestedFileName = safe,
            DefaultExtension = "png",
            FileTypeChoices =
            [
                new FilePickerFileType("PNG image") { Patterns = ["*.png"] },
            ],
        });
        return file?.TryGetLocalPath();
    }

    public static async Task<string?> PickFromMainAsync(string suggestedFileName)
    {
        if (Avalonia.Application.Current?.ApplicationLifetime is not
            Avalonia.Controls.ApplicationLifetimes.IClassicDesktopStyleApplicationLifetime
            {
                MainWindow: { } win
            })
            return null;
        return await PickAsync(win, suggestedFileName);
    }
}
