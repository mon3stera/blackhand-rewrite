# 1) Dialog Item param -> &Variable mode: which list ids does the picker use?
# 2) Create Units action: what does an unset point parameter look like?

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

Click-Node $listTree (Find-TriggerNode $listTree "Buff1")
Start-Sleep -Milliseconds 1500

Write-Output "=== Create Units 动作的参数行 ==="
$act = (Get-GroupChildren $elemTree "Buff1" "Actions")[0]
Click-Node $elemTree $act
Start-Sleep -Milliseconds 1200
$i = 0
foreach ($b in (Get-ParamButtons $main)) { Write-Output ("  param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }

Write-Output "=== Dialog Item 事件的 &Variable 模式 ==="
$ev = (Get-GroupChildren $elemTree "Buff1" "Events")[0]
Click-Node $elemTree $ev
Start-Sleep -Milliseconds 1200
$btns = Get-ParamButtons $main
Write-Output ("event param[0] = '" + (Get-WindowTitle $btns[0]) + "'")
Click-Btn $btns[0]
Start-Sleep -Milliseconds 2200
$d = Find-Dialog
Write-Output ("dialog = '" + (Get-WindowTitle $d) + "'")
Click-Btn (Find-Child $d "Button\|&Variable")
Start-Sleep -Milliseconds 2000
Write-Output "=== &Variable 之后 ==="
foreach ($k in [SC2]::KidsAll($d)) {
  if ($k -match "\|Edit\||\|SysListView32\||\|Button\||\|ComboBox\|") {
    Write-Output ("  " + $k)
    $h = [IntPtr][int64]($k.Split("|")[0])
    if ($k -match "\|SysListView32\|") {
      $cnt = List-Count $h
      Write-Output ("    LIST count=" + $cnt)
      for ($j = 0; $j -lt [Math]::Min($cnt, 8); $j++) { Write-Output ("      [" + $j + "] " + (Read-ListItem $h $j)) }
    }
  }
}
$cancel = Find-Child $d "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
