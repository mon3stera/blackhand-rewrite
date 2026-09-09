# Dump the Show/Hide preset parameter dialog.

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

Click-Node $listTree (Find-TriggerNode $listTree "BuffChoice")
Start-Sleep -Milliseconds 1500
$node = (Get-GroupChildren $elemTree "BuffChoice" "Actions")[8]
Click-Node $elemTree $node
Start-Sleep -Milliseconds 1200

$btns = Get-ParamButtons $main
Write-Output ("param[0] = '" + (Get-WindowTitle $btns[0]) + "'")
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
    for ($j = 0; $j -lt [Math]::Min($cnt, 15); $j++) { Write-Output ("      [" + $j + "] " + (Read-ListItem $h $j)) }
  }
  if ($k -match "\|Edit\||\|RichEdit20W\|") { Write-Output ("    text=[" + (Read-ControlText $h 256) + "]") }
}
$cancel = Find-Child $d "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
