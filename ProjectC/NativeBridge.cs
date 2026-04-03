using System.Runtime.InteropServices;

namespace ProjectC;

/// <summary>
/// P/Invoke declarations for ProjectB.dll (C++ DLL that chains through ProjectA).
/// ProjectB.dll must be present in the same directory as this assembly at runtime.
/// </summary>
internal static class NativeBridge
{
    // CallingConvention.Cdecl matches the default for extern "C" on MSVC x64.
    [DllImport("ProjectB", CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Ansi)]
    private static extern IntPtr GetJsonGreeting();

    /// <summary>
    /// Calls GetJsonGreeting() from ProjectB.dll and marshals the result to a managed string.
    /// The native memory is owned by ProjectB and must NOT be freed by the caller.
    /// </summary>
    public static string GetJsonGreetingManaged()
    {
        IntPtr ptr = GetJsonGreeting();
        return Marshal.PtrToStringAnsi(ptr)
               ?? throw new InvalidOperationException("GetJsonGreeting returned null.");
    }
}
