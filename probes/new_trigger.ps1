# Reusable: create a new trigger (Data > New > New Trigger, id 580) and name it.

$NAME = "BuffChoice"
$AFTER = "Untitled Trigger 004"

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

function Show-List([IntPtr]$tree) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) { Write-Output ("  " + (Get-NodeText $tree $cur)); $cur = Get-Next $tree $cur }
}

Write-Output "=== 创建前 ==="
Show-List $listTree

if ((Find-TriggerNode $listTree $NAME) -ne [IntPtr]::Zero) {
  Write-Output ("已存在: " + $NAME)
  return
}

Click-Node $listTree (Find-TriggerNode $listTree $AFTER)
Start-Sleep -Milliseconds 1200

[void][SC2]::SendMessage($main, 0x0111, [IntPtr]580, [IntPtr]::Zero)
Start-Sleep -Milliseconds 2500

$edit = [IntPtr]::Zero
foreach ($k in [SC2]::KidsAll($main)) {
  if ($k -match "\|Edit\|" -and $k -match "Untitled Trigger") { $edit = [IntPtr][int64]($k.Split("|")[0]) }
}
Write-Output ("inline edit = " + $edit)
if ($edit -ne [IntPtr]::Zero) {
  Set-EditText $edit $NAME
  Start-Sleep -Milliseconds 500
  [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)
  [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
  Start-Sleep -Milliseconds 1500
}

Write-Output "=== 创建后 ==="
Show-List $listTree

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
