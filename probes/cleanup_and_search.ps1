# 1) delete the broken Buff1/2/3 triggers
# 2) inspect the Dialog Item parameter dialog of a fresh event
# 3) list actions matching "Create Units"

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

Write-Output "=== 删除 Buff1/2/3 ==="
foreach ($n in @("Buff1", "Buff2", "Buff3")) {
  $node = Find-TriggerNode $listTree $n
  if ($node -eq [IntPtr]::Zero) { continue }
  Click-Node $listTree $node
  Start-Sleep -Milliseconds 900
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 1500
  Write-Output ("  已删除 " + $n)
}

Write-Output "=== 剩余 ==="
$cur = Get-Root $listTree
while ($cur -ne [IntPtr]::Zero) { Write-Output ("  " + (Get-NodeText $listTree $cur)); $cur = Get-Next $listTree $cur }

Write-Output "=== 动作列表: Create Units ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000
$dlg = Find-Dialog
$lv = Find-ListByCtlId $dlg 20
$null = Set-FilterText $dlg "Create Units" 1
$cnt = List-Count $lv
for ($i = 0; $i -lt [Math]::Min($cnt, 15); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }
Click-Btn (Find-Child $dlg "Button\|Cancel")
Start-Sleep -Milliseconds 1000
