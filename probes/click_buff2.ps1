# Click the "增援" dialog button with a real mouse event (SendInput-class), not
# PostMessage, then screenshot.

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class INP {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, IntPtr extra);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
}
"@

$p = Get-Process -Name SC2_x64 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $p) { Write-Output "SC2 未运行"; return }
$h = $p.MainWindowHandle
Write-Output ("SC2 hwnd = " + $h)

[void][INP]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 1200
$fg = [INP]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 256
[void][INP]::GetWindowText($fg, $sb, 256)
Write-Output ("foreground = " + $fg + " '" + $sb.ToString() + "'")

$sx = 1153; $sy = 637
[void][INP]::SetCursorPos($sx, $sy)
Start-Sleep -Milliseconds 400
[INP]::mouse_event(0x0001, 0, 0, 0, [IntPtr]::Zero)   # MOUSEEVENTF_MOVE
Start-Sleep -Milliseconds 200
[INP]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)   # LEFTDOWN
Start-Sleep -Milliseconds 120
[INP]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)   # LEFTUP
Write-Output ("clicked at " + $sx + "," + $sy)

Start-Sleep -Seconds 5
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.X, $b.Y, 0, 0, $bmp.Size)
$bmp.Save("C:\Users\Administrator\AppData\Local\Temp\dsh_click2.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output "screenshot saved"
