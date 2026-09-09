# Rename/redefine the auto-created global variable through its inline editor,
# then commit and save.

$NEW = "KillCount"

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Find-VariableNode([IntPtr]$tree) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -like "*KillCount*") { return $cur }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

function Find-InlineEdit([IntPtr]$main) {
  foreach ($k in [SC2]::Kids($main)) {
    if ($k -match "\|Edit\|" -and $k -match "KillCount|Variable") { return [IntPtr][int64]($k.Split("|")[0]) }
  }
  return [IntPtr]::Zero
}

$v = Find-VariableNode $listTree
Write-Output ("variable node = " + $v)
Select-Node $listTree $v
Start-Sleep -Milliseconds 1500

$edit = Find-InlineEdit $main
Write-Output ("inline edit = " + $edit + "  text=[" + (Read-ControlText $edit 256) + "]")
if ($edit -eq [IntPtr]::Zero) { return }

Set-EditText $edit $NEW
Start-Sleep -Milliseconds 800
Write-Output ("after set: [" + (Read-ControlText $edit 256) + "]")

# commit: click the element tree, then save
Click-Node $elemTree (Get-Root $elemTree)
Start-Sleep -Milliseconds 1200

Write-Output "=== 触发器列表 ==="
$cur = Get-Root $listTree
while ($cur -ne [IntPtr]::Zero) { Write-Output ("  " + (Get-NodeText $listTree $cur)); $cur = Get-Next $listTree $cur }

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
