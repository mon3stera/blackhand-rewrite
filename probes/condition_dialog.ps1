# Dump the "Configure Condition" dialog's controls.

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

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500

# the New Condition command only fires when the Conditions group is selected
$root = Get-Root $elemTree
$c = Get-Child $elemTree $root
while ($c -ne [IntPtr]::Zero) {
  if ((Get-NodeText $elemTree $c) -eq "Conditions") { Click-Node $elemTree $c }
  $c = Get-Next $elemTree $c
}
Start-Sleep -Milliseconds 1200

[void][SC2]::SendMessage($main, 0x0111, [IntPtr]582, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000

$dlg = Find-Dialog
Write-Output ("dialog = " + $dlg + " title='" + (Get-WindowTitle $dlg) + "'")
foreach ($k in [SC2]::KidsAll($dlg)) {
  Write-Output ("  " + $k)
  $h = [IntPtr][int64]($k.Split("|")[0])
  if ($k -match "\|SysListView32\|") {
    $cnt = List-Count $h
    Write-Output ("    LIST count=" + $cnt)
    for ($j = 0; $j -lt [Math]::Min($cnt, 20); $j++) { Write-Output ("      [" + $j + "] " + (Read-ListItem $h $j)) }
  }
  if ($k -match "\|Edit\||\|RichEdit20W\|") { Write-Output ("    text=[" + (Read-ControlText $h 256) + "]") }
}
