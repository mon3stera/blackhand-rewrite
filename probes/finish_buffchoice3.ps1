# Rename the leftover "Untitled Variable 001" to BuffShown, then wire the guard
# condition into BuffChoice and relabel button 2.

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

function Find-VarNode([IntPtr]$tree, [string]$name) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -like ("*" + $name + "*")) { return $cur }
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

function Get-SentenceButtons([IntPtr]$dlg) {
  $res = @()
  foreach ($k in [SC2]::KidsAll($dlg)) {
    if ($k -match "\|Button\|") {
      $h = [IntPtr][int64]($k.Split("|")[0])
      $r = (Get-RectStr $h).Split(",")
      if ([int]$r[1] -ge 570 -and [int]$r[1] -lt 625) { $res += ,@($h, (Get-WindowTitle $h)) }
    }
  }
  return $res
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Write-Output "=== 1) 重命名变量 ==="
$v = Find-VarNode $listTree "Untitled Variable"
if ($v -ne [IntPtr]::Zero) {
  Click-Node $listTree $v
  Start-Sleep -Milliseconds 1500
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]83, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 1500
  $edit = [IntPtr]::Zero
  foreach ($k in [SC2]::KidsAll($main)) {
    if ($k -match "\|Edit\|") {
      $h = [IntPtr][int64]($k.Split("|")[0])
      $t = Read-ControlText $h 128
      Write-Output ("  edit " + $k + " text=[" + $t + "]")
      if ($t -match "Untitled Variable|Variable") { $edit = $h }
    }
  }
  if ($edit -eq [IntPtr]::Zero) { Write-Output "  !! 找不到重命名编辑框" }
  else {
    Set-EditText $edit "BuffShown"
    Start-Sleep -Milliseconds 700
    [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)
    [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
    Start-Sleep -Milliseconds 1500
  }
} else {
  Write-Output "  没有 Untitled Variable"
}
Write-Output ("  现在: " + (Get-NodeText $listTree (Find-VarNode $listTree "BuffShown")))

Write-Output "=== 2) BuffChoice 条件 BuffShown == 0 ==="
Click-Node $listTree (Find-TriggerNode $listTree "BuffChoice")
Start-Sleep -Milliseconds 1500
Click-Node $elemTree (Get-GroupNode $elemTree "BuffChoice" "Conditions")
Start-Sleep -Milliseconds 1100
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]582, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000
$dlg = Find-Dialog
Write-Output ("  dialog = '" + (Get-WindowTitle $dlg) + "'")
$lv = Find-ListByCtlId $dlg 147
Set-ListSel $lv (Find-ListIndexByText $lv "Comparison")
Start-Sleep -Milliseconds 1500

$btns = Get-SentenceButtons $dlg
Click-Btn $btns[0][0]
Start-Sleep -Milliseconds 2200
$d2 = Find-Dialog
Write-Output ("  左槽 dialog = '" + (Get-WindowTitle $d2) + "'")
$vb = Find-Child $d2 "Button\|&Variable"
if ($vb -ne [IntPtr]::Zero) { Click-Btn $vb; Start-Sleep -Milliseconds 1800 }
Set-DialogVariable $d2 "BuffShown"
Start-Sleep -Milliseconds 1000

$btns = Get-SentenceButtons $dlg
foreach ($x in $btns) { Write-Output ("    '" + $x[1] + "'") }
$right = [IntPtr]::Zero
for ($i = 0; $i -lt $btns.Count; $i++) {
  if ($btns[$i][1] -eq "==" -and ($i + 1) -lt $btns.Count) { $right = $btns[$i + 1][0]; break }
}
if ($right -ne [IntPtr]::Zero) {
  Click-Btn $right
  Start-Sleep -Milliseconds 2200
  Set-DialogInt (Find-Dialog) "0"
  Start-Sleep -Milliseconds 1000
}
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2500
foreach ($c in (Get-GroupChildren $elemTree "BuffChoice" "Conditions")) { Write-Output ("  条件: " + (Get-NodeText $elemTree $c)) }

Write-Output "=== 3) 末尾加 Set BuffShown = 1 ==="
$acts = Get-GroupChildren $elemTree "BuffChoice" "Actions"
Click-Node $elemTree $acts[$acts.Count - 1]
Start-Sleep -Milliseconds 1100
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000
$dlg = Find-Dialog
if (-not (Select-ListItemByText $dlg "Set Variable" 20 19)) {
  Write-Output "  !! 找不到 Set Variable"
  Click-Btn (Find-Child $dlg "Button\|Cancel")
} else {
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2200
  $acts = Get-GroupChildren $elemTree "BuffChoice" "Actions"
  $node = $acts[$acts.Count - 1]
  Click-Node $elemTree $node
  Start-Sleep -Milliseconds 1100
  $pb = Get-ParamButtons $main
  Write-Output ("  参数: " + (($pb | ForEach-Object { Get-WindowTitle $_ }) -join " | "))
  Click-Btn $pb[0]
  Start-Sleep -Milliseconds 1800
  $d3 = Find-Dialog
  if ((Get-WindowTitle $d3) -ne "Any Variable") {
    $vb = Find-Child $d3 "Button\|&Variable"
    if ($vb -ne [IntPtr]::Zero) { Click-Btn $vb; Start-Sleep -Milliseconds 1600 }
  }
  Set-DialogVariable $d3 "BuffShown"
  Start-Sleep -Milliseconds 1000
  $pb = Get-ParamButtons $main
  Click-Btn $pb[1]
  Start-Sleep -Milliseconds 1800
  Set-DialogInt (Find-Dialog) "1"
  Start-Sleep -Milliseconds 1000
  Write-Output ("  动作: " + (Get-NodeText $elemTree $node))
}

Write-Output "=== 4) 按钮2 文字 医疗兵 -> 重装 ==="
Click-Node $listTree (Find-TriggerNode $listTree "BuffChoice")
Start-Sleep -Milliseconds 1400
$btnAction = (Get-GroupChildren $elemTree "BuffChoice" "Actions")[4]
Click-Node $elemTree $btnAction
Start-Sleep -Milliseconds 1100
$pb = Get-ParamButtons $main
Click-Btn $pb[7]
Start-Sleep -Milliseconds 1800
Set-DialogText (Find-Dialog) "重装"
Start-Sleep -Milliseconds 1000
Write-Output ("  动作: " + (Get-NodeText $elemTree $btnAction))

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
