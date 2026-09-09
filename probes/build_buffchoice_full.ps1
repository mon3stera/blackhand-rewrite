# Rebuild BuffChoice fully:
#   Create Dialog -> Set BuffDialog -> 3x (Create Button -> Set BuffBtnN) -> Show

$TRIGGER = "BuffChoice"

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
  Start-Sleep -Milliseconds 2800
  $dlg = Find-Dialog
  $lv = Find-ListByCtlId $dlg 20
  $null = Set-FilterText $dlg $search 1
  $idx = Find-ListIndexByText $lv $search
  if ($idx -lt 0) { Write-Output ("  !! 找不到: " + $search); Click-Btn (Find-Child $dlg "Button\|Cancel"); Start-Sleep -Milliseconds 800; return }
  Set-ListSel $lv $idx
  Start-Sleep -Milliseconds 600
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2000
}

function Node-At([int]$i) { return (Get-GroupChildren $elemTree $TRIGGER "Actions")[$i] }

function Set-ParamVar([IntPtr]$node, [int]$pi, [string]$var) {
  Click-Node $elemTree $node
  Start-Sleep -Milliseconds 1100
  $btns = Get-ParamButtons $main
  Click-Btn $btns[$pi]
  Start-Sleep -Milliseconds 2000
  $d = Find-Dialog
  # a plain "Any Variable" dialog goes straight to the picker; a typed dialog
  # (e.g. "Dialog") needs the &Variable mode first
  if ((Get-WindowTitle $d) -ne "Any Variable") {
    $vb = Find-Child $d "Button\|&Variable"
    if ($vb -ne [IntPtr]::Zero) { Click-Btn $vb; Start-Sleep -Milliseconds 1500 }
  }
  Set-DialogVariable $d $var
  Start-Sleep -Milliseconds 1000
}

function Set-ParamFunc([IntPtr]$node, [int]$pi, [string]$func) {
  Click-Node $elemTree $node
  Start-Sleep -Milliseconds 1100
  $btns = Get-ParamButtons $main
  Click-Btn $btns[$pi]
  Start-Sleep -Milliseconds 2000
  $d = Find-Dialog
  Click-Btn (Find-Child $d "Button\|&Function")
  Start-Sleep -Milliseconds 2000
  $lv = Filter-List $d 43 42 $func
  $idx = Find-ListIndexByText $lv $func
  if ($idx -lt 0) { Write-Output ("  !! 找不到函数: " + $func); Click-Btn (Find-Child $d "Button\|Cancel"); return }
  Set-ListSel $lv $idx
  Start-Sleep -Milliseconds 600
  Click-Btn (Find-Child $d "Button\|&OK")
  Start-Sleep -Milliseconds 2000
}

function Set-ParamText([IntPtr]$node, [int]$pi, [string]$text) {
  Click-Node $elemTree $node
  Start-Sleep -Milliseconds 1100
  $btns = Get-ParamButtons $main
  Click-Btn $btns[$pi]
  Start-Sleep -Milliseconds 2000
  $d = Find-Dialog
  Set-DialogText $d $text
  Start-Sleep -Milliseconds 1000
}

function Set-ParamInt([IntPtr]$node, [int]$pi, [string]$val) {
  Click-Node $elemTree $node
  Start-Sleep -Milliseconds 1100
  $btns = Get-ParamButtons $main
  Click-Btn $btns[$pi]
  Start-Sleep -Milliseconds 2000
  $d = Find-Dialog
  Set-DialogInt $d $val
  Start-Sleep -Milliseconds 1000
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500

Write-Output "=== 清空 ==="
$guard = 0
while ($guard -lt 25) {
  $acts = Get-GroupChildren $elemTree $TRIGGER "Actions"
  if ($acts.Count -eq 0) { break }
  Click-Node $elemTree $acts[0]
  Start-Sleep -Milliseconds 800
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 1200
  $guard++
}

Write-Output "=== 添加动作 ==="
Add-Action "Create Dialog"
Add-Action "Set Variable"
Add-Action "Create Dialog Item (Button)"
Add-Action "Set Variable"
Add-Action "Create Dialog Item (Button)"
Add-Action "Set Variable"
Add-Action "Create Dialog Item (Button)"
Add-Action "Set Variable"
Add-Action "Show/Hide Dialog"
Show-Actions $elemTree $TRIGGER

Write-Output "=== 配置参数 ==="
# 1: BuffDialog = Last Created Dialog
Set-ParamVar (Node-At 1) 0 "BuffDialog"
Set-ParamFunc (Node-At 1) 1 "Last Created Dialog"

$labels = @("增援", "医疗兵", "精英")
$ys = @("50", "120", "190")
for ($k = 0; $k -lt 3; $k++) {
  $btnAction = 2 + $k * 2
  $setAction = $btnAction + 1
  Write-Output ("--- 按钮 " + $k + " (" + $labels[$k] + ") ---")
  Set-ParamVar (Node-At $btnAction) 0 "BuffDialog"
  Set-ParamText (Node-At $btnAction) 7 $labels[$k]
  Set-ParamInt (Node-At $btnAction) 5 $ys[$k]
  Set-ParamVar (Node-At $setAction) 0 ("BuffBtn" + ($k + 1))
  Set-ParamFunc (Node-At $setAction) 1 "Last Created Dialog Item"
}

Write-Output "=== 显示动作 ==="
Set-ParamVar (Node-At 8) 1 "BuffDialog"

Write-Output "=== 结果 ==="
Show-Actions $elemTree $TRIGGER

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
