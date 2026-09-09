# Fill triggers 003 (periodic spawn) and 004 (kill notice) using the verified
# value-dialog writers, then report the resulting action texts.
#
#   003: Event Periodic 5s
#        action 0  Text Message        -> "spawn"
#        action 1  Create Units        -> 1 Zergling for player 2 at (Start location of player 2),
#                                         facing (Start location of player 1)
#   004: Event Any Unit Dies
#        action 0  Text Message        -> "unit died"

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

function Open-Param([IntPtr]$elemTree, [IntPtr]$action, [int]$idx, [string]$label) {
  # diagnostics must use Write-Host: Write-Output would pollute the return value
  Click-Node $elemTree $action
  Start-Sleep -Milliseconds 1500
  $btns = Get-ParamButtons (Find-Main)
  Write-Host ("  -> 打开参数[" + $idx + "] " + $label + " (按钮 " + $btns[$idx] + ")")
  Click-Btn $btns[$idx]
  Start-Sleep -Milliseconds 2500
  return (Find-Dialog)
}

function Report-Actions([IntPtr]$elemTree, [string]$name) {
  foreach ($a in Get-ActionNodes $elemTree $name) { Write-Output ("    ACTION: " + (Get-NodeText $elemTree $a)) }
}

Write-Output "########## Untitled Trigger 003 ##########"
Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 003")
Start-Sleep -Milliseconds 1500
$acts = Get-ActionNodes $elemTree "Untitled Trigger 003"

# --- Text Message: text ---
$dlg = Open-Param $elemTree $acts[0] 0 "Text Message / 文本"
if ($dlg -ne [IntPtr]::Zero) { Write-Output ("    dialog = " + $dlg + " '" + (Get-WindowTitle $dlg) + "'"); Set-DialogText $dlg "spawn" }

# --- Create Units: unit type / player / point / facing ---
$acts = Get-ActionNodes $elemTree "Untitled Trigger 003"
$cu = $acts[1]

$dlg = Open-Param $elemTree $cu 1 "单位类型"
if ($dlg -ne [IntPtr]::Zero) { Write-Output ("    dialog = " + $dlg + " '" + (Get-WindowTitle $dlg) + "'"); [void](Set-DialogGameLink $dlg "Zergling") }

$dlg = Open-Param $elemTree $cu 2 "玩家"
if ($dlg -ne [IntPtr]::Zero) { Write-Output ("    dialog = " + $dlg + " '" + (Get-WindowTitle $dlg) + "'"); Set-DialogInt $dlg "2" }

$dlg = Open-Param $elemTree $cu 3 "点"
if ($dlg -ne [IntPtr]::Zero) { Write-Output ("    dialog = " + $dlg + " '" + (Get-WindowTitle $dlg) + "'"); [void](Set-DialogPointFunc $dlg "Start Location Of Player" "Start Location") }

$acts = Get-ActionNodes $elemTree "Untitled Trigger 003"
$btns = Get-ParamButtons $main
Write-Output ("    当前参数按钮数 = " + $btns.Count)
foreach ($k in [SC2]::Kids($main)) { if ($k -match "\|Button\|") { Write-Output ("      " + $k) } }

# facing: its expression renders as "(" followed by the nested unit argument
# ("Triggering unit"), which is how we locate it after the row re-lays out.
Click-Node $elemTree $cu
Start-Sleep -Milliseconds 1500
$btns = Get-ParamButtons $main
$faceIdx = -1
for ($i = 0; $i -lt $btns.Count - 1; $i++) {
  if ((Get-WindowTitle $btns[$i]) -eq "(" -and (Get-WindowTitle $btns[$i + 1]) -eq "Triggering unit") { $faceIdx = $i }
}
Write-Output ("    朝向参数按钮索引 = " + $faceIdx)
if ($faceIdx -ge 0) {
  Click-Btn $btns[$faceIdx]
  Start-Sleep -Milliseconds 2500
  $dlg = Find-Dialog
  if ($dlg -ne [IntPtr]::Zero) { Write-Output ("    dialog = " + $dlg + " '" + (Get-WindowTitle $dlg) + "'"); [void](Set-DialogPointFunc $dlg "Start Location Of Player" "Start Location") }
}

Report-Actions $elemTree "Untitled Trigger 003"

Write-Output "########## Untitled Trigger 004 ##########"
Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 004")
Start-Sleep -Milliseconds 1500
$acts4 = Get-ActionNodes $elemTree "Untitled Trigger 004"
$dlg = Open-Param $elemTree $acts4[0] 0 "Text Message / 文本"
if ($dlg -ne [IntPtr]::Zero) { Write-Output ("    dialog = " + $dlg + " '" + (Get-WindowTitle $dlg) + "'"); Set-DialogText $dlg "unit died" }

Report-Actions $elemTree "Untitled Trigger 004"
Write-Output "done"
