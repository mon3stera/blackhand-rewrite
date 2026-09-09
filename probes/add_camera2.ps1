# Add a Pan Camera action to Untitled Trigger 002 and dump its parameters.
# NOTE: the element pane only refreshes when the list selection actually changes,
# so always select a neighbouring trigger first.

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Find-TriggerNode([string]$name) {
  $cur = Get-Root $listTree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $listTree $cur) -eq $name) { return $cur }
    $cur = Get-Next $listTree $cur
  }
  return [IntPtr]::Zero
}

function Select-Trigger([string]$name) {
  $other = $null
  $cur = Get-Root $listTree
  while ($cur -ne [IntPtr]::Zero) {
    $t = Get-NodeText $listTree $cur
    if ($t -ne $name -and $t -notmatch "=") { $other = $cur; break }
    $cur = Get-Next $listTree $cur
  }
  if ($other -ne $null) { Select-Node $listTree $other; Start-Sleep -Milliseconds 300; Click-Node $listTree $other; Start-Sleep -Milliseconds 1000 }
  $node = Find-TriggerNode $name
  if ($node -eq [IntPtr]::Zero) { return $false }
  Select-Node $listTree $node
  Start-Sleep -Milliseconds 300
  Click-Node $listTree $node
  Start-Sleep -Milliseconds 1600
  return ((Get-NodeText $elemTree (Get-Root $elemTree)) -eq $name)
}

function Get-GroupChildren([string]$trigger, [string]$group) {
  $root = Get-Root $elemTree
  if ((Get-NodeText $elemTree $root) -ne $trigger) { return @() }
  $c = Get-Child $elemTree $root
  while ($c -ne [IntPtr]::Zero) {
    if ((Get-NodeText $elemTree $c) -eq $group) {
      $res = @(); $a = Get-Child $elemTree $c
      while ($a -ne [IntPtr]::Zero) { $res += $a; $a = Get-Next $elemTree $a }
      return $res
    }
    $c = Get-Next $elemTree $c
  }
  return @()
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

if (-not (Select-Trigger "Untitled Trigger 002")) { Write-Output "!! 选择 002 失败"; return }
$acts = Get-GroupChildren "Untitled Trigger 002" "Actions"
Click-Node $elemTree $acts[$acts.Count - 1]
Start-Sleep -Milliseconds 1100
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000
$dlg = Find-Dialog
if (-not (Select-ListItemByText $dlg "Pan Camera" 20 19)) {
  Write-Output "!! 找不到 Pan Camera"
  Click-Btn (Find-Child $dlg "Button\|Cancel")
  return
}
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2200

$acts = Get-GroupChildren "Untitled Trigger 002" "Actions"
$node = $acts[$acts.Count - 1]
Click-Node $elemTree $node
Start-Sleep -Milliseconds 1200
Write-Output ("动作: " + (Get-NodeText $elemTree $node))
$i = 0
foreach ($b in (Get-ParamButtons $main)) { Write-Output ("  param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
