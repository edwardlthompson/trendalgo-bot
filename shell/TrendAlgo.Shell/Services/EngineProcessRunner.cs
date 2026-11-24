using System.Diagnostics;

namespace TrendAlgo.Shell.Services;

/// <summary>
/// Centralized Python Research Engine subprocess factory (AUD-12 / ADR-0021).
/// Prefers bundled engine runtime beside the published shell, then repo .venv python, then uv run.
/// </summary>
public static class EngineProcessRunner
{
    public static ProcessStartInfo CreateResultsStorePsi(
        string? repoRoot = null,
        bool redirectOutput = true)
    {
        var workDir = repoRoot ?? FindRepoRoot();
        var (fileName, preArgs, pyPath) = ResolveEngineRuntime(workDir);
        var psi = new ProcessStartInfo
        {
            FileName = fileName,
            WorkingDirectory = workDir,
            RedirectStandardOutput = redirectOutput,
            RedirectStandardError = redirectOutput,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        if (!string.IsNullOrWhiteSpace(pyPath))
        {
            var existing = Environment.GetEnvironmentVariable("PYTHONPATH");
            psi.Environment["PYTHONPATH"] = string.IsNullOrWhiteSpace(existing)
                ? pyPath
                : $"{pyPath}{Path.PathSeparator}{existing}";
        }
        foreach (var arg in preArgs)
            psi.ArgumentList.Add(arg);
        psi.ArgumentList.Add("-m");
        psi.ArgumentList.Add("trendalgo.results_store");
        return psi;
    }

    public static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "pyproject.toml"))
                && Directory.Exists(Path.Combine(dir.FullName, "shell")))
                return dir.FullName;
            dir = dir.Parent;
        }
        var bundled = Path.Combine(AppContext.BaseDirectory, "engine");
        if (Directory.Exists(bundled))
            return AppContext.BaseDirectory;
        return Directory.GetCurrentDirectory();
    }

    private static (string FileName, string[] PreArgs, string? PythonPath) ResolveEngineRuntime(string repoRoot)
    {
        var envPy = Environment.GetEnvironmentVariable("TRENDALGO_ENGINE_PYTHON");
        if (!string.IsNullOrWhiteSpace(envPy) && File.Exists(envPy))
            return (envPy, Array.Empty<string>(), ResolveBundledPythonPath());

        // 1. Official bundled engine layout (dist/shell/<rid>/engine/)
        var engineDir = Path.Combine(AppContext.BaseDirectory, "engine");
        var bundledCandidates = new[]
        {
            Path.Combine(engineDir, "python", "python.exe"),
            Path.Combine(engineDir, "python", "bin", "python3"),
            Path.Combine(engineDir, "python.exe"),
            Path.Combine(engineDir, "bin", "python3"),
        };
        foreach (var candidate in bundledCandidates)
        {
            if (File.Exists(candidate))
                return (candidate, Array.Empty<string>(), engineDir);
        }

        // 2. Repo .venv interpreter (fast direct invoke, no uv lock check overhead)
        var venvCandidates = new[]
        {
            Path.Combine(repoRoot, ".venv", "Scripts", "python.exe"),
            Path.Combine(repoRoot, ".venv", "bin", "python"),
        };
        foreach (var candidate in venvCandidates)
        {
            if (File.Exists(candidate))
                return (candidate, Array.Empty<string>(), ResolveBundledPythonPath());
        }

        // 3. Developer uv fallback
        var uv = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".local", "bin", "uv.exe");
        var uvBin = File.Exists(uv) ? uv : "uv";
        return (uvBin, new[] { "run", "python" }, ResolveBundledPythonPath());
    }

    private static string? ResolveBundledPythonPath()
    {
        var engineDir = Path.Combine(AppContext.BaseDirectory, "engine");
        return Directory.Exists(Path.Combine(engineDir, "trendalgo")) ? engineDir : null;
    }
}
