# Reusable: add an Event (581), Condition (582) or Action (583) to a trigger by
# searching the picker.  Set the variables below before running.

$TRIGGER = "BuffChoice"
$KIND = "Condition"                 # Event | Condition | Action
$SEARCH = "Compare"
$PICK_TEXT = ""                 # exact item text (optional)
$PICK = 0                       # index if PICK_TEXT is empty

$CMD = @{ "Event" = 581; "Condition" = 582; "Action" = 583 }
$NODE_TEXT = @{ "Event" = "Events"; "Condition" = "Conditions"; "Action" = "Actions" }

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
Write-Output "=== 添加前 ==="
Show-Groups $elemTree $TRIGGER

$kids = Get-GroupChildren $elemTree $TRIGGER $NODE_TEXT[$KIND]
if ($kids.Count -gt 0) { Click-Node $elemTree $kids[$kids.Count - 1] } else { Click-Node $elemTree (Get-GroupNode $elemTree $TRIGGER $NODE_TEXT[$KIND]) }
Start-Sleep -Milliseconds 1200

Write-Output ("=== New " + $KIND + ": 搜索 '" + $SEARCH + "' ===")
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]$CMD[$KIND], [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000

$dlg = Find-Dialog
Write-Output ("dialog = '" + (Get-WindowTitle $dlg) + "'")
$lv = Find-ListByCtlId $dlg 20
$null = Set-FilterText $dlg $SEARCH 1
$cnt = List-Count $lv
Write-Output ("matches = " + $cnt)
for ($i = 0; $i -lt [Math]::Min($cnt, 20); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }

if ($PICK_TEXT -ne "") {
  $idx = Find-ListIndexByText $lv $PICK_TEXT
  if ($idx -ge 0) { $PICK = $idx; Write-Output ("按文本定位 -> [" + $idx + "]") }
}
if ($cnt -le $PICK) { Write-Output "结果不足，取消"; Click-Btn (Find-Child $dlg "Button\|Cancel"); return }

Set-ListSel $lv $PICK
Start-Sleep -Milliseconds 800
Write-Output ("选中: " + (Read-ListItem $lv $PICK))
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2500

Write-Output "=== 添加后 ==="
Show-Groups $elemTree $TRIGGER
Write-Output "=== 参数 ==="
$i = 0
foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
