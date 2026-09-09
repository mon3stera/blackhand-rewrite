# Reusable: create global variables of a given type through the GUI.
# New Variable (Data > New > New Variable, id 593) creates an Integer variable in
# inline-rename mode; the type is then set by typing into the type combo (id 320).

$VARS = @(
  @("BuffDialog", "Dialog"),
  @("BuffBtn1",   "Dialog Item"),
  @("BuffBtn2",   "Dialog Item"),
  @("BuffBtn3",   "Dialog Item")
)

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

function Find-InlineEdit([IntPtr]$parent) {
  foreach ($k in [SC2]::KidsAll($parent)) {
    if ($k -match "\|Edit\|") { return [IntPtr][int64]($k.Split("|")[0]) }
  }
  return [IntPtr]::Zero
}

function Set-VarType([IntPtr]$main, [string]$type) {
  $cb = Find-ChildAll $main "ComboBox\|.*\|id=320"
  if ($cb -eq [IntPtr]::Zero) { Write-Output "  找不到类型下拉"; return }
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
}

# restore the existing counter to Integer first
$kill = Find-VarNode $listTree "KillCount"
if ($kill -ne [IntPtr]::Zero) {
  Click-Node $listTree $kill
  Start-Sleep -Milliseconds 1500
  Write-Output ("恢复 KillCount -> Integer  (当前: " + (Get-NodeText $listTree $kill) + ")")
  Set-VarType $main "Integer"
  Start-Sleep -Milliseconds 800
}

foreach ($pair in $VARS) {
  $name = $pair[0]; $type = $pair[1]
  $existing = Find-VarNode $listTree $name
  if ($existing -ne [IntPtr]::Zero) {
    Write-Output ("已存在，跳过: " + $name)
    continue
  }

  Write-Output ("=== 新建变量 " + $name + " : " + $type + " ===")
  $sel = Find-VarNode $listTree "KillCount"
  if ($sel -ne [IntPtr]::Zero) { Click-Node $listTree $sel; Start-Sleep -Milliseconds 900 }

  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]593, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 2200

  $edit = Find-InlineEdit $main
  Write-Output ("  inline edit = " + $edit + " text=[" + (Read-ControlText $edit 128) + "]")
  if ($edit -ne [IntPtr]::Zero) {
    Set-EditText $edit $name
    Start-Sleep -Milliseconds 500
    [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)
    [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
    Start-Sleep -Milliseconds 1500
  }

  $node = Find-VarNode $listTree $name
  if ($node -eq [IntPtr]::Zero) { Write-Output ("  创建失败: " + $name); continue }
  Click-Node $listTree $node
  Start-Sleep -Milliseconds 1600
  Set-VarType $main $type
  Start-Sleep -Milliseconds 800
  Write-Output ("  结果: " + (Get-NodeText $listTree $node))
}

Write-Output "=== 变量列表 ==="
$cur = Get-Root $listTree
while ($cur -ne [IntPtr]::Zero) { Write-Output ("  " + (Get-NodeText $listTree $cur)); $cur = Get-Next $listTree $cur }

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
