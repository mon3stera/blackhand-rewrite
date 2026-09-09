# Rebuild BuffChoice's action list in order:
#   Create Dialog -> 3x Create Dialog Item (Button) -> Show/Hide Dialog

$TRIGGER = "BuffChoice"
$ACTIONS = @(
  "Create Dialog",
  "Create Dialog Item (Button)",
  "Create Dialog Item (Button)",
  "Create Dialog Item (Button)",
  "Show/Hide Dialog"
)

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

function Show-Actions([IntPtr]$tree, [string]$trigger) {
  $i = 0
  foreach ($a in (Get-GroupChildren $tree $trigger "Actions")) { Write-Output ("    [" + $i + "] " + (Get-NodeText $tree $a)); $i++ }
}

function Add-Action([string]$search) {
  $acts = Get-GroupChildren $elemTree $TRIGGER "Actions"
  if ($acts.Count -gt 0) { Click-Node $elemTree $acts[$acts.Count - 1] } else { Click-Node $elemTree (Get-GroupNode $elemTree $TRIGGER "Actions") }
  Start-Sleep -Milliseconds 1200
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 3000
  $dlg = Find-Dialog
  $lv = Find-ListByCtlId $dlg 20
  $null = Set-FilterText $dlg $search 1
  $idx = Find-ListIndexByText $lv $search
  if ($idx -lt 0) {
    Write-Output ("  !! 找不到动作: " + $search)
    Click-Btn (Find-Child $dlg "Button\|Cancel")
    Start-Sleep -Milliseconds 800
    return
  }
  Set-ListSel $lv $idx
  Start-Sleep -Milliseconds 700
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2200
  Write-Output ("  已添加: " + $search)
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500

Write-Output "=== 清空动作 ==="
$guard = 0
while ($guard -lt 20) {
  $acts = Get-GroupChildren $elemTree $TRIGGER "Actions"
  if ($acts.Count -eq 0) { break }
  Click-Node $elemTree $acts[0]
  Start-Sleep -Milliseconds 800
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 1300
  $guard++
}
Show-Actions $elemTree $TRIGGER

Write-Output "=== 按顺序添加 ==="
foreach ($a in $ACTIONS) { Add-Action $a }

Write-Output "=== 结果 ==="
Show-Actions $elemTree $TRIGGER

Write-Output "=== 各动作参数 ==="
$i = 0
foreach ($node in (Get-GroupChildren $elemTree $TRIGGER "Actions")) {
  Click-Node $elemTree $node
  Start-Sleep -Milliseconds 1200
  Write-Output ("  [" + $i + "] " + (Get-NodeText $elemTree $node))
  $j = 0
  foreach ($b in (Get-ParamButtons $main)) { Write-Output ("      param[" + $j + "] '" + (Get-WindowTitle $b) + "'"); $j++ }
  $i++
}

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
