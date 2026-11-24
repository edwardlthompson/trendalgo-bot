using System.Text.Json;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Styling;

namespace TrendAlgo.Shell.Services;

/// <summary>Apply settings.json theme/accent to Avalonia Fluent (PySide apply_theme parity).</summary>
public static class ShellTheme
{
    public static readonly string[] ThemeChoices = ["system", "light", "dark"];
    public static readonly string[] AccentPresets =
    [
        "", "#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed",
    ];

    public static (string Theme, string Accent) LoadFromSettings()
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, "settings.json");
        if (!File.Exists(path))
            return ("system", "");
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            var theme = doc.RootElement.TryGetProperty("theme", out var t)
                ? t.GetString() ?? "system"
                : "system";
            var accent = doc.RootElement.TryGetProperty("accent", out var a)
                ? a.GetString() ?? ""
                : "";
            if (!ThemeChoices.Contains(theme))
                theme = "system";
            if (!AccentPresets.Contains(accent, StringComparer.OrdinalIgnoreCase))
                accent = "";
            return (theme, accent);
        }
        catch
        {
            return ("system", "");
        }
    }

    public static void Apply(string theme, string accent)
    {
        if (Application.Current is not { } app)
            return;
        app.RequestedThemeVariant = theme switch
        {
            "light" => ThemeVariant.Light,
            "dark" => ThemeVariant.Dark,
            _ => ThemeVariant.Default,
        };

        var resources = app.Resources;
        if (string.IsNullOrWhiteSpace(accent) || !Color.TryParse(accent, out var color))
        {
            resources.Remove("ShellAccentBrush");
            return;
        }
        resources["ShellAccentBrush"] = new SolidColorBrush(color);
        // Fluent SystemAccentColor* keys when present
        resources["SystemAccentColor"] = color;
        resources["SystemAccentColorDark1"] = color;
        resources["SystemAccentColorLight1"] = color;
    }

    public static void ApplyFromSettings()
    {
        var (theme, accent) = LoadFromSettings();
        Apply(theme, accent);
    }

    public static void Persist(string theme, string accent)
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, "settings.json");
        JsonObjectMerge(path, theme, accent);
        Apply(theme, accent);
    }

    private static void JsonObjectMerge(string path, string theme, string accent)
    {
        Dictionary<string, JsonElement> map = new();
        if (File.Exists(path))
        {
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                foreach (var p in doc.RootElement.EnumerateObject())
                    map[p.Name] = p.Value.Clone();
            }
            catch
            {
                map.Clear();
            }
        }
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions { Indented = true }))
        {
            writer.WriteStartObject();
            foreach (var (k, v) in map)
            {
                if (k is "theme" or "accent")
                    continue;
                writer.WritePropertyName(k);
                v.WriteTo(writer);
            }
            writer.WriteString("theme", theme);
            writer.WriteString("accent", accent);
            writer.WriteEndObject();
        }
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);
        File.WriteAllBytes(path, stream.ToArray());
    }
}
