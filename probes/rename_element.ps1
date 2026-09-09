# Rename an element (variable/trigger) through Edit > Rename (id 83), which opens
# the inline label editor in the trigger list.

$NAME = "KillCount"

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Find-VarNode([IntPtr]$tree) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    $t = Get-NodeText $tree $cur
    if ($t -like "*KillCount*" -or $t -like "*Untitled Variable*") { return $cur }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

function Find-InlineEdit([IntPtr]$parent) {
  foreach ($k in [SC2]::KidsAll($parent)) {
    if ($k -match "\|Edit\|") { return [IntPtr][int64]($k.Split("|")[0]) }
  }
  return [IntPtr]::Zero
}

$v = Find-VarNode $listTree
Write-Output ("node = " + $v + " text=[" + (Get-NodeText $listTree $v) + "]")
Click-Node $listTree $v
Start-Sleep -Milliseconds 1200

Write-Output "=== 发送 Rename (83) ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]83, [IntPtr]::Zero)
Start-Sleep -Milliseconds 1500

$edit = Find-InlineEdit $listTree
if ($edit -eq [IntPtr]::Zero) { $edit = Find-InlineEdit $main }
Write-Output ("inline edit = " + $edit + "  text=[" + (Read-ControlText $edit 256) + "]")

if ($edit -ne [IntPtr]::Zero) {
  Set-EditText $edit $NAME
  Start-Sleep -Milliseconds 600
  [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)   # VK_RETURN
  [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
  Start-Sleep -Milliseconds 1500
}

Click-Node $elemTree (Get-Root $elemTree)
Start-Sleep -Milliseconds 1200

Write-Output "=== 触发器列表 ==="
$cur = Get-Root $listTree
while ($cur -ne [IntPtr]::Zero) { Write-Output ("  " + (Get-NodeText $listTree $cur)); $cur = Get-Next $listTree $cur }

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
