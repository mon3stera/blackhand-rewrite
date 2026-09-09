# Replace BuffChoice's event with a periodic event (every 25 s).

$TRIGGER = "BuffChoice"
$SECONDS = "25"

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

function Show-Groups([IntPtr]$tree, [string]$trigger) {
  foreach ($g in @("Events", "Conditions", "Actions")) {
    Write-Output ("  " + $g + ":")
    foreach ($n in (Get-GroupChildren $tree $trigger $g)) { Write-Output ("    " + (Get-NodeText $tree $n)) }
  }
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
Write-Output "=== 前 ==="
Show-Groups $elemTree $TRIGGER

foreach ($ev in (Get-GroupChildren $elemTree $TRIGGER "Events")) {
  Write-Output ("删除事件: " + (Get-NodeText $elemTree $ev))
  Click-Node $elemTree $ev
  Start-Sleep -Milliseconds 900
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 1500
}

Click-Node $elemTree (Get-GroupNode $elemTree $TRIGGER "Events")
Start-Sleep -Milliseconds 1200
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]581, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000

$dlg = Find-Dialog
Write-Output ("dialog = '" + (Get-WindowTitle $dlg) + "'")
$lv = Find-ListByCtlId $dlg 20
$null = Set-FilterText $dlg "Periodic" 1
$cnt = List-Count $lv
Write-Output ("matches = " + $cnt)
for ($i = 0; $i -lt [Math]::Min($cnt, 10); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }

$idx = Find-ListIndexByText $lv "Periodic Event"
if ($idx -lt 0) { Write-Output "找不到 Periodic Event"; Click-Btn (Find-Child $dlg "Button\|Cancel"); return }
Set-ListSel $lv $idx
Start-Sleep -Milliseconds 700
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2500

Write-Output "=== 后 ==="
Show-Groups $elemTree $TRIGGER
Write-Output "=== 参数 ==="
$i = 0
foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
