$main = Find-Main
Write-Output ("title = " + (Get-WindowTitle $main))
Write-Output "=== 主窗口下所有 SysTreeView32 ==="
function Walk([IntPtr]$h, [int]$depth) {
  foreach ($k in [SC2]::KidsAll($h)) {
    $g = $k.Split("|")
    if ($g[1] -eq "SysTreeView32") {
      $items = 0
      $t = [IntPtr][int64]$g[0]
      try { $items = List-Count $t } catch { }
      Write-Output ("  hwnd=" + $g[0] + " rect=" + $g[3] + " 项数=" + $items)
    }
    if ($depth -lt 4) { Walk ([IntPtr][int64]$g[0]) ($depth + 1) }
  }
}
Walk $main 0
