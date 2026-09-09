# Learn two things: the Dialog Item parameter dialog layout, and the exact action
# name for unit creation.

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

function New-Trigger([string]$name, [string]$after) {
  if ((Find-TriggerNode $listTree $name) -ne [IntPtr]::Zero) { Write-Output ($name + " 已存在"); return }
  Click-Node $listTree (Find-TriggerNode $listTree $after)
  Start-Sleep -Milliseconds 1200
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]580, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 2500
  foreach ($k in [SC2]::KidsAll($main)) {
    if ($k -match "\|Edit\|" -and $k -match "Untitled Trigger") {
      $edit = [IntPtr][int64]($k.Split("|")[0])
      Set-EditText $edit $name
      Start-Sleep -Milliseconds 500
      [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)
      [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
      Start-Sleep -Milliseconds 1400
    }
  }
  Write-Output ("  新建: " + $name)
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

New-Trigger "Buff1" "BuffChoice"
Click-Node $listTree (Find-TriggerNode $listTree "Buff1")
Start-Sleep -Milliseconds 1400

Click-Node $elemTree (Get-GroupNode $elemTree "Buff1" "Events")
Start-Sleep -Milliseconds 1100
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]581, [IntPtr]::Zero)
Start-Sleep -Milliseconds 2800
$dlg = Find-Dialog
$lv = Find-ListByCtlId $dlg 20
$null = Set-FilterText $dlg "Dialog Item Is Used" 1
$idx = Find-ListIndexByText $lv "Dialog Item Is Used"
Set-ListSel $lv $idx
Start-Sleep -Milliseconds 600
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2200

$ev = (Get-GroupChildren $elemTree "Buff1" "Events")[0]
Write-Output ("事件: " + (Get-NodeText $elemTree $ev))
Click-Node $elemTree $ev
Start-Sleep -Milliseconds 1200
$btns = Get-ParamButtons $main
Write-Output ("param[0] = '" + (Get-WindowTitle $btns[0]) + "'")

Write-Output "=== 点击 param[0] ==="
Click-Btn $btns[0]
Start-Sleep -Milliseconds 2200
$d = Find-Dialog
Write-Output ("dialog = " + $d + " title='" + (Get-WindowTitle $d) + "'")
foreach ($k in [SC2]::KidsAll($d)) {
  Write-Output ("  " + $k)
  $h = [IntPtr][int64]($k.Split("|")[0])
  if ($k -match "\|SysListView32\|") {
    $cnt = List-Count $h
    Write-Output ("    LIST count=" + $cnt)
    for ($j = 0; $j -lt [Math]::Min($cnt, 10); $j++) { Write-Output ("      [" + $j + "] " + (Read-ListItem $h $j)) }
  }
  if ($k -match "\|Edit\||\|RichEdit20W\|") { Write-Output ("    text=[" + (Read-ControlText $h 256) + "]") }
}
$cancel = Find-Child $d "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
Start-Sleep -Milliseconds 900

Write-Output "=== 动作搜索: Create ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000
$dlg2 = Find-Dialog
$lv2 = Find-ListByCtlId $dlg2 20
$null = Set-FilterText $dlg2 "Create Units" 0
Start-Sleep -Milliseconds 800
$cnt = List-Count $lv2
Write-Output ("[Create Units] = " + $cnt)
for ($i = 0; $i -lt [Math]::Min($cnt, 20); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv2 $i)) }
$null = Set-FilterText $dlg2 "Create Unit" 0
Start-Sleep -Milliseconds 800
$cnt2 = List-Count $lv2
Write-Output ("[Create Unit] = " + $cnt2)
for ($i = 0; $i -lt [Math]::Min($cnt2, 20); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv2 $i)) }
Click-Btn (Find-Child $dlg2 "Button\|Cancel")
