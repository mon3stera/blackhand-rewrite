# Probe: click a parameter button of the selected action and dump whatever dialog
# opens, so we can learn how to pick a variable.

$TRIGGER = "Untitled Trigger 004"
$ACTION_INDEX = 0
$PARAM_INDEX = 0

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

$acts = Get-ActionNodes $elemTree $TRIGGER
Click-Node $elemTree $acts[$ACTION_INDEX]
Start-Sleep -Milliseconds 1500

$btns = Get-ParamButtons $main
$i = 0
foreach ($b in $btns) { Write-Output ("  param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }

Write-Output ("=== 点击 param[" + $PARAM_INDEX + "] ===")
Click-Btn $btns[$PARAM_INDEX]
Start-Sleep -Milliseconds 2500

$dlg = Find-Dialog
Write-Output ("dialog = " + $dlg + "  title='" + (Get-WindowTitle $dlg) + "'")

# text param: only dump, no auto-commit
Start-Sleep -Milliseconds 1500
Write-Output ("dialog now = " + (Find-Dialog))

Write-Output "=== 参数行 ==="
$i = 0
foreach ($b in (Get-ParamButtons $main)) { Write-Output ("  param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
Write-Output "=== 动作 ==="
foreach ($a in (Get-ActionNodes $elemTree $TRIGGER)) { Write-Output ("    " + (Get-NodeText $elemTree $a)) }

$cancel = Find-Child $dlg "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
Start-Sleep -Milliseconds 800
