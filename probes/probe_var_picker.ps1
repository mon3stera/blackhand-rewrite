# Why is the Dialog Item variable picker empty?  Open it, then poke the filter box
# and the type combo.

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

Click-Node $listTree (Find-TriggerNode $listTree "Buff1")
Start-Sleep -Milliseconds 1500
$ev = (Get-GroupChildren $elemTree "Buff1" "Events")[0]
Click-Node $elemTree $ev
Start-Sleep -Milliseconds 1200
$btns = Get-ParamButtons $main
Click-Btn $btns[0]
Start-Sleep -Milliseconds 2200
$d = Find-Dialog
Click-Btn (Find-Child $d "Button\|&Variable")
Start-Sleep -Milliseconds 2000

$lv = Find-ListByCtlId $d 67
$edit = Find-ChildAll $d "Edit\|.*\|id=66"
Write-Output ("lv = " + $lv + " edit = " + $edit + " count=" + (List-Count $lv))

foreach ($term in @("Buff", "BuffBtn1", "BuffBtn")) {
  Set-EditText $edit ""
  Start-Sleep -Milliseconds 500
  Set-EditText $edit $term -Nudge
  Start-Sleep -Milliseconds 1500
  $cnt = List-Count $lv
  Write-Output ("--- 过滤 [" + $term + "] -> " + $cnt)
  for ($i = 0; $i -lt [Math]::Min($cnt, 8); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }
}

Write-Output "=== 类别列表 63 ==="
$cat = Find-ListByCtlId $d 63
Write-Output ("count=" + (List-Count $cat))
for ($i = 0; $i -lt (List-Count $cat); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $cat $i)) }

Write-Output "=== 类型下拉 15 ==="
$null = Read-ComboUIA (Find-ChildAll $d "ComboBox\|.*\|id=15")

$cancel = Find-Child $d "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
