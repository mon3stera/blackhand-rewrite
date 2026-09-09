# Read the variable property panel: name field, type selectors, flags.

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Find-VarNode([IntPtr]$tree) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -like "*KillCount*") { return $cur }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

$v = Find-VarNode $listTree
Click-Node $listTree $v
Start-Sleep -Milliseconds 1800

foreach ($k in [SC2]::KidsAll($main)) {
  if ($k -match "\|ComboBox\||\|Edit\||\|RichEdit20W\||\|Button\|") {
    Write-Output ($k)
    $h = [IntPtr][int64]($k.Split("|")[0])
    if ($k -match "\|ComboBox\|") { $names = Read-ComboUIA $h }
    if ($k -match "\|Edit\||\|RichEdit20W\|") { Write-Output ("    text=[" + (Read-ControlText $h 256) + "]") }
  }
}
