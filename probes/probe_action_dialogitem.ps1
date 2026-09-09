# Does the Dialog Item variable picker work from an ACTION parameter (as opposed to
# the event parameter)?

$TRIGGER = "Buff1"

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

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500

$acts = Get-GroupChildren $elemTree $TRIGGER "Actions"
Click-Node $elemTree $acts[$acts.Count - 1]
Start-Sleep -Milliseconds 1100
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 2800
$dlg = Find-Dialog
if (-not (Select-ListItemByText $dlg "Set Dialog Item Text" 20 19)) {
  Write-Output "找不到 Set Dialog Item Text"
  $lv = Find-ListByCtlId $dlg 20
  $null = Set-FilterText $dlg "Dialog Item" 1
  for ($i = 0; $i -lt [Math]::Min((List-Count $lv), 20); $i++) { Write-Output ("  [" + $i + "] " + (Read-ListItem $lv $i)) }
  Click-Btn (Find-Child $dlg "Button\|Cancel")
  return
}
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2200

$act = (Get-GroupChildren $elemTree $TRIGGER "Actions")
$node = $act[$act.Count - 1]
Click-Node $elemTree $node
Start-Sleep -Milliseconds 1200
Write-Output ("动作: " + (Get-NodeText $elemTree $node))
$i = 0
foreach ($b in (Get-ParamButtons $main)) { Write-Output ("  param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }

$btns = Get-ParamButtons $main
Write-Output ("=== 点击 param[0] '" + (Get-WindowTitle $btns[0]) + "' ===")
Click-Btn $btns[0]
Start-Sleep -Milliseconds 2200
$d = Find-Dialog
Write-Output ("dialog = '" + (Get-WindowTitle $d) + "'")
Click-Btn (Find-Child $d "Button\|&Variable")
Start-Sleep -Milliseconds 1800
$lv = Find-ListByCtlId $d 67
Write-Output ("variable list count = " + (List-Count $lv))
for ($i = 0; $i -lt [Math]::Min((List-Count $lv), 10); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }
$cancel = Find-Child $d "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
Start-Sleep -Milliseconds 800

Write-Output "=== 删掉刚加的动作 ==="
Click-Node $elemTree $node
Start-Sleep -Milliseconds 900
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
Start-Sleep -Milliseconds 1200
