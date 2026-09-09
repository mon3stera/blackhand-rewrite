# Launch Test Document (menu command 23) and capture evidence.
# Saves a desktop screenshot to Windows temp so we can inspect the running game.

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$main = Find-Main
Write-Output ("main = " + $main + " title='" + (Get-WindowTitle $main) + "'")

Write-Output "=== 发送 Test Document (WM_COMMAND 23) ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]23, [IntPtr]::Zero)

for ($i = 1; $i -le 12; $i++) {
  Start-Sleep -Seconds 5
  $procs = Get-Process -Name SC2_x64 -ErrorAction SilentlyContinue
  $dlgs = @()
  foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
    if ($a -match "\|#32770\|True\|" -and $a -notmatch "Triggers - \[|Terrain - \[|Messages - |Console - ") { $dlgs += $a }
  }
  Write-Output ("[" + ($i * 5) + "s] SC2_x64 = " + ($procs | Measure-Object).Count + "  编辑器对话框 = " + ($dlgs -join "; "))
  if ($dlgs.Count -gt 0) {
    foreach ($d in $dlgs) {
      $h = [IntPtr][int64]($d.Split("|")[0])
      Write-Output ("     DLG " + $d)
      foreach ($k in [SC2]::KidsAll($h)) { Write-Output ("       " + $k) }
    }
  }
  if (($procs | Measure-Object).Count -gt 0) { break }
}

Write-Output "=== 顶层窗口 ==="
foreach ($p in (Get-Process | Where-Object { $_.MainWindowTitle -ne "" }) | Select-Object -First 25) {
  Write-Output ("  " + $p.ProcessName + " | " + $p.MainWindowTitle)
}

Write-Output "=== 截图 ==="
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
Write-Output ("screen = " + $b.Width + "x" + $b.Height)
$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.X, $b.Y, 0, 0, $bmp.Size)
$out = "C:\Users\Administrator\AppData\Local\Temp\dsh_shot.png"
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ("saved " + $out)
