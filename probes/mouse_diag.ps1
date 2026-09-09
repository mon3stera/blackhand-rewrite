# Mouse diagnostic: close the F10 menu, hover the "增援" button, screenshot the
# hover state, then click and screenshot again.

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class MIN {
  [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx, dy; public uint data, flags, time; public IntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public MOUSEINPUT mi; }
  [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] inputs, int size);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, IntPtr extra);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
}
"@

$p = Get-Process -Name SC2_x64 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $p) { Write-Output "SC2 未运行"; return }
[void][MIN]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep -Milliseconds 1000

# close the F10 menu
[MIN]::keybd_event(0x1B, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 80
[MIN]::keybd_event(0x1B, 0, 2, [IntPtr]::Zero)
Start-Sleep -Milliseconds 1500

function Shot([string]$path) {
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.X, $b.Y, 0, 0, $bmp.Size)
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
}

$sx = 1153; $sy = 637
[void][MIN]::SetCursorPos($sx, $sy)
Start-Sleep -Milliseconds 1500
$pt = New-Object MIN+POINT
[void][MIN]::GetCursorPos([ref]$pt)
Write-Output ("cursor = " + $pt.X + "," + $pt.Y)
Shot "C:\Users\Administrator\AppData\Local\Temp\dsh_hover.png"

# SendInput absolute move + click
$inp = New-Object MIN+INPUT
$inp.type = 0
$inp.mi = New-Object MIN+MOUSEINPUT
$inp.mi.dx = [int](65535 * $sx / 1707)
$inp.mi.dy = [int](65535 * $sy / 1067)
$inp.mi.flags = 0x0001 -bor 0x8000
$null = [MIN]::SendInput(1, @($inp), [System.Runtime.InteropServices.Marshal]::SizeOf([type]'MIN+INPUT'))
Start-Sleep -Milliseconds 300

$inp.mi.dx = 0; $inp.mi.dy = 0; $inp.mi.flags = 0x0002
$null = [MIN]::SendInput(1, @($inp), [System.Runtime.InteropServices.Marshal]::SizeOf([type]'MIN+INPUT'))
Start-Sleep -Milliseconds 120
$inp.mi.flags = 0x0004
$null = [MIN]::SendInput(1, @($inp), [System.Runtime.InteropServices.Marshal]::SizeOf([type]'MIN+INPUT'))
Write-Output "SendInput click sent"

Start-Sleep -Seconds 4
Shot "C:\Users\Administrator\AppData\Local\Temp\dsh_after.png"
Write-Output "screenshots saved"
