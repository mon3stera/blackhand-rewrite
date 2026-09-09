# Repair pass:
#   1) rename "Untitled Variable 001" -> BuffShown (match the inline edit by title)
#   2) delete the bogus BuffChoice condition and add BuffShown == 0
#   3) configure the "Set Variable = Value" action at the end of BuffChoice

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

function Pick-Variable([IntPtr]$dlg, [string]$name) {
  if ((Get-WindowTitle $dlg) -ne "Any Variable") {
    $vb = Find-Child $dlg "Button\|&Variable"
    if ($vb -ne [IntPtr]::Zero) { Click-Btn $vb; Start-Sleep -Milliseconds 1800 }
  }
  Set-DialogVariable $dlg $name
  Start-Sleep -Milliseconds 1000
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
      $t = Get-WindowTitle $h
      if ($t -match "Untitled Variable") { $edit = $h; Write-Output ("  edit " + $k) }
    }
  }
  if ($edit -ne [IntPtr]::Zero) {
    Set-EditText $edit "BuffShown"
    Start-Sleep -Milliseconds 700
    [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)
    [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
    Start-Sleep -Milliseconds 1500
  } else { Write-Output "  !! 没有找到内联编辑框" }
}
$bs = Find-VarNode $listTree "BuffShown"
if ($bs -ne [IntPtr]::Zero) { Write-Output ("  现在: " + (Get-NodeText $listTree $bs)) } else { Write-Output "  !! 变量仍是未命名" }

Write-Output "=== 2) 删除错误条件 ==="
Click-Node $listTree (Find-TriggerNode $listTree "BuffChoice")
Start-Sleep -Milliseconds 1400
$conds = Get-GroupChildren $elemTree "BuffChoice" "Conditions"
foreach ($c in $conds) {
  Write-Output ("  删除: " + (Get-NodeText $elemTree $c))
  Click-Node $elemTree $c
  Start-Sleep -Milliseconds 900
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 1400
}
$conds = Get-GroupChildren $elemTree "BuffChoice" "Conditions"
Write-Output ("  剩余条件数: " + $conds.Count)

if ($conds.Count -eq 0) {
  Write-Output "=== 2b) 添加条件 BuffShown == 0 ==="
  Click-Node $elemTree (Get-GroupNode $elemTree "BuffChoice" "Conditions")
  Start-Sleep -Milliseconds 1100
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]582, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 3000
  $dlg = Find-Dialog
  $lv = Find-ListByCtlId $dlg 147
  Set-ListSel $lv (Find-ListIndexByText $lv "Comparison")
  Start-Sleep -Milliseconds 1500
  $btns = Get-SentenceButtons $dlg
  Click-Btn $btns[0][0]
  Start-Sleep -Milliseconds 2200
  Pick-Variable (Find-Dialog) "BuffShown"
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
}

Write-Output "=== 3) 配置 Set Variable 动作 ==="
Click-Node $listTree (Find-TriggerNode $listTree "BuffChoice")
Start-Sleep -Milliseconds 1400
$acts = Get-GroupChildren $elemTree "BuffChoice" "Actions"
$node = $acts[$acts.Count - 1]
Write-Output ("  最后一个动作: " + (Get-NodeText $elemTree $node))
Click-Node $elemTree $node
Start-Sleep -Milliseconds 1100
$pb = Get-ParamButtons $main
Write-Output ("  参数: " + (($pb | ForEach-Object { Get-WindowTitle $_ }) -join " | "))
Click-Btn $pb[0]
Start-Sleep -Milliseconds 1800
Pick-Variable (Find-Dialog) "BuffShown"
$pb = Get-ParamButtons $main
Click-Btn $pb[1]
Start-Sleep -Milliseconds 1800
Set-DialogInt (Find-Dialog) "1"
Start-Sleep -Milliseconds 1000
Write-Output ("  动作: " + (Get-NodeText $elemTree $node))

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
