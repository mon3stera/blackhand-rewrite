# Try to set the variable type combo without reading its items:
# 1) WM_SETTEXT "Dialog"  2) real click + type-ahead 'd' + Enter.
# After each attempt, read back the variable's line in the trigger list.

$trees = Get-Trees
$listTree = $trees[0]
$main = Find-Main

function Find-VarNode([IntPtr]$tree) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -like "*KillCount*") { return $cur }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

function VarLine([IntPtr]$tree) {
  $v = Find-VarNode $tree
  if ($v -eq [IntPtr]::Zero) { return "(none)" }
  return (Get-NodeText $tree $v)
}

Click-Node $listTree (Find-VarNode $listTree)
Start-Sleep -Milliseconds 1800
Write-Output ("初始: " + (VarLine $listTree))

$cb = Find-ChildAll $main "ComboBox\|.*\|id=320"
Write-Output ("combo = " + $cb)

Write-Output "=== 尝试 1: WM_SETTEXT 'Dialog' ==="
[void][SC2]::SendMessageW($cb, 0x000C, [IntPtr]::Zero, "Dialog")
Start-Sleep -Milliseconds 800
Click-Node $listTree (Find-VarNode $listTree)
Start-Sleep -Milliseconds 1200
Write-Output ("  结果: " + (VarLine $listTree))

Write-Output "=== 尝试 2: 真实点击 + 首字母 'd' + Enter ==="
$r = (Get-RectStr $cb).Split(",")
$x = ([int]$r[0] + [int]$r[2]) / 2
$y = ([int]$r[1] + [int]$r[3]) / 2
$lp = [IntPtr](([int]$x -bor ([int]$y -shl 16)))
[void][SC2]::PostMessage($cb, 0x0201, [IntPtr]1, $lp)
[void][SC2]::PostMessage($cb, 0x0202, [IntPtr]0, $lp)
Start-Sleep -Milliseconds 1200
[void][SC2]::SendMessage($cb, 0x0102, [IntPtr]100, [IntPtr]1)   # WM_CHAR 'd'
Start-Sleep -Milliseconds 800
[void][SC2]::SendMessage($cb, 0x0100, [IntPtr]0x0D, [IntPtr]1)  # VK_RETURN
[void][SC2]::SendMessage($cb, 0x0101, [IntPtr]0x0D, [IntPtr]1)
Start-Sleep -Milliseconds 1200
Click-Node $listTree (Find-VarNode $listTree)
Start-Sleep -Milliseconds 1200
Write-Output ("  结果: " + (VarLine $listTree))

Write-Output "=== 参数面板现状 ==="
foreach ($k in [SC2]::KidsAll($main)) {
  if ($k -match "\|ComboBox\|" -and $k -match "id=320|id=321|id=322|id=323|id=324") {
    $h = [IntPtr][int64]($k.Split("|")[0])
    $cnt = [int][SC2]::SendMessage($h, 0x0146, [IntPtr]0, [IntPtr]::Zero)
    $cur = [int][SC2]::SendMessage($h, 0x0147, [IntPtr]0, [IntPtr]::Zero)
    Write-Output ("  " + $k + "  count=" + $cnt + " cur=" + $cur)
  }
}
