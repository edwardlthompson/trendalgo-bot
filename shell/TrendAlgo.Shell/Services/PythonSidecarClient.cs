using System.Diagnostics;
using System.Text.Json;

namespace TrendAlgo.Shell.Services;

/// <summary>Persistent warm Python --sidecar NDJSON client with fail-soft fallback.</summary>
public sealed class PythonSidecarClient
{
    private static readonly Lazy<PythonSidecarClient> Shared = new(() => new PythonSidecarClient());
    public static PythonSidecarClient Instance => Shared.Value;

    private readonly SemaphoreSlim _gate = new(1, 1);
    private Process? _proc;
    private int _nextId;

    private PythonSidecarClient()
    {
        AppDomain.CurrentDomain.ProcessExit += (_, _) => DisposeProc();
    }

    public async Task<JsonDocument?> TryRequestAsync(
        string repoRoot,
        object payload,
        int timeoutMs = 45_000,
        CancellationToken ct = default)
    {
        if (Environment.GetEnvironmentVariable("TRENDALGO_DISABLE_SIDECAR") == "1")
            return null;
        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            var proc = EnsureProcess(repoRoot);
            if (proc is null)
                return null;
            var id = Interlocked.Increment(ref _nextId);
            var json = JsonSerializer.Serialize(payload);
            using var objDoc = JsonDocument.Parse(json);
            var line = InjectId(objDoc.RootElement, id);

            await proc.StandardInput.WriteLineAsync(line.AsMemory(), ct).ConfigureAwait(false);
            await proc.StandardInput.FlushAsync().ConfigureAwait(false);

            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(timeoutMs);
            var respLine = await proc.StandardOutput.ReadLineAsync(cts.Token).ConfigureAwait(false);
            if (string.IsNullOrWhiteSpace(respLine))
            {
                DisposeProc();
                return null;
            }
            using var respDoc = JsonDocument.Parse(respLine);
            var root = respDoc.RootElement;
            if (!root.TryGetProperty("ok", out var okEl) || okEl.ValueKind != JsonValueKind.True)
                return null;
            if (!root.TryGetProperty("data", out var dataEl))
                return null;
            return JsonDocument.Parse(dataEl.GetRawText());
        }
        catch
        {
            DisposeProc();
            return null;
        }
        finally
        {
            _gate.Release();
        }
    }

    private Process? EnsureProcess(string repoRoot)
    {
        if (_proc is { HasExited: false })
            return _proc;
        DisposeProc();
        var psi = EngineProcessRunner.CreateResultsStorePsi(repoRoot, redirectOutput: true);
        psi.RedirectStandardInput = true;
        psi.ArgumentList.Add("--root");
        psi.ArgumentList.Add(ProfilePaths.DeviceRoot);
        psi.ArgumentList.Add("--sidecar");
        _proc = Process.Start(psi);
        return _proc;
    }

    private void DisposeProc()
    {
        try
        {
            if (_proc is { HasExited: false })
                _proc.Kill(entireProcessTree: true);
        }
        catch { /* ignore */ }
        try { _proc?.Dispose(); } catch { /* ignore */ }
        _proc = null;
    }

    private static string InjectId(JsonElement root, int id)
    {
        using var ms = new MemoryStream();
        using (var w = new Utf8JsonWriter(ms))
        {
            w.WriteStartObject();
            w.WriteNumber("id", id);
            foreach (var prop in root.EnumerateObject())
            {
                if (!string.Equals(prop.Name, "id", StringComparison.Ordinal))
                    prop.WriteTo(w);
            }
            w.WriteEndObject();
        }
        return System.Text.Encoding.UTF8.GetString(ms.ToArray());
    }
}
