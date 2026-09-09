# Audit every trigger: select it, verify the element tree actually switched, then
# dump events / conditions / actions.

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
    $root = Get-Root $elemTree
    if ((Get-NodeText $elemTree $root) -eq $name) { return $true }
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

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

$names = @()
$cur = Get-Root $listTree
while ($cur -ne [IntPtr]::Zero) {
  $t = Get-NodeText $listTree $cur
  if ($t -notmatch "=") { $names += $t }
  $cur = Get-Next $listTree $cur
}

foreach ($n in $names) {
  Write-Output ("########## " + $n)
  if (-not (Select-Trigger $n)) { Write-Output "  !! 选择失败"; continue }
  foreach ($g in @("Events", "Conditions", "Actions")) {
    $kids = Get-GroupChildren $n $g
    Write-Output ("  [" + $g + "] (" + $kids.Count + ")")
    foreach ($k in $kids) { Write-Output ("    " + (Get-NodeText $elemTree $k)) }
  }
}
