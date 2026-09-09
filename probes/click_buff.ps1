# Try to click the "增援" dialog button through PostMessage and screenshot the result.

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$p = Get-Process -Name SC2_x64 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $p) { Write-Output "SC2 未运行"; return }
$h = $p.MainWindowHandle
Write-Output ("SC2 hwnd = " + $h + " title=" + $p.MainWindowTitle)

$r = New-Object SC2+RECT
[void][SC2]::GetWindowRect($h, [ref]$r)
Write-Output ("window rect = " + $r.L + "," + $r.T + "," + $r.R + "," + $r.B)

# button centre measured from the screenshot (screen pixels)
$sx = 1153; $sy = 637
$cx = $sx - $r.L; $cy = $sy - $r.T
Write-Output ("client click = " + $cx + "," + $cy)

$lp = [IntPtr]($cx -bor ($cy -shl 16))
[void][SC2]::PostMessage($h, 0x0200, [IntPtr]0, $lp)        # WM_MOUSEMOVE
Start-Sleep -Milliseconds 400
[void][SC2]::PostMessage($h, 0x0201, [IntPtr]1, $lp)        # WM_LBUTTONDOWN
Start-Sleep -Milliseconds 120
[void][SC2]::PostMessage($h, 0x0202, [IntPtr]0, $lp)        # WM_LBUTTONUP
Write-Output "clicked"

Start-Sleep -Seconds 4
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.X, $b.Y, 0, 0, $bmp.Size)
$bmp.Save("C:\Users\Administrator\AppData\Local\Temp\dsh_click.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output "screenshot saved"
