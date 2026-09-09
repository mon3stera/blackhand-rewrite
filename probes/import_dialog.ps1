# 打开“导入管理器”（F9）并 dump 它的控件结构，为自动化导入 CustomGameScript.galaxy 做准备。
#
#   python3 tools/sc2gui.py --timeout 300 probes/import_dialog.ps1

$main = Find-Main
Write-Output ("main = " + (Get-WindowTitle $main))
Write-Output ("pid  = " + $P.Id)

# F9 -> 导入管理器
[void][SC2]::SetForegroundWindow($main)
Start-Sleep -Milliseconds 500
[void][SC2]::SendMessage($main, 0x0100, [IntPtr]0x78, [IntPtr]::Zero)   # WM_KEYDOWN F9
Start-Sleep -Milliseconds 150
[void][SC2]::SendMessage($main, 0x0101, [IntPtr]0x78, [IntPtr]::Zero)   # WM_KEYUP   F9
Start-Sleep -Seconds 3

Write-Output "=== 顶层窗口 ==="
foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  $visible = $f[2]
  $cls = $f[1]
  $title = $f[4]
  if ($visible -ne "True") { continue }
  Write-Output ("  " + $f[0] + "  cls=" + $cls + "  title='" + $title + "'")

  # 对可能的对话框 dump 一层子控件
  if ($cls -eq "#32770" -or $title -match "Import|导入") {
    $h = [IntPtr][int64]$f[0]
    foreach ($k in [SC2]::KidsAll($h)) {
      $g = $k.Split("|")
      Write-Output ("      " + $g[1] + "  id=" + $g[4] + "  text='" + $g[5] + "'  rect=" + $g[3])
    }
  }
}

Write-Output "=== 菜单里的导入相关命令 ==="
$bar = [SC2]::GetMenu($main)
function Walk([IntPtr]$menu, [string]$prefix) {
  $n = [SC2]::GetMenuItemCount($menu)
  for ($i = 0; $i -lt $n; $i++) {
    $sb = New-Object System.Text.StringBuilder 256
    [void][SC2]::GetMenuStringW($menu, $i, $sb, 256, 0x0400)
    $label = $sb.ToString()
    $id = [SC2]::GetMenuItemID($menu, $i)
    $sub = [SC2]::GetSubMenu($menu, $i)
    if ($sub -ne [IntPtr]::Zero) {
      Walk $sub ($prefix + "  ")
    } elseif ($label -match "导入|Import|管理器") {
      Write-Output ($prefix + $label + "  id=" + $id)
    }
  }
}
Walk $bar ""
