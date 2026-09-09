# Finish the buff system:
#   - fix the unset "Point" (position) parameter on every Create Units action
#   - replace the nonexistent Medic with Marauder, and make Buff3 a Thor
#   - give Buff2/Buff3 their (Used dialog item) == BuffBtnN condition
#   - relabel the three buttons to 增援 / 重装 / 精英

$SPECS = @(
  @("Buff1", "Marine", "2",   "BuffBtn1"),
  @("Buff2", "Marauder", "1", "BuffBtn2"),
  @("Buff3", "Thor", "1",     "BuffBtn3")
)
$SPAWN_X = "64"
$SPAWN_Y = "64"

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Find-TriggerNode([IntPtr]$tree, [string]$name) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -eq $name) { return $cur }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

function Get-GroupNode([IntPtr]$tree, [string]$trigger, [string]$group) {
  $t = Find-TriggerNode $tree $trigger
  if ($t -eq [IntPtr]::Zero) { return [IntPtr]::Zero }
  $c = Get-Child $tree $t
  while ($c -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $c) -eq $group) { return $c }
    $c = Get-Next $tree $c
  }
  return [IntPtr]::Zero
}

function Get-GroupChildren([IntPtr]$tree, [string]$trigger, [string]$group) {
  $g = Get-GroupNode $tree $trigger $group
  if ($g -eq [IntPtr]::Zero) { return @() }
  $res = @(); $a = Get-Child $tree $g
  while ($a -ne [IntPtr]::Zero) { $res += $a; $a = Get-Next $tree $a }
  return $res
}

function Get-SentenceButtons([IntPtr]$dlg) {
  $res = @()
  foreach ($k in [SC2]::KidsAll($dlg)) {
    if ($k -match "\|Button\|") {
      $h = [IntPtr][int64]($k.Split("|")[0])
      $r = (Get-RectStr $h).Split(",")
      if ([int]$r[1] -ge 570 -and [int]$r[1] -lt 625) { $res += ,@($h, (Get-WindowTitle $h)) }
    }
  }
  return $res
}

function Set-ParamUnit([IntPtr]$node, [int]$pi, [string]$unit) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $btns = Get-ParamButtons $main
  if ((Get-WindowTitle $btns[$pi]) -eq $unit) { Write-Output ("    单位已是 " + $unit); return }
  Click-Btn $btns[$pi]; Start-Sleep -Milliseconds 2200
  $d = Find-Dialog
  if ((Get-WindowTitle $d) -ne "Game Link - Unit") { Write-Output ("    !! 单位对话框 = '" + (Get-WindowTitle $d) + "'"); return }
  Set-DialogGameLink $d $unit
  Start-Sleep -Milliseconds 1200
}

function Set-ParamInt([IntPtr]$node, [int]$pi, [string]$val) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $btns = Get-ParamButtons $main
  if ((Get-WindowTitle $btns[$pi]) -eq $val) { return }
  Click-Btn $btns[$pi]; Start-Sleep -Milliseconds 1800
  Set-DialogInt (Find-Dialog) $val
  Start-Sleep -Milliseconds 900
}

function Set-PointParam([IntPtr]$node, [int]$pi, [string]$x, [string]$y) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $btns = Get-ParamButtons $main
  $title = Get-WindowTitle $btns[$pi]
  Write-Output ("    点位参数[" + $pi + "] = '" + $title + "'")
  if ($title -ne "(") {
    Click-Btn $btns[$pi]; Start-Sleep -Milliseconds 2000
    $d = Find-Dialog
    Write-Output ("      dialog = '" + (Get-WindowTitle $d) + "'")
    [void](Set-DialogPointFunc $d "Point From XY" "Point From")
    Start-Sleep -Milliseconds 1200
  }
  foreach ($off in @(1, 2)) {
    $val = if ($off -eq 1) { $x } else { $y }
    Click-Node $elemTree $node; Start-Sleep -Milliseconds 900
    $btns = Get-ParamButtons $main
    Write-Output ("      [" + ($pi + $off) + "] '" + (Get-WindowTitle $btns[$pi + $off]) + "' -> " + $val)
    Click-Btn $btns[$pi + $off]; Start-Sleep -Milliseconds 1800
    Set-DialogInt (Find-Dialog) $val
    Start-Sleep -Milliseconds 900
  }
}

