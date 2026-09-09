# Dump editor top-level windows; a disabled main window means a modal dialog.

$main = Find-Main
Write-Output ("main=" + (Get-WindowTitle $main) + " enabled=" + [SC2]::IsWindowEnabled($main))

foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  Write-Output ("  top class=" + $f[1] + " visible=" + $f[2] + " enabled=" + [SC2]::IsWindowEnabled([IntPtr][int64]$f[0]) + " title='" + $f[4] + "' rect=" + $f[3])
}

Write-Output "--- 主窗口直接子控件 ---"
foreach ($k in [SC2]::KidsAll($main)) {
  $g = $k.Split("|")
  if ($g[4] -eq "id=0") { continue }
  Write-Output ("  " + $g[1] + " " + $g[4] + " visible=" + $g[2] + " text='" + $g[5] + "'")
}
