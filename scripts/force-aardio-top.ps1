# 强制 aardio IDE 窗口置顶 (HWND_TOPMOST), 参数: -Release 取消置顶
param([switch]$Release, [string]$TitlePattern = "*")

# 使用 C# 辅助类进行窗口控制
$proc = Get-Process aardio -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*$TitlePattern*" } | Select-Object -First 1
if(-not $proc){
    $proc = Get-Process aardio -ErrorAction SilentlyContinue | Select-Object -First 1
}
if(-not $proc){ Write-Output "[失败] 未找到 aardio 窗口"; exit 1 }

try {
    # 动态加载或使用现有类型
    Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class W32Top{ [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h,int hAfter,int x,int y,int cx,int cy,uint f); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int n); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); }' -ErrorAction SilentlyContinue
} catch {}

if($Release){
    try {
        [W32Top]::SetWindowPos($proc.MainWindowHandle, [IntPtr](-2), 0, 0, 0, 0, 0x0001 -bor 0x0002) | Out-Null
    } catch {}
    Write-Output "[已取消置顶] $($proc.MainWindowTitle)"
} else {
    try {
        [W32Top]::ShowWindow($proc.MainWindowHandle, 9) | Out-Null
        [W32Top]::SetWindowPos($proc.MainWindowHandle, [IntPtr](-1), 0, 0, 0, 0, 0x0001 -bor 0x0002 -bor 0x0040) | Out-Null
        [W32Top]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
    } catch {}
    Write-Output "[已置顶] $($proc.MainWindowTitle)"
}
