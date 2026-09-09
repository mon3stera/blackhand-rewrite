# Set the Value parameter of Buff1's Store Integer action to 1.

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Select-Trigger([string]$name) {
  $other = $null
  $cur = Get-Root $listTree
  while ($cur -ne [IntPtr]::Zero) {
    $t = Get-NodeText $listTree $cur
    if ($t -ne $name -and $t -notmatch "=") { $other = $cur; break }
    $cur = Get-Next $listTree $cur
  }
  if ($other -ne [IntPtr]::Zero) { Select-Node $listTree $other; Start-Sleep -Milliseconds 300; Click-Node $listTree $other; Start-Sleep -Milliseconds 1000 }
  $node = [IntPtr]::Zero
  $cur = Get-Root $listTree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $listTree $cur) -eq $name) { $node = $cur; break }
    $cur = Get-Next $listTree $cur
  }
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

if (-not (Select-Trigger "Buff1")) { Write-Output "!! 选择失败"; return }
$acts = Get-GroupChildren "Buff1" "Actions"
foreach ($a in $acts) {
  $t = Get-NodeText $elemTree $a
  if ($t -match "^Bank -Store integer") {
    Write-Output ("目标动作: " + $t)
    Click-Node $elemTree $a
    Start-Sleep -Milliseconds 1100
    $pb = Get-ParamButtons $main
    Write-Output ("  param[0] = '" + (Get-WindowTitle $pb[0]) + "'")
    Click-Btn $pb[0]
    Start-Sleep -Milliseconds 1800
    Set-DialogInt (Find-Dialog) "1"
    Start-Sleep -Milliseconds 900
    Write-Output ("  -> " + (Get-NodeText $elemTree $a))
  }
}

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
