# 用 WM_COMMAND 307 打开“导入管理器”，dump 它的控件结构（为自动化导入做准备）。
#   python3 tools/sc2gui.py --timeout 300 probes/import_open.ps1

$main = Find-Main
Write-Output ("main = " + (Get-WindowTitle $main))
Write-Output ("pid  = " + $P.Id)

$PANE_TITLES = @("Open Document", "g_osGuiModalParent", "CEditorApp::m_gfxDialog",
                 "Console - StarCraft II Editor", "Messages - StarCraft II Editor")

function Get-StrayDialog {
  foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
    $f = $w.Split("|")
    if ($f[1] -ne "#32770") { continue }
    if ($f[2] -ne "True") { continue }
    if ($f[4] -match "^(Triggers|Terrain|Data|Modules) - ") { continue }
    if ($PANE_TITLES -contains $f[4]) { continue }
    if ($f[4] -eq "") { continue }
    return [IntPtr][int64]$f[0]
  }
  return [IntPtr]::Zero
}

Write-Output "=== 打开导入管理器 (WM_COMMAND 307) ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]307, [IntPtr]::Zero)
Start-Sleep -Seconds 4

Write-Output "=== 顶层窗口 ==="
foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[2] -ne "True") { continue }
  Write-Output ("  " + $f[0] + "  cls=" + $f[1] + "  title='" + $f[4] + "'")
}

$dlg = Get-StrayDialog
Write-Output ("stray dialog = " + $dlg)

if ($dlg -ne [IntPtr]::Zero) {
  Write-Output ("=== 对话框 '" + (Get-WindowTitle $dlg) + "' 的控件 ===")
  foreach ($k in [SC2]::KidsAll($dlg)) {
    $g = $k.Split("|")
    Write-Output ("  hwnd=" + $g[0] + "  cls=" + $g[1] + "  id=" + $g[4] + "  text='" + $g[5] + "'  rect=" + $g[3])
  }
}