function Add-UsedItemCondition([string]$trigger, [string]$var) {
  Write-Output ("    --- 条件 " + $trigger + " == " + $var)
  Click-Node $listTree (Find-TriggerNode $listTree $trigger); Start-Sleep -Milliseconds 1400
  Click-Node $elemTree (Get-GroupNode $elemTree $trigger "Conditions"); Start-Sleep -Milliseconds 1100
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]582, [IntPtr]::Zero); Start-Sleep -Milliseconds 3000
  $dlg = Find-Dialog
  if ((Get-WindowTitle $dlg) -ne "Configure Condition") { Write-Output ("    !! 对话框 = '" + (Get-WindowTitle $dlg) + "'"); return }
  $lv = Find-ListByCtlId $dlg 147
  Set-ListSel $lv (Find-ListIndexByText $lv "Comparison"); Start-Sleep -Milliseconds 1500
  $btns = Get-SentenceButtons $dlg
  Click-Btn $btns[0][0]; Start-Sleep -Milliseconds 2200
  $d2 = Find-Dialog
  Click-Btn (Find-Child $d2 "Button\|&Function"); Start-Sleep -Milliseconds 2000
  if (-not (Select-ListItemByText $d2 "Used Dialog Item" 43 42)) {
    Write-Output "    !! 找不到 Used Dialog Item"
    Click-Btn (Find-Child $d2 "Button\|Cancel"); return
  }
  Click-Btn (Find-Child $d2 "Button\|&OK"); Start-Sleep -Milliseconds 2000
  $btns = Get-SentenceButtons $dlg
  $right = [IntPtr]::Zero
  for ($i = 0; $i -lt $btns.Count; $i++) {
    if ($btns[$i][1] -eq "==" -and ($i + 1) -lt $btns.Count) { $right = $btns[$i + 1][0]; break }
  }
  if ($right -eq [IntPtr]::Zero) { Write-Output "    !! 找不到右槽"; Click-Btn (Find-Child $dlg "Button\|Cancel"); return }
  Click-Btn $right; Start-Sleep -Milliseconds 2200
  $d3 = Find-Dialog
  if ((Get-WindowTitle $d3) -ne "Any Variable") {
    $vb = Find-Child $d3 "Button\|&Variable"
    if ($vb -ne [IntPtr]::Zero) { Click-Btn $vb; Start-Sleep -Milliseconds 1600 }
  }
  Set-DialogVariable $d3 $var
  Start-Sleep -Milliseconds 1000
  Click-Btn (Find-Child $dlg "Button\|&OK"); Start-Sleep -Milliseconds 2500
  foreach ($c in (Get-GroupChildren $elemTree $trigger "Conditions")) { Write-Output ("    => " + (Get-NodeText $elemTree $c)) }
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

foreach ($spec in $SPECS) {
  $name = $spec[0]; $unit = $spec[1]; $count = $spec[2]; $var = $spec[3]
  Write-Output ("########## " + $name + " ##########")
  Click-Node $listTree (Find-TriggerNode $listTree $name)
  Start-Sleep -Milliseconds 1400
  $act = (Get-GroupChildren $elemTree $name "Actions")[0]
  if ($act -eq [IntPtr]::Zero) { Write-Output "  !! 没有动作"; continue }
  Set-ParamUnit $act 1 $unit
  Set-ParamInt $act 0 $count
  Set-PointParam $act 3 $SPAWN_X $SPAWN_Y
  Write-Output ("  动作: " + (Get-NodeText $elemTree $act))
  if ((Get-GroupChildren $elemTree $name "Conditions").Count -eq 0) {
    Add-UsedItemCondition $name $var
  } else {
    foreach ($c in (Get-GroupChildren $elemTree $name "Conditions")) { Write-Output ("  已有条件: " + (Get-NodeText $elemTree $c)) }
  }
}

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
