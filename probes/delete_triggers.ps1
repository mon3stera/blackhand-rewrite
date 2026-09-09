# Delete leftover triggers from the trigger list.
# Uses the tree's own keyboard delete after a real click, then confirms the
# possible "are you sure" dialog.

$TARGETS = @("Untitled Trigger 005", "Untitled Trigger 001")

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
  while ($cur -ne [IntPtr]::Zero) { Write-Output ("    " + (Get-NodeText $tree $cur)); $cur = Get-Next $tree $cur }
}

Write-Output "=== 删除前 ==="
Show-List $listTree

foreach ($name in $TARGETS) {
  $node = Find-TriggerNode $listTree $name
  if ($node -eq [IntPtr]::Zero) { Write-Output ("跳过（不存在）: " + $name); continue }
  Write-Output ("--- 删除 " + $name + " (node " + $node + ") ---")
  Click-Node $listTree $node
  Start-Sleep -Milliseconds 900
  [void][SC2]::SendMessage($listTree, 0x0100, [IntPtr]0x2E, [IntPtr]1)   # WM_KEYDOWN VK_DELETE
  [void][SC2]::SendMessage($listTree, 0x0101, [IntPtr]0x2E, [IntPtr]1)   # WM_KEYUP
  Start-Sleep -Milliseconds 1500

  $dlg = Find-Dialog
  if ($dlg -ne [IntPtr]::Zero) {
    Write-Output ("    确认对话框: '" + (Get-WindowTitle $dlg) + "'")
    foreach ($k in [SC2]::KidsAll($dlg)) { Write-Output ("      " + $k) }
    $ok = Find-Child $dlg "Button\|&Yes"
    if ($ok -eq [IntPtr]::Zero) { $ok = Find-Child $dlg "Button\|&OK" }
    if ($ok -eq [IntPtr]::Zero) { $ok = Find-Child $dlg "Button\|Yes" }
    if ($ok -ne [IntPtr]::Zero) { Click-Btn $ok }
    Start-Sleep -Milliseconds 2000
  } else {
    Write-Output "    没有确认对话框"
  }
}

Write-Output "=== 删除后 ==="
Show-List $listTree

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
