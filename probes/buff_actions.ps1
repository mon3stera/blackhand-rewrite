# Set the periodic event interval, then add a "Create Dialog" action and show its
# parameter row.

$TRIGGER = "BuffChoice"
$INTERVAL = "25.0"
$ACTION_SEARCH = "Create Dialog Item"

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

function Show-Row([IntPtr]$main) {
  $i = 0
  foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500

$ev = (Get-GroupChildren $elemTree $TRIGGER "Events")[0]
Click-Node $elemTree $ev
Start-Sleep -Milliseconds 1200
$btns = Get-ParamButtons $main
Write-Output ("事件参数: '" + (Get-WindowTitle $btns[0]) + "'")
Click-Btn $btns[0]
Start-Sleep -Milliseconds 2200
$d = Find-Dialog
Write-Output ("  dialog = '" + (Get-WindowTitle $d) + "'")
Set-DialogInt $d $INTERVAL
Start-Sleep -Milliseconds 1000
Click-Node $elemTree $ev
Start-Sleep -Milliseconds 1000
Write-Output ("  事件: " + (Get-NodeText $elemTree $ev))

Write-Output ("=== 添加动作 '" + $ACTION_SEARCH + "' ===")
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000
$dlg = Find-Dialog
$lv = Find-ListByCtlId $dlg 20
$null = Set-FilterText $dlg $ACTION_SEARCH 1
$cnt = List-Count $lv
for ($i = 0; $i -lt [Math]::Min($cnt, 10); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }
$idx = Find-ListIndexByText $lv $ACTION_SEARCH
if ($idx -lt 0) { Write-Output "找不到"; Click-Btn (Find-Child $dlg "Button\|Cancel"); return }
Set-ListSel $lv $idx
Start-Sleep -Milliseconds 700
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2500

Write-Output "=== 动作 ==="
foreach ($a in (Get-GroupChildren $elemTree $TRIGGER "Actions")) { Write-Output ("    " + (Get-NodeText $elemTree $a)) }
Write-Output "=== 参数 ==="
Show-Row $main
