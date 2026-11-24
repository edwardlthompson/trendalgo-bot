using System.Runtime.InteropServices;
using System.Text;

namespace TrendAlgo.Shell.Services;

/// <summary>Windows Credential Manager adapter — same TargetNames as PySide vaults.</summary>
public sealed class WindowsCredManStore
{
    private const int CredTypeGeneric = 1;
    private const int CredPersistLocalMachine = 2;
    private const int ErrorNotFound = 1168;

    public bool Has(string target)
    {
        if (!OperatingSystem.IsWindows())
            return false;
        if (!CredRead(target, CredTypeGeneric, 0, out var ptr))
            return false;
        try
        {
            var cred = Marshal.PtrToStructure<NativeCredential>(ptr);
            return cred.CredentialBlobSize > 0;
        }
        finally
        {
            CredFree(ptr);
        }
    }

    public string? Read(string target)
    {
        if (!OperatingSystem.IsWindows())
            return null;
        if (!CredRead(target, CredTypeGeneric, 0, out var ptr))
            return null;
        try
        {
            var cred = Marshal.PtrToStructure<NativeCredential>(ptr);
            if (cred.CredentialBlobSize == 0 || cred.CredentialBlob == IntPtr.Zero)
                return null;
            var bytes = new byte[cred.CredentialBlobSize];
            Marshal.Copy(cred.CredentialBlob, bytes, 0, bytes.Length);
            // Python stores UTF-8; recover legacy UTF-16LE entries if alternating null bytes are present.
            var looksUtf16Le = bytes.Length >= 2
                && bytes.Length % 2 == 0
                && bytes[1] == 0
                && bytes[0] != 0;
            return (looksUtf16Le
                ? Encoding.Unicode.GetString(bytes)
                : Encoding.UTF8.GetString(bytes)).TrimEnd('\0');
        }
        finally
        {
            CredFree(ptr);
        }
    }

    public void Write(string target, string secret)
    {
        if (!OperatingSystem.IsWindows())
            throw new InvalidOperationException("CredMan is Windows-only.");
        var blob = Encoding.UTF8.GetBytes(secret);
        var cred = new NativeCredential
        {
            Type = CredTypeGeneric,
            TargetName = target,
            CredentialBlobSize = (uint)blob.Length,
            Persist = CredPersistLocalMachine,
            UserName = Environment.UserName,
        };
        var handle = GCHandle.Alloc(blob, GCHandleType.Pinned);
        try
        {
            cred.CredentialBlob = handle.AddrOfPinnedObject();
            if (!CredWrite(ref cred, 0))
                throw new InvalidOperationException($"CredWrite failed ({Marshal.GetLastWin32Error()}).");
        }
        finally
        {
            handle.Free();
        }
    }

    public void Delete(string target)
    {
        if (!OperatingSystem.IsWindows())
            return;
        if (!CredDelete(target, CredTypeGeneric, 0))
        {
            var code = Marshal.GetLastWin32Error();
            if (code != ErrorNotFound)
                throw new InvalidOperationException($"CredDelete failed ({code}).");
        }
    }

    public IReadOnlyList<(string Kind, string Target, bool Present)> CorePresence()
    {
        var list = new List<(string, string, bool)>(CredManTargets.CoreTargets.Count);
        foreach (var (kind, target) in CredManTargets.CoreTargets)
            list.Add((kind, target, Has(target)));
        return list;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct NativeCredential
    {
        public uint Flags;
        public uint Type;
        public string TargetName;
        public string? Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public uint CredentialBlobSize;
        public IntPtr CredentialBlob;
        public uint Persist;
        public uint AttributeCount;
        public IntPtr Attributes;
        public string? TargetAlias;
        public string? UserName;
    }

    [DllImport("advapi32.dll", EntryPoint = "CredReadW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CredRead(string target, int type, int reserved, out IntPtr credential);

    [DllImport("advapi32.dll", EntryPoint = "CredWriteW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CredWrite(ref NativeCredential credential, uint flags);

    [DllImport("advapi32.dll", EntryPoint = "CredDeleteW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CredDelete(string target, int type, int reserved);

    [DllImport("advapi32.dll", EntryPoint = "CredFree", SetLastError = true)]
    private static extern void CredFree(IntPtr buffer);
}
