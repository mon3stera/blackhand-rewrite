# Inspect the Real parameter dialog of Point From XY (param 4 of trigger 003's
# create-units action) and list functions matching "Random".

$TRIGGER = "Untitled Trigger 003"
$ACTION_INDEX = 1
$PARAM_INDEX = 4
$SEARCH = "Random"

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

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
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
Write-Output ("dialog = '" + (Get-WindowTitle $dlg) + "'")

Click-Btn (Find-Child $dlg "Button\|&Function")
Start-Sleep -Milliseconds 2200

$lv = Find-ListByCtlId $dlg 43
$find = Find-ChildAll $dlg "Edit\|.*\|id=42"
Write-Output ("lv = " + $lv + " find = " + $find)

foreach ($term in @($SEARCH, "Random Integer")) {
  Set-EditText $find $term -Nudge
  Start-Sleep -Milliseconds 1800
  $cnt = List-Count $lv
  Write-Output ("--- [" + $term + "] matches = " + $cnt)
  for ($i = 0; $i -lt [Math]::Min($cnt, 20); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }
}

$cancel = Find-Child $dlg "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
Start-Sleep -Milliseconds 800
