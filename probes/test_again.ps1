# Re-run Test Document with the fixed point parameters and report the game's
# script-error log (the only machine-readable evidence of in-game behaviour).

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$existing = Get-Process -Name SC2_x64 -ErrorAction SilentlyContinue
if ($existing) {
  Write-Output ("关闭已有游戏进程: " + ($existing | Measure-Object).Count)
  $existing | Stop-Process -Force
  Start-Sleep -Seconds 5
}

$logDir = "C:\Users\Administrator\Documents\StarCraft II\GameLogs"
$before = @(Get-ChildItem $logDir -Filter "*ScriptError.txt" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name)

$main = Find-Main
Write-Output ("发送 Test Document，窗口: " + (Get-WindowTitle $main))
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]23, [IntPtr]::Zero)

for ($i = 1; $i -le 10; $i++) {
  Start-Sleep -Seconds 5
  $procs = @(Get-Process -Name SC2_x64 -ErrorAction SilentlyContinue)
  Write-Output ("[" + ($i * 5) + "s] SC2_x64 进程数 = " + $procs.Count)
  if ($procs.Count -gt 0) { break }
}

Write-Output "等待游戏运行 40 秒..."
Start-Sleep -Seconds 40

$after = @(Get-ChildItem $logDir -Filter "*ScriptError.txt" -ErrorAction SilentlyContinue)
foreach ($f in $after) {
  if ($before -notcontains $f.Name) {
    Write-Output ("=== 新脚本错误日志: " + $f.Name + " ===")
    Get-Content $f.FullName | Select-Object -First 60 | ForEach-Object { Write-Output ("  " + $_) }
  }
}
if (($after | Measure-Object).Count -eq ($before | Measure-Object).Count) {
  Write-Output "=== 没有新的 ScriptError 日志（无脚本错误）==="
}

Write-Output "=== 截图 ==="
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.X, $b.Y, 0, 0, $bmp.Size)
$out = "C:\Users\Administrator\AppData\Local\Temp\dsh_shot2.png"
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ("saved " + $out)
