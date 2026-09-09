# Set the variable's type by typing the type name into the combo (type-ahead).

$TYPE = "Dialog"

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
$r = (Get-RectStr $cb).Split(",")
$x = [int](([int]$r[0] + [int]$r[2]) / 2)
$y = [int](([int]$r[1] + [int]$r[3]) / 2)
$lp = [IntPtr]($x -bor ($y -shl 16))

[void][SC2]::PostMessage($cb, 0x0201, [IntPtr]1, $lp)
[void][SC2]::PostMessage($cb, 0x0202, [IntPtr]0, $lp)
Start-Sleep -Milliseconds 1000

Write-Output ("=== 输入 '" + $TYPE + "' ===")
foreach ($ch in $TYPE.ToCharArray()) {
  [void][SC2]::SendMessage($cb, 0x0102, [IntPtr][int]$ch, [IntPtr]1)
  Start-Sleep -Milliseconds 180
}
Start-Sleep -Milliseconds 500
[void][SC2]::SendMessage($cb, 0x0100, [IntPtr]0x0D, [IntPtr]1)
[void][SC2]::SendMessage($cb, 0x0101, [IntPtr]0x0D, [IntPtr]1)
Start-Sleep -Milliseconds 1200

Click-Node $listTree (Find-VarNode $listTree)
Start-Sleep -Milliseconds 1500
Write-Output ("结果: " + (VarLine $listTree))

$cnt = [int][SC2]::SendMessage($cb, 0x0146, [IntPtr]0, [IntPtr]::Zero)
$cur = [int][SC2]::SendMessage($cb, 0x0147, [IntPtr]0, [IntPtr]::Zero)
Write-Output ("combo index = " + $cur + " / " + $cnt)
