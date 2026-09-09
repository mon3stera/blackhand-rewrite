# Fix the variable name through its property panel (Edit id 318) and save.

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

$v = Find-VarNode $listTree
Write-Output ("node = " + $v + " text=[" + (Get-NodeText $listTree $v) + "]")
Select-Node $listTree $v
Start-Sleep -Milliseconds 1800

$nameEdit = Find-Child $main "Edit\|.*\|id=318"
if ($nameEdit -eq [IntPtr]::Zero) { $nameEdit = Find-Child $main "Edit\|" }
Write-Output ("name edit = " + $nameEdit)
if ($nameEdit -eq [IntPtr]::Zero) { return }

Set-EditText $nameEdit $NAME
Start-Sleep -Milliseconds 800

# commit by clicking the element tree
Click-Node $elemTree (Get-Root $elemTree)
Start-Sleep -Milliseconds 1500

Write-Output "=== 触发器列表 ==="
$cur = Get-Root $listTree
while ($cur -ne [IntPtr]::Zero) { Write-Output ("  " + (Get-NodeText $listTree $cur)); $cur = Get-Next $listTree $cur }

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
