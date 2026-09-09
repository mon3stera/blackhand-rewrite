# What type index do the BuffBtn variables sit on, and what does "Control" give?

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Find-VarNode([IntPtr]$tree, [string]$name) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -like ("*" + $name + "*")) { return $cur }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

function Set-VarType([IntPtr]$main, [string]$type) {
  $cb = Find-ChildAll $main "ComboBox\|.*\|id=320"
  $r = (Get-RectStr $cb).Split(",")
  $x = [int](([int]$r[0] + [int]$r[2]) / 2)
  $y = [int](([int]$r[1] + [int]$r[3]) / 2)
  $lp = [IntPtr]($x -bor ($y -shl 16))
  [void][SC2]::PostMessage($cb, 0x0201, [IntPtr]1, $lp)
  [void][SC2]::PostMessage($cb, 0x0202, [IntPtr]0, $lp)
  Start-Sleep -Milliseconds 900
  foreach ($ch in $type.ToCharArray()) {
    [void][SC2]::SendMessage($cb, 0x0102, [IntPtr][int]$ch, [IntPtr]1)
    Start-Sleep -Milliseconds 150
  }
  Start-Sleep -Milliseconds 400
  [void][SC2]::SendMessage($cb, 0x0100, [IntPtr]0x0D, [IntPtr]1)
  [void][SC2]::SendMessage($cb, 0x0101, [IntPtr]0x0D, [IntPtr]1)
  Start-Sleep -Milliseconds 1200
  $cur = [int][SC2]::SendMessage($cb, 0x0147, [IntPtr]0, [IntPtr]::Zero)
  $cnt = [int][SC2]::SendMessage($cb, 0x0146, [IntPtr]0, [IntPtr]::Zero)
  Write-Output ("  type combo index = " + $cur + " / " + $cnt)
}

foreach ($n in @("BuffBtn1", "BuffDialog", "KillCount")) {
  $v = Find-VarNode $listTree $n
  if ($v -eq [IntPtr]::Zero) { Write-Output ($n + " 不存在"); continue }
  Click-Node $listTree $v
  Start-Sleep -Milliseconds 1500
  $cb = Find-ChildAll $main "ComboBox\|.*\|id=320"
  $cur = [int][SC2]::SendMessage($cb, 0x0147, [IntPtr]0, [IntPtr]::Zero)
  $cnt = [int][SC2]::SendMessage($cb, 0x0146, [IntPtr]0, [IntPtr]::Zero)
  Write-Output ((Get-NodeText $listTree $v) + "   -> type index " + $cur + " / " + $cnt)
}

Write-Output "=== 测试把 BuffBtn3 改成 Control ==="
$v = Find-VarNode $listTree "BuffBtn3"
Click-Node $listTree $v
Start-Sleep -Milliseconds 1500
Set-VarType $main "Control"
Click-Node $listTree $v
Start-Sleep -Milliseconds 1200
Write-Output ("  现在: " + (Get-NodeText $listTree $v))

Write-Output "=== 再改回 Dialog Item ==="
Click-Node $listTree $v
Start-Sleep -Milliseconds 1200
Set-VarType $main "Dialog Item"
Click-Node $listTree $v
Start-Sleep -Milliseconds 1200
Write-Output ("  现在: " + (Get-NodeText $listTree $v))
