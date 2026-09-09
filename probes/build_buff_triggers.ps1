# Build Buff1/Buff2/Buff3: event "Dialog Item Is Used" on BuffBtnN, then give the
# buff (create units) and hide the dialog.

$SPECS = @(
  @("Buff1", "BuffBtn1", "Marine",   "2"),
  @("Buff2", "BuffBtn2", "Medic",    "1"),
  @("Buff3", "BuffBtn3", "Marauder", "1")
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

function New-Trigger([string]$name, [string]$after) {
  $existing = Find-TriggerNode $listTree $name
  if ($existing -ne [IntPtr]::Zero) {
    Write-Output ("  删除已存在的 " + $name)
    Click-Node $listTree $existing
    Start-Sleep -Milliseconds 900
    [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 1500
  }
  Click-Node $listTree (Find-TriggerNode $listTree $after)
  Start-Sleep -Milliseconds 1200
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]580, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 2500
  foreach ($k in [SC2]::KidsAll($main)) {
    if ($k -match "\|Edit\|" -and $k -match "Untitled Trigger") {
      $edit = [IntPtr][int64]($k.Split("|")[0])
      Set-EditText $edit $name
      Start-Sleep -Milliseconds 500
      [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)
      [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
      Start-Sleep -Milliseconds 1400
    }
  }
  Write-Output ("  新建触发器: " + $name)
}

function Add-Event([string]$trigger, [string]$search) {
  Click-Node $elemTree (Get-GroupNode $elemTree $trigger "Events")
  Start-Sleep -Milliseconds 1100
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]581, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 2800
  $dlg = Find-Dialog
  if (-not (Select-ListItemByText $dlg $search 20 19)) {
    Write-Output ("  !! 找不到事件 " + $search)
    Click-Btn (Find-Child $dlg "Button\|Cancel")
    return
  }
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2000
}

function Add-Action([string]$trigger, [string]$search) {
  $acts = Get-GroupChildren $elemTree $trigger "Actions"
  if ($acts.Count -gt 0) { Click-Node $elemTree $acts[$acts.Count - 1] } else { Click-Node $elemTree (Get-GroupNode $elemTree $trigger "Actions") }
  Start-Sleep -Milliseconds 1100
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 2800
  $dlg = Find-Dialog
  if (-not (Select-ListItemByText $dlg $search 20 19)) {
    Write-Output ("  !! 找不到动作 " + $search)
    Click-Btn (Find-Child $dlg "Button\|Cancel")
    return
  }
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2000
}

function Node-At([string]$trigger, [string]$group, [int]$i) { return (Get-GroupChildren $elemTree $trigger $group)[$i] }

function Set-ParamVar([IntPtr]$node, [int]$pi, [string]$var) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $btns = Get-ParamButtons $main
  Click-Btn $btns[$pi]; Start-Sleep -Milliseconds 1800
  $d = Find-Dialog
  if ((Get-WindowTitle $d) -ne "Any Variable") {
    $vb = Find-Child $d "Button\|&Variable"
    if ($vb -ne [IntPtr]::Zero) { Click-Btn $vb; Start-Sleep -Milliseconds 1400 }
  }
  Set-DialogVariable $d $var
  Start-Sleep -Milliseconds 900
}

function Set-ParamInt([IntPtr]$node, [int]$pi, [string]$val) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $btns = Get-ParamButtons $main
  Click-Btn $btns[$pi]; Start-Sleep -Milliseconds 1800
  Set-DialogInt (Find-Dialog) $val
  Start-Sleep -Milliseconds 900
}

function Set-ParamUnit([IntPtr]$node, [int]$pi, [string]$unit) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $btns = Get-ParamButtons $main
  Click-Btn $btns[$pi]; Start-Sleep -Milliseconds 2000
  $d = Find-Dialog
  Write-Output ("    unit dialog = '" + (Get-WindowTitle $d) + "'")
  Set-DialogGameLink $d $unit
  Start-Sleep -Milliseconds 1200
}

