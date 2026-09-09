# Insert a Set Variable action after a chosen action, bind the variable, and
# explore what value-functions the target type offers.

$TRIGGER = "BuffChoice"
$AFTER_INDEX = 0
$VAR = "BuffDialog"
$FUNC_SEARCH = "Last Created"

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

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500

$acts = Get-GroupChildren $elemTree $TRIGGER "Actions"
Click-Node $elemTree $acts[$AFTER_INDEX]
Start-Sleep -Milliseconds 1200

Write-Output "=== 添加 Set Variable ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000
$dlg = Find-Dialog
$lv = Find-ListByCtlId $dlg 20
$null = Set-FilterText $dlg "Set Variable" 1
$idx = Find-ListIndexByText $lv "Set Variable"
Set-ListSel $lv $idx
Start-Sleep -Milliseconds 700
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2500

Show-Actions $elemTree $TRIGGER

$acts = Get-GroupChildren $elemTree $TRIGGER "Actions"
$node = $acts[$AFTER_INDEX + 1]
Click-Node $elemTree $node
Start-Sleep -Milliseconds 1300
$btns = Get-ParamButtons $main
Write-Output "=== 新动作参数 ==="
$i = 0
foreach ($b in $btns) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }

Write-Output ("=== 点击 param[0] 选变量 " + $VAR + " ===")
Click-Btn $btns[0]
Start-Sleep -Milliseconds 2200
$d = Find-Dialog
Write-Output ("dialog = '" + (Get-WindowTitle $d) + "'")
Set-DialogVariable $d $VAR
Start-Sleep -Milliseconds 1200

Click-Node $elemTree $node
Start-Sleep -Milliseconds 1200
$btns = Get-ParamButtons $main
Write-Output "=== 变量后参数 ==="
$i = 0
foreach ($b in $btns) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }

if ($btns.Count -ge 2) {
  Write-Output ("=== 点击 param[1] 看函数 ===")
  Click-Btn $btns[1]
  Start-Sleep -Milliseconds 2200
  $d = Find-Dialog
  Write-Output ("dialog = '" + (Get-WindowTitle $d) + "'")
  Click-Btn (Find-Child $d "Button\|&Function")
  Start-Sleep -Milliseconds 2200
  $flv = Find-ListByCtlId $d 43
  $find = Find-ChildAll $d "Edit\|.*\|id=42"
  $null = Set-FilterText $d $FUNC_SEARCH 0
  Start-Sleep -Milliseconds 600
  $fcnt = List-Count $flv
  Write-Output ("函数匹配 = " + $fcnt)
  for ($k = 0; $k -lt [Math]::Min($fcnt, 15); $k++) { Write-Output ("    [" + $k + "] " + (Read-ListItem $flv $k)) }
  $cancel = Find-Child $d "Button\|Cancel"
  if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
}
