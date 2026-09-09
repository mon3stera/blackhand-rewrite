# BuffChoice: fire exactly once.
#   - new global Integer variable BuffShown
#   - condition BuffShown == 0
#   - last action: Set BuffShown = 1
# Also relabel button 2 from 医疗兵 to 重装.

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

function Set-VarType([IntPtr]$main, [string]$type) {
  $cb = Find-ChildAll $main "ComboBox\|.*\|id=320"
  $r = (Get-RectStr $cb).Split(",")
  $x = [int](([int]$r[0] + [int]$r[2]) / 2)
  $y = [int](([int]$r[1] + [int]$r[3]) / 2)
  $lp = [IntPtr]($x -bor ($y -shl 16))
  [void][SC2]::PostMessage($cb, 0x0201, [IntPtr]1, $lp)
  [void][SC2]::PostMessage($cb, 0x0202, [IntPtr]0, $lp)
  Start-Sleep -Milliseconds 900
  foreach ($ch in $type.ToCharArray()) {
    [void][SC2]::SendMessage($cb, 0x0102, [IntPtr][int]$ch, [IntPtr]1)
    Start-Sleep -Milliseconds 150
  }
  Start-Sleep -Milliseconds 400
  [void][SC2]::SendMessage($cb, 0x0100, [IntPtr]0x0D, [IntPtr]1)
  [void][SC2]::SendMessage($cb, 0x0101, [IntPtr]0x0D, [IntPtr]1)
  Start-Sleep -Milliseconds 1200
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Write-Output "=== 1) 新建变量 BuffShown ==="
if ((Find-VarNode $listTree "BuffShown") -ne [IntPtr]::Zero) {
  Write-Output "  已存在"
} else {
  $sel = Find-VarNode $listTree "KillCount"
  if ($sel -ne [IntPtr]::Zero) { Click-Node $listTree $sel; Start-Sleep -Milliseconds 900 }
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]593, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 2200
  $edit = [IntPtr]::Zero
  foreach ($k in [SC2]::KidsAll($main)) {
    if ($k -match "\|Edit\|") { $edit = [IntPtr][int64]($k.Split("|")[0]) }
  }
  if ($edit -ne [IntPtr]::Zero) {
    Set-EditText $edit "BuffShown"
    Start-Sleep -Milliseconds 500
    [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)
    [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
    Start-Sleep -Milliseconds 1500
  }
  $node = Find-VarNode $listTree "BuffShown"
  if ($node -ne [IntPtr]::Zero) {
    Click-Node $listTree $node
    Start-Sleep -Milliseconds 1500
    Set-VarType $main "Integer"
    Write-Output ("  " + (Get-NodeText $listTree $node))
  }
}

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
if (-not (Select-ListItemByText $dlg "Set Variable" 20 19)) { Write-Output "  !! 找不到 Set Variable"; Click-Btn (Find-Child $dlg "Button\|Cancel") }
else {
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2200
  $acts = Get-GroupChildren $elemTree "BuffChoice" "Actions"
  $node = $acts[$acts.Count - 1]
  Click-Node $elemTree $node
  Start-Sleep -Milliseconds 1100
  $pb = Get-ParamButtons $main
  Write-Output ("  新动作参数: " + (($pb | ForEach-Object { Get-WindowTitle $_ }) -join " | "))
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

Write-Output "=== 4) 改按钮文字 医疗兵 -> 重装 ==="
Click-Node $listTree (Find-TriggerNode $listTree "BuffChoice")
Start-Sleep -Milliseconds 1400
$btnAction = (Get-GroupChildren $elemTree "BuffChoice" "Actions")[4]
Click-Node $elemTree $btnAction
Start-Sleep -Milliseconds 1100
$pb = Get-ParamButtons $main
Write-Output ("  参数: " + (($pb | ForEach-Object { Get-WindowTitle $_ }) -join " | "))
Click-Btn $pb[7]
Start-Sleep -Milliseconds 1800
Set-DialogText (Find-Dialog) "重装"
Start-Sleep -Milliseconds 1000
Write-Output ("  动作: " + (Get-NodeText $elemTree $btnAction))

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
