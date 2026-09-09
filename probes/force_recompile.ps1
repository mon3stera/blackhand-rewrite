# Force the open document to become dirty and save it, so the editor regenerates
# MapScript.galaxy from the (externally generated) Triggers XML.
#
#   python3 tools/sc2gui.py --timeout 900 probes/force_recompile.ps1

$main = Find-Main
Write-Output ("start: " + (Get-WindowTitle $main))

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

function Clear-StrayDialogs {
  for ($i = 0; $i -lt 6; $i++) {
    $d = Get-StrayDialog
    if ($d -eq [IntPtr]::Zero) { break }
    Write-Output ("  [dialog] '" + (Get-WindowTitle $d) + "'")
    foreach ($k in [SC2]::KidsAll($d)) {
      $g = $k.Split("|")
      if ($g[1] -ne "SysListView32" -or $g[2] -ne "True") { continue }
      $lv = [IntPtr][int64]$g[0]
      for ($j = 0; $j -lt (List-Count $lv); $j++) { Write-Output ("     " + (Read-ListItem $lv $j)) }
    }
    $btn = [IntPtr]::Zero; $okBtn = [IntPtr]::Zero; $noBtn = [IntPtr]::Zero
    foreach ($k in [SC2]::KidsAll($d)) {
      $g = $k.Split("|")
      if ($g[1] -ne "Button") { continue }
      if ($g[4] -eq "id=12") { $btn = [IntPtr][int64]$g[0]; break }
      if ($g[4] -eq "id=7" -or $g[5] -match "^&?No$|Cancel|Close") { $noBtn = [IntPtr][int64]$g[0] }
      if ($g[4] -eq "id=11" -or $g[5] -match "^&?OK$") { $okBtn = [IntPtr][int64]$g[0] }
    }
    if ($btn -eq [IntPtr]::Zero) { $btn = $noBtn }
    if ($btn -eq [IntPtr]::Zero) { $btn = $okBtn }
    if ($btn -eq [IntPtr]::Zero) { [void][SC2]::PostMessage($d, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) }
    else { Click-Btn $btn }
    Start-Sleep -Seconds 2
  }
}

function Get-TriggerList {
  $lt = (Get-Trees)[0]
  $res = @()
  $cur = Get-Root $lt
  while ($cur -ne [IntPtr]::Zero) { $res += (Get-NodeText $lt $cur); $cur = Get-Next $lt $cur }
  return $res
}

function Select-TriggerNode([string]$name) {
  $lt = (Get-Trees)[0]; $et = (Get-Trees)[1]
  $target = [IntPtr]::Zero; $neighbor = [IntPtr]::Zero
  $cur = Get-Root $lt
  while ($cur -ne [IntPtr]::Zero) {
    $t = Get-NodeText $lt $cur
    if ($t -eq $name) { $target = $cur }
    elseif ($neighbor -eq [IntPtr]::Zero -and $t -ne $name) { $neighbor = $cur }
    $cur = Get-Next $lt $cur
  }
  if ($target -eq [IntPtr]::Zero) { return $false }
  if ($neighbor -ne [IntPtr]::Zero) {
    Select-Node $lt $neighbor; Start-Sleep -Milliseconds 400
    Click-Node $lt $neighbor; Start-Sleep -Milliseconds 1000
  }
  Select-Node $lt $target; Start-Sleep -Milliseconds 400
  Click-Node $lt $target; Start-Sleep -Milliseconds 1600
  return ((Get-NodeText $et (Get-Root $et)) -eq $name)
}

[void](Clear-StrayDialogs)
$before = Get-TriggerList
Write-Output ("=== 当前列表（" + $before.Count + " 项）===")
foreach ($t in $before) { Write-Output ("  " + $t) }

$lt = (Get-Trees)[0]
$sel = $false
foreach ($name in @("Init", "Spawn", "Buff1", "BuffChoice")) {
  if (Select-TriggerNode $name) { Write-Output ("选中: " + $name); $sel = $true; break }
}
if (-not $sel) { Write-Output "!! 无法选中任何触发器" }

Set-CtrlFocus $lt
Start-Sleep -Milliseconds 500

$new = @()
for ($try = 1; $try -le 3; $try++) {
  Write-Output ("--- 尝试新建触发器 #" + $try)
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]580, [IntPtr]::Zero)
  Start-Sleep -Seconds 4
  [void](Clear-StrayDialogs)
  $after = Get-TriggerList
  $new = @()
  foreach ($t in $after) { if ($before -notcontains $t) { $new += $t } }
  Write-Output ("    新增 = " + ($new -join ", ") + "  (总数 " + $after.Count + ")")
  if ($new.Count -gt 0) { break }
}

if ($new.Count -eq 0) {
  Write-Output "!! 新建失败，尝试重命名脏标记"
  Set-CtrlFocus $lt
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]83, [IntPtr]::Zero)
  Start-Sleep -Seconds 1
  $edit = [IntPtr]::Zero
  foreach ($k in [SC2]::KidsAll($lt)) {
    $g = $k.Split("|")
    if ($g[1] -eq "Edit") { $edit = [IntPtr][int64]$g[0] }
  }
  if ($edit -ne [IntPtr]::Zero) {
    [void][SC2]::SendMessageW($edit, 0x000C, [IntPtr]::Zero, "SpawnX")
    Start-Sleep -Milliseconds 300
    [void][SC2]::SendMessage($edit, 0x0100, [IntPtr]13, [IntPtr]::Zero)
    [void][SC2]::SendMessage($edit, 0x0101, [IntPtr]13, [IntPtr]::Zero)
    Start-Sleep -Seconds 2
    Write-Output ("    重命名后标题: " + (Get-WindowTitle $main))
  } else {
    Write-Output "    !! 没有内联编辑框"
  }
} else {
  foreach ($n in $new) {
    if (Select-TriggerNode $n) {
      [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
      Start-Sleep -Seconds 2
      [void](Clear-StrayDialogs)
    } else { Write-Output ("  !! 无法选中 " + $n) }
  }
  $final = Get-TriggerList
  Write-Output ("  删除后列表数 = " + $final.Count + " (原 " + $before.Count + ")")
}

Write-Output ("=== 保存前标题: " + (Get-WindowTitle $main))
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Seconds 2
  [void](Clear-StrayDialogs)
  $t = Get-WindowTitle $main
  if ($t -notmatch "\*") { Write-Output ("[saved " + ($i*2+2) + "s] " + $t); break }
  if ($i -eq 89) { Write-Output ("!! 保存超时: " + $t) }
}
[void](Clear-StrayDialogs)
Write-Output ("=== 最终标题: " + (Get-WindowTitle $main))
