# Set the three buttons' labels and offsets.

$TRIGGER = "BuffChoice"
# action index -> @{ text; x; y }
$BUTTONS = @(
  @(1, "增援",   "50", "50"),
  @(2, "医疗兵", "50", "120"),
  @(3, "精英",   "50", "190")
)

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

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500

foreach ($spec in $BUTTONS) {
  $ai = [int]$spec[0]; $text = $spec[1]; $x = $spec[2]; $y = $spec[3]
  $acts = Get-GroupChildren $elemTree $TRIGGER "Actions"
  $node = $acts[$ai]
  Write-Output ("=== 动作 [" + $ai + "] 文字='" + $text + "' 偏移=(" + $x + "," + $y + ") ===")

  # label
  Click-Node $elemTree $node
  Start-Sleep -Milliseconds 1200
  $btns = Get-ParamButtons $main
  Write-Output ("  文字参数原值: '" + (Get-WindowTitle $btns[7]) + "'")
  Click-Btn $btns[7]
  Start-Sleep -Milliseconds 2200
  $d = Find-Dialog
  Write-Output ("  dialog = '" + (Get-WindowTitle $d) + "'")
  Set-DialogText $d $text
  Start-Sleep -Milliseconds 1200

  # offsets
  foreach ($pair in @(@(4, $x), @(5, $y))) {
    Click-Node $elemTree $node
    Start-Sleep -Milliseconds 1000
    $btns = Get-ParamButtons $main
    $pi = [int]$pair[0]; $val = $pair[1]
    Write-Output ("  param[" + $pi + "] 原值 '" + (Get-WindowTitle $btns[$pi]) + "' -> " + $val)
    Click-Btn $btns[$pi]
    Start-Sleep -Milliseconds 2000
    $d = Find-Dialog
    Write-Output ("  dialog = '" + (Get-WindowTitle $d) + "'")
    Set-DialogInt $d $val
    Start-Sleep -Milliseconds 1000
  }
}

Write-Output "=== 结果 ==="
$i = 0
foreach ($node in (Get-GroupChildren $elemTree $TRIGGER "Actions")) {
  Write-Output ("  [" + $i + "] " + (Get-NodeText $elemTree $node)); $i++
}

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
