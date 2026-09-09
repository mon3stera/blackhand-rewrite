# 枚举导入管理器工具栏按钮，点击第一个（通常是 Import），再 dump 出来的文件对话框。
#   python3 tools/sc2gui.py --timeout 400 probes/import_toolbar.ps1

$main = Find-Main
$PANE_TITLES = @("Open Document", "g_osGuiModalParent", "CEditorApp::m_gfxDialog",
                 "Console - StarCraft II Editor", "Messages - StarCraft II Editor")

function Get-DialogByTitle([string]$pattern) {
  foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
    $f = $w.Split("|")
    if ($f[2] -ne "True") { continue }
    if ($f[4] -match $pattern) { return [IntPtr][int64]$f[0] }
  }
  return [IntPtr]::Zero
}

$dlg = Get-DialogByTitle "^\s*Import"
if ($dlg -eq [IntPtr]::Zero) {
  Write-Output "导入管理器未打开，先用 307 打开"
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]307, [IntPtr]::Zero)
  Start-Sleep -Seconds 4
  $dlg = Get-DialogByTitle "^\s*Import"
}
Write-Output ("dialog = " + $dlg + "  '" + (Get-WindowTitle $dlg) + "'")

$tb = [IntPtr]::Zero
foreach ($k in [SC2]::KidsAll($dlg)) {
  $g = $k.Split("|")
  if ($g[1] -eq "ToolbarWindow32") { $tb = [IntPtr][int64]$g[0] }
}
Write-Output ("toolbar = " + $tb)

if ($tb -ne [IntPtr]::Zero) {
  $count = [int][SC2]::SendMessage($tb, 0x0418, [IntPtr]::Zero, [IntPtr]::Zero)   # TB_BUTTONCOUNT
  Write-Output ("按钮数 = " + $count)

  for ($i = 0; $i -lt $count; $i++) {
    # TB_GETITEMRECT 需要把 RECT 写到目标进程，这里用简化方式：直接给出相对坐标猜测
    $txt = New-Object System.Text.StringBuilder 128
    $len = [int][SC2]::SendMessage($tb, 0x040B, [IntPtr]$i, [IntPtr]::Zero)       # TB_GETBUTTONTEXTW -> 长度
    Write-Output ("  btn[" + $i + "] textLen=" + $len)
  }

  # 点击第 0 个按钮：真实鼠标消息（工具栏按坐标响应）
  $r = Get-RectStr $tb
  Write-Output ("  toolbar rect = " + $r)

  # 用 BM_CLICK 不适用，改用 WM_LBUTTONDOWN/UP 落在第一个按钮上（约 (24,14)）
  $lp = [IntPtr]((14 -shl 16) -bor 24)
  [void][SC2]::PostMessage($tb, 0x0201, [IntPtr]1, $lp)   # WM_LBUTTONDOWN
  Start-Sleep -Milliseconds 120
  [void][SC2]::PostMessage($tb, 0x0202, [IntPtr]::Zero, $lp)  # WM_LBUTTONUP
  Start-Sleep -Seconds 3
}

Write-Output "=== 点击后的顶层窗口 ==="
foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[2] -ne "True") { continue }
  Write-Output ("  " + $f[0] + "  cls=" + $f[1] + "  title='" + $f[4] + "'")
}
