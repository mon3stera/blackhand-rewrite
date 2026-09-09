# Create a trigger named $NAME and add the "Dialog Item Is Used" event, then dump
# the event's parameters.

$NAME = "Buff1"
$AFTER = "BuffChoice"
$EVENT_SEARCH = "Dialog Item Is Used"

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

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

if ((Find-TriggerNode $listTree $NAME) -eq [IntPtr]::Zero) {
  Write-Output ("=== 新建触发器 " + $NAME + " ===")
  Click-Node $listTree (Find-TriggerNode $listTree $AFTER)
  Start-Sleep -Milliseconds 1200
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]580, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 2500
  foreach ($k in [SC2]::KidsAll($main)) {
    if ($k -match "\|Edit\|" -and $k -match "Untitled Trigger") {
      $edit = [IntPtr][int64]($k.Split("|")[0])
      Set-EditText $edit $NAME
      Start-Sleep -Milliseconds 500
      [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)
      [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
      Start-Sleep -Milliseconds 1500
    }
  }
} else {
  Write-Output ($NAME + " 已存在")
}

Click-Node $listTree (Find-TriggerNode $listTree $NAME)
Start-Sleep -Milliseconds 1500

if ((Get-GroupChildren $elemTree $NAME "Events").Count -eq 0) {
  Write-Output "=== 添加事件 ==="
  Click-Node $elemTree (Get-GroupNode $elemTree $NAME "Events")
  Start-Sleep -Milliseconds 1200
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]581, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 3000
  $dlg = Find-Dialog
  $lv = Find-ListByCtlId $dlg 20
  $null = Set-FilterText $dlg $EVENT_SEARCH 1
  $idx = Find-ListIndexByText $lv $EVENT_SEARCH
  Write-Output ("事件匹配 index = " + $idx)
  if ($idx -ge 0) {
    Set-ListSel $lv $idx
    Start-Sleep -Milliseconds 600
    Click-Btn (Find-Child $dlg "Button\|&OK")
    Start-Sleep -Milliseconds 2200
  } else {
    for ($i = 0; $i -lt [Math]::Min((List-Count $lv), 10); $i++) { Write-Output ("  [" + $i + "] " + (Read-ListItem $lv $i)) }
    Click-Btn (Find-Child $dlg "Button\|Cancel")
  }
}

Write-Output "=== 事件与参数 ==="
foreach ($ev in (Get-GroupChildren $elemTree $NAME "Events")) {
  Write-Output ("  " + (Get-NodeText $elemTree $ev))
  Click-Node $elemTree $ev
  Start-Sleep -Milliseconds 1200
  $i = 0
  foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
}
