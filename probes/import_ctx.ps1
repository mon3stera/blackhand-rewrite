# 取消 New Document，然后在导入管理器的树节点上右键，dump 上下文菜单命令。
$main = Find-Main

function Get-DialogByTitle([string]$pattern) {
  foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
    $f = $w.Split("|")
    if ($f[2] -ne "True") { continue }
    if ($f[4] -match $pattern) { return [IntPtr][int64]$f[0] }
  }
  return [IntPtr]::Zero
}

$nd = Get-DialogByTitle "^New Document"
if ($nd -ne [IntPtr]::Zero) {
  foreach ($k in [SC2]::KidsAll($nd)) {
    $g = $k.Split("|")
    if ($g[1] -eq "Button" -and ($g[5] -match "Cancel|取消" -or $g[4] -eq "id=2")) {
      Click-Btn ([IntPtr][int64]$g[0]); Write-Output "已取消 New Document"; break
    }
  }
  Start-Sleep -Seconds 2
}

$dlg = Get-DialogByTitle "^\s*Import"
Write-Output ("import dialog = " + $dlg)
$tree = [IntPtr]::Zero
foreach ($k in [SC2]::KidsAll($dlg)) {
  $g = $k.Split("|")
  if ($g[1] -eq "SysTreeView32") { $tree = [IntPtr][int64]$g[0] }
}
Write-Output ("tree = " + $tree + "  rect=" + (Get-RectStr $tree))

# 右键点树中间
$r = (Get-RectStr $tree).Split(",")
$x = [int](([int]$r[0] + [int]$r[2]) / 2); $y = [int](([int]$r[1] + [int]$r[3]) / 2)
$lp = [IntPtr](($y -shl 16) -bor $x)
[void][SC2]::PostMessage($tree, 0x0204, [IntPtr]2, $lp)   # WM_RBUTTONDOWN
Start-Sleep -Milliseconds 150
[void][SC2]::PostMessage($tree, 0x0205, [IntPtr]::Zero, $lp)  # WM_RBUTTONUP
Start-Sleep -Seconds 2

$menu = [SC2]::GetMenu($dlg)
if ($menu -eq [IntPtr]::Zero) {
  foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
    $f = $w.Split("|")
    if ($f[2] -ne "True") { continue }
    $m = [SC2]::GetMenu([IntPtr][int64]$f[0])
    if ($m -ne [IntPtr]::Zero) {
      Write-Output ("窗口 '" + $f[4] + "' 有菜单")
      $n = [SC2]::GetMenuItemCount($m)
      for ($i = 0; $i -lt $n; $i++) {
        $sb = New-Object System.Text.StringBuilder 256
        [void][SC2]::GetMenuStringW($m, $i, $sb, 256, 0x0400)
        Write-Output ("   " + $sb.ToString() + "  id=" + [SC2]::GetMenuItemID($m, $i))
      }
    }
  }
} else {
  Write-Output "对话框自带菜单"
  $n = [SC2]::GetMenuItemCount($menu)
  for ($i = 0; $i -lt $n; $i++) {
    $sb = New-Object System.Text.StringBuilder 256
    [void][SC2]::GetMenuStringW($menu, $i, $sb, 256, 0x0400)
    Write-Output ("   " + $sb.ToString() + "  id=" + [SC2]::GetMenuItemID($menu, $i))
  }
}
