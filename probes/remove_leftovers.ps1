# Remove the two leftovers found by the audit:
#   - Melee Initialization: the stray "Any Dialog Item is used" event and the
#     "Show (Last created dialog)" action (they cause a script error at map init)
#   - BuffChoice: the unconfigured "Set Variable = Value" action

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Select-Trigger([string]$name) {
  $node = [IntPtr]::Zero
  $cur = Get-Root $listTree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $listTree $cur) -eq $name) { $node = $cur; break }
    $cur = Get-Next $listTree $cur
  }
  if ($node -eq [IntPtr]::Zero) { return $false }
  for ($try = 1; $try -le 3; $try++) {
    Select-Node $listTree $node
    Click-Node $listTree $node
    Start-Sleep -Milliseconds 1200
    if ((Get-NodeText $elemTree (Get-Root $elemTree)) -eq $name) { return $true }
    Start-Sleep -Milliseconds 800
  }
  return $false
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

function Remove-Nodes([string]$trigger, [string]$group, [string]$pattern) {
  $n = 0
  foreach ($k in (Get-GroupChildren $trigger $group)) {
    $t = Get-NodeText $elemTree $k
    if ($t -match $pattern) {
      Write-Output ("  删除 [" + $group + "] " + $t)
      Click-Node $elemTree $k
      Start-Sleep -Milliseconds 900
      [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
      Start-Sleep -Milliseconds 1300
      $n++
    }
  }
  return $n
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Write-Output "=== Melee Initialization ==="
if (-not (Select-Trigger "Melee Initialization")) { Write-Output "  !! 选择失败" }
else {
  $null = Remove-Nodes "Melee Initialization" "Events" "Any Dialog Item"
  $null = Remove-Nodes "Melee Initialization" "Actions" "^Dialog -Show \(Last created dialog\)"
  foreach ($g in @("Events", "Actions")) {
    foreach ($k in (Get-GroupChildren "Melee Initialization" $g)) { Write-Output ("  剩: " + (Get-NodeText $elemTree $k)) }
  }
}

Write-Output "=== BuffChoice ==="
if (-not (Select-Trigger "BuffChoice")) { Write-Output "  !! 选择失败" }
else {
  $null = Remove-Nodes "BuffChoice" "Actions" "^Variable -Set Variable = Value$"
  foreach ($k in (Get-GroupChildren "BuffChoice" "Actions")) { Write-Output ("  剩: " + (Get-NodeText $elemTree $k)) }
}

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
