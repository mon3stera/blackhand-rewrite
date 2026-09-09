# Send File > Open (WM_COMMAND 11) and dump the resulting dialog structure.

$main = Find-Main
Write-Output ("main = " + $main)
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]11, [IntPtr]::Zero)
Start-Sleep -Seconds 3

Write-Output "=== 顶层窗口 ==="
$dlg = [IntPtr]::Zero
foreach ($w in [SC2]::Tops($P.Id)) {
  $f = $w.Split("|")
  Write-Output ("  " + $f[0] + "  [" + $f[1] + "]  vis=" + $f[2] + "  " + $f[4])
  if ($f[1] -eq "#32770" -and $f[4] -notmatch "Triggers - \[|Terrain - \[|Messages|Console|g_osGuiModalParent|m_gfxDialog") {
    $dlg = [IntPtr][int64]$f[0]
  }
}

if ($dlg -eq [IntPtr]::Zero) { Write-Output "!! 没找到新对话框"; return }
Write-Output ("=== 对话框 '" + (Get-WindowTitle $dlg) + "' ===")
foreach ($k in [SC2]::KidsAll($dlg)) { Write-Output ("  " + $k) }
