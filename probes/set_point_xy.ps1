# Set every point-valued parameter of an action to "Point From XY" with fixed
# coordinates, filling the two numeric arguments too.
#
# The parameter row renders a function value as "(" followed by its arguments, so
# the Nth "(" button identifies the Nth point-valued parameter of the action.

$TRIGGER = "Untitled Trigger 002"
$ACTION_INDEX = 1
$COORD = "64"

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

function Get-ActionNodes([IntPtr]$tree, [string]$name) {
  $t = Find-TriggerNode $tree $name
  if ($t -eq [IntPtr]::Zero) { return @() }
  $c = Get-Child $tree $t
  while ($c -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $c) -eq "Actions") {
      $res = @(); $a = Get-Child $tree $c
      while ($a -ne [IntPtr]::Zero) { $res += $a; $a = Get-Next $tree $a }
      return $res
    }
    $c = Get-Next $tree $c
  }
  return @()
}

function Get-ParenIndexes([IntPtr]$main) {
  $btns = Get-ParamButtons $main
  $res = @()
  for ($i = 0; $i -lt $btns.Count; $i++) { if ((Get-WindowTitle $btns[$i]) -eq "(") { $res += $i } }
  return ,$res
}

function Show-Row([IntPtr]$main, [string]$label) {
  Write-Output ("--- " + $label + " ---")
  $i = 0
  foreach ($b in (Get-ParamButtons $main)) { Write-Output ("   [" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
}

function Set-PointParamToXY([IntPtr]$elemTree, [IntPtr]$action, [int]$parenIndex) {
  Click-Node $elemTree $action
  Start-Sleep -Milliseconds 1500
  $parens = Get-ParenIndexes $main
  Write-Output ("    parens = " + ($parens -join ",") + "  -> 目标 parenIndex " + $parenIndex)
  if ($parenIndex -ge $parens.Count) { Write-Output "    没有这个点参数"; return }
  $btns = Get-ParamButtons $main
  Click-Btn $btns[$parens[$parenIndex]]
  Start-Sleep -Milliseconds 2500
  $dlg = Find-Dialog
  if ($dlg -eq [IntPtr]::Zero) { Write-Output "    没有对话框"; return }
  Write-Output ("    dialog = '" + (Get-WindowTitle $dlg) + "'")
  [void](Set-DialogPointFunc $dlg "Point From XY" "Point From")
  Start-Sleep -Milliseconds 1200

  # fill the two numeric arguments that appeared between this "(" and the next one
  for ($n = 0; $n -lt 4; $n++) {
    Click-Node $elemTree $action
    Start-Sleep -Milliseconds 1200
    $btns = Get-ParamButtons $main
    $parens = Get-ParenIndexes $main
    if ($parenIndex -ge $parens.Count) { break }
    $start = $parens[$parenIndex] + 1
    $end = if ($parens.Count -gt $parenIndex + 1) { $parens[$parenIndex + 1] - 1 } else { $btns.Count - 1 }
    $target = -1
    for ($k = $start; $k -le $end; $k++) {
      # Real parameters render as "64.0", so match by prefix rather than equality
      if ((Get-WindowTitle $btns[$k]) -notlike ($COORD + "*")) { $target = $k; break }
    }
    if ($target -lt 0) { break }
    Write-Output ("    设置参数 [" + $target + "] (原值 '" + (Get-WindowTitle $btns[$target]) + "') -> " + $COORD)
    Click-Btn $btns[$target]
    Start-Sleep -Milliseconds 2200
    $dlg = Find-Dialog
    if ($dlg -eq [IntPtr]::Zero) { Write-Output "    没有对话框"; break }
    Write-Output ("    dialog = '" + (Get-WindowTitle $dlg) + "'")
    Set-DialogInt $dlg $COORD
  }
}

foreach ($target in @(@($TRIGGER, $ACTION_INDEX), @("Untitled Trigger 003", 1))) {
  $tname = $target[0]; $aidx = $target[1]
  Write-Output ("########## " + $tname + " 动作[" + $aidx + "] ##########")
  Click-Node $listTree (Find-TriggerNode $listTree $tname)
  Start-Sleep -Milliseconds 1500
  $acts = Get-ActionNodes $elemTree $tname
  $action = $acts[$aidx]
  Click-Node $elemTree $action
  Start-Sleep -Milliseconds 1800
  Show-Row $main "初始"

  Set-PointParamToXY $elemTree $action 0
  Set-PointParamToXY $elemTree $action 1

  Click-Node $elemTree $action
  Start-Sleep -Milliseconds 1500
  Show-Row $main "完成"
  foreach ($a in Get-ActionNodes $elemTree $tname) { Write-Output ("ACTION: " + (Get-NodeText $elemTree $a)) }
}

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
