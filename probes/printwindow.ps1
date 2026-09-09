# Capture a specific window with PrintWindow (PW_RENDERFULLCONTENT), which also
# works for some D3D/exclusive-fullscreen windows where GDI screen capture fails.

Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class PW {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
"@

$name = "SC2Editor_x64"
$out = "C:\Users\Administrator\AppData\Local\Temp\dsh_printwindow2.png"

$p = Get-Process -Name $name -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $p) { Write-Output ($name + " 未运行"); return }
$h = $p.MainWindowHandle
Write-Output ("hwnd = " + $h + " title=" + $p.MainWindowTitle)

$r = New-Object PW+RECT
[void][PW]::GetWindowRect($h, [ref]$r)
$w = [int]($r.R - $r.L); $hh = [int]($r.B - $r.T)
Write-Output ("rect = " + $r.L + "," + $r.T + " size = " + $w + "x" + $hh)

$bmp = New-Object System.Drawing.Bitmap($w, $hh)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [PW]::PrintWindow($h, $hdc, [uint32]2)
$g.ReleaseHdc($hdc)
$g.Dispose()
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output ("PrintWindow = " + $ok + " -> " + (Get-Item $out).Length + " bytes")
