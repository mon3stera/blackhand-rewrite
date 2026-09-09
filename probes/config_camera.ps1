# Configure the Pan Camera action in Untitled Trigger 002:
#   point -> Point From XY (64, 64), duration -> 0.0

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

if (-not (Select-Trigger "Untitled Trigger 002")) { Write-Output "!! 选择失败"; return }
$acts = Get-GroupChildren "Untitled Trigger 002" "Actions"
$node = $acts[$acts.Count - 1]
Click-Node $elemTree $node
Start-Sleep -Milliseconds 1200

Write-Output "=== 设置点位 ==="
$pb = Get-ParamButtons $main
Click-Btn $pb[1]
Start-Sleep -Milliseconds 2000
$d = Find-Dialog
Write-Output ("  dialog = '" + (Get-WindowTitle $d) + "'")
[void](Set-DialogPointFunc $d "Point From XY" "Point From")
Start-Sleep -Milliseconds 1200

foreach ($idx in @(2, 3)) {
  Click-Node $elemTree $node
  Start-Sleep -Milliseconds 900
  $pb = Get-ParamButtons $main
  Write-Output ("  param[" + $idx + "] '" + (Get-WindowTitle $pb[$idx]) + "' -> 64")
  Click-Btn $pb[$idx]
  Start-Sleep -Milliseconds 1800
  Set-DialogInt (Find-Dialog) "64"
  Start-Sleep -Milliseconds 900
}

Write-Output "=== 设置时长 0 ==="
Click-Node $elemTree $node
Start-Sleep -Milliseconds 900
$pb = Get-ParamButtons $main
$target = -1
for ($i = 0; $i -lt $pb.Count; $i++) {
  $t = Get-WindowTitle $pb[$i]
  Write-Output ("    [" + $i + "] '" + $t + "'")
  if ($t -eq "2.0") { $target = $i }
}
if ($target -ge 0) {
  Click-Btn $pb[$target]
  Start-Sleep -Milliseconds 1800
  Set-DialogInt (Find-Dialog) "0"
  Start-Sleep -Milliseconds 900
}
Write-Output ("动作: " + (Get-NodeText $elemTree $node))

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
