# Delete leftover triggers via Edit > Clear (WM_COMMAND 536).
# The target node must be really clicked first, otherwise the command is ignored.

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
  if ($node -eq [IntPtr]::Zero) { Write-Output ("跳过: " + $name); continue }
  Write-Output ("--- Clear " + $name + " ---")
  Click-Node $listTree $node
  Start-Sleep -Milliseconds 900
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 1500

  $dlg = Find-Dialog
  if ($dlg -ne [IntPtr]::Zero) {
    Write-Output ("    确认: '" + (Get-WindowTitle $dlg) + "'")
    foreach ($k in [SC2]::KidsAll($dlg)) { Write-Output ("      " + $k) }
    foreach ($re in @("Button\|&Yes", "Button\|&OK", "Button\|Yes", "Button\|&Clear")) {
      $b = Find-Child $dlg $re
      if ($b -ne [IntPtr]::Zero) { Click-Btn $b; break }
    }
    Start-Sleep -Milliseconds 2000
  } else {
    Write-Output "    无确认对话框"
  }
}

Write-Output "=== 删除后 ==="
Show-List $listTree

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
