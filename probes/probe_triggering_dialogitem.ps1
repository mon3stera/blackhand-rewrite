# In the Comparison sentence, open the left slot and look for the
# "Triggering Dialog Item" function.

$TRIGGER = "Buff1"

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

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
Click-Node $elemTree (Get-GroupNode $elemTree $TRIGGER "Conditions")
Start-Sleep -Milliseconds 1200

[void][SC2]::SendMessage($main, 0x0111, [IntPtr]582, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000
$dlg = Find-Dialog
$lv = Find-ListByCtlId $dlg 147
Set-ListSel $lv (Find-ListIndexByText $lv "Comparison")
Start-Sleep -Milliseconds 1500

# leftmost "(" button
$b = Find-ChildAll $dlg "Button\|.*\|id=152"
if ($b -eq [IntPtr]::Zero) { $b = Find-Child $dlg "Button\|(" }
Write-Output ("左槽按钮 = " + $b + " '" + (Get-WindowTitle $b) + "'")
Click-Btn $b
Start-Sleep -Milliseconds 2200
$d2 = Find-Dialog
Write-Output ("dialog = '" + (Get-WindowTitle $d2) + "'")

Click-Btn (Find-Child $d2 "Button\|&Function")
Start-Sleep -Milliseconds 2000
$flv = Find-ListByCtlId $d2 43
$find = Find-ChildAll $d2 "Edit\|.*\|id=42"
foreach ($term in @("Triggering Dialog", "Triggering", "Dialog Item")) {
  Set-EditText $find ""
  Start-Sleep -Milliseconds 400
  Set-EditText $find $term -Nudge
  Start-Sleep -Milliseconds 1500
  $cnt = List-Count $flv
  Write-Output ("--- [" + $term + "] = " + $cnt)
  for ($i = 0; $i -lt [Math]::Min($cnt, 12); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $flv $i)) }
}

$cancel = Find-Child $d2 "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
Start-Sleep -Milliseconds 900
$cancel = Find-Child $dlg "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