function Set-ParamPreset([IntPtr]$node, [int]$pi, [string]$value) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $btns = Get-ParamButtons $main
  Click-Btn $btns[$pi]; Start-Sleep -Milliseconds 1800
  $d = Find-Dialog
  $lv = Filter-List $d 59 58 $value
  $idx = Find-ListIndexByText $lv $value
  if ($idx -lt 0) { Write-Output ("    !! 找不到预设 " + $value); Click-Btn (Find-Child $d "Button\|Cancel"); return }
  Set-ListSel $lv $idx
  Start-Sleep -Milliseconds 500
  Click-Btn (Find-Child $d "Button\|&OK")
  Start-Sleep -Milliseconds 1500
}

function Set-ParamPointXY([IntPtr]$node, [int]$parenIndex, [string]$x, [string]$y) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $btns = Get-ParamButtons $main
  $parens = @()
  for ($i = 0; $i -lt $btns.Count; $i++) { if ((Get-WindowTitle $btns[$i]) -eq "(") { $parens += $i } }
  if ($parenIndex -ge $parens.Count) { Write-Output "    !! 没有第 $parenIndex 个点参数"; return }
  Click-Btn $btns[$parens[$parenIndex]]; Start-Sleep -Milliseconds 2000
  [void](Set-DialogPointFunc (Find-Dialog) "Point From XY" "Point From")
  Start-Sleep -Milliseconds 1200

  foreach ($val in @($x, $y)) {
    Click-Node $elemTree $node; Start-Sleep -Milliseconds 900
    $btns = Get-ParamButtons $main
    $parens = @()
    for ($i = 0; $i -lt $btns.Count; $i++) { if ((Get-WindowTitle $btns[$i]) -eq "(") { $parens += $i } }
    $start = $parens[$parenIndex] + 1
    $end = if ($parens.Count -gt $parenIndex + 1) { $parens[$parenIndex + 1] - 1 } else { $btns.Count - 1 }
    $target = -1
    for ($k = $start; $k -le $end; $k++) { if ((Get-WindowTitle $btns[$k]) -notlike ($val + "*")) { $target = $k; break } }
    if ($target -lt 0) { break }
    Click-Btn $btns[$target]; Start-Sleep -Milliseconds 1800
    Set-DialogInt (Find-Dialog) $val
    Start-Sleep -Milliseconds 900
  }
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

$prev = "BuffChoice"
foreach ($spec in $SPECS) {
  $name = $spec[0]; $btnVar = $spec[1]; $unit = $spec[2]; $count = $spec[3]
  Write-Output ("########## " + $name + " : " + $count + " x " + $unit + " ##########")
  New-Trigger $name $prev
  Click-Node $listTree (Find-TriggerNode $listTree $name)
  Start-Sleep -Milliseconds 1400

  Add-Event $name "Dialog Item Is Used"
  $ev = (Get-GroupChildren $elemTree $name "Events")[0]
  if ($ev -ne [IntPtr]::Zero) { Set-ParamVar $ev 0 $btnVar }

  Add-Action $name "Create Units Facing Point"
  $act = (Get-GroupChildren $elemTree $name "Actions")[0]
  if ($act -ne [IntPtr]::Zero) {
    Set-ParamInt $act 0 $count
    Set-ParamUnit $act 1 $unit
    Set-ParamPointXY $act 0 $SPAWN_X $SPAWN_Y
    Set-ParamPointXY $act 1 $SPAWN_X $SPAWN_Y
  }

  Add-Action $name "Show/Hide Dialog"
  $hide = (Get-GroupChildren $elemTree $name "Actions")[1]
  if ($hide -ne [IntPtr]::Zero) {
    Set-ParamPreset $hide 0 "Hide"
    Set-ParamVar $hide 1 "BuffDialog"
  }

  Write-Output ("  --- " + $name + " 结果 ---")
  foreach ($g in @("Events", "Actions")) {
    foreach ($n in (Get-GroupChildren $elemTree $name $g)) { Write-Output ("    " + (Get-NodeText $elemTree $n)) }
  }
  $prev = $name
}

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
