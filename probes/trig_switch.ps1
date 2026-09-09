$main = Find-Main
Write-Output ("main = " + $main + "  title = " + (Get-WindowTitle $main))
Write-Output "=== 该进程所有顶层窗口 ==="
foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  Write-Output ("  hwnd=" + $f[0] + " visible=" + $f[2] + " cls=" + $f[1] + " title='" + $f[4] + "'")
}
# 尝试激活后切换模块
[void][SC2]::SetForegroundWindow($main)
Start-Sleep -Milliseconds 600
Set-CtrlFocus $main
Start-Sleep -Milliseconds 300
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]304, [IntPtr]::Zero)
Start-Sleep -Seconds 5
Write-Output ("切换后 title = " + (Get-WindowTitle $main))
