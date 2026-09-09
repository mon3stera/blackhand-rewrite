# Probe: does typing into the Value-mode Search box filter the game-link tree?
# Read-only: cancels the dialog at the end.

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

function Get-ActionNodes([IntPtr]$tree, [string]$triggerName) {
  $t = Find-TriggerNode $tree $triggerName
  if ($t -eq [IntPtr]::Zero) { return @() }
  $child = Get-Child $tree $t
  while ($child -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $child) -eq "Actions") {
      $res = @()
      $a = Get-Child $tree $child
      while ($a -ne [IntPtr]::Zero) { $res += $a; $a = Get-Next $tree $a }
      return $res
    }
    $child = Get-Next $tree $child
  }
  return @()
}

function Show-Tree([IntPtr]$t, [int]$maxNodes) {
  $node = Get-Root $t
  $n = 0
  while ($node -ne [IntPtr]::Zero -and $n -lt $maxNodes) {
    Write-Output ("    " + (Get-NodeText $t $node))
    $node = Get-Next $t $node
    $n++
  }
  Write-Output ("    (显示 " + $n + " 个根/兄弟节点)")
}

function Expand-All([IntPtr]$t, [IntPtr]$node, [int]$depth) {
  if ($node -eq [IntPtr]::Zero -or $depth -gt 4) { return }
  $cur = $node
  while ($cur -ne [IntPtr]::Zero) {
    [void][SC2]::SendMessage($t, 0x1102, [IntPtr]2, $cur)   # TVM_EXPAND / TVE_EXPAND
    $c = Get-Child $t $cur
    if ($c -ne [IntPtr]::Zero) { Expand-All $t $c ($depth + 1) }
    $cur = Get-Next $t $cur
  }
}

Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 002")
Start-Sleep -Milliseconds 1500
$actions = Get-ActionNodes $elemTree "Untitled Trigger 002"
Click-Node $elemTree $actions[$actions.Count - 1]
Start-Sleep -Milliseconds 1800

$unitBtn = [IntPtr]::Zero
foreach ($k in [SC2]::Kids($main)) {
  if ($k -match "\|Button\|\x22") { $unitBtn = [IntPtr][int64]($k.Split("|")[0]) }
}
Click-Btn $unitBtn
Start-Sleep -Milliseconds 2500

$dlg = [IntPtr]::Zero
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  if ($a -match "Game Link - Unit$") { $dlg = [IntPtr][int64]($a.Split("|")[0]) }
}
if ($dlg -eq [IntPtr]::Zero) { Write-Output "no dialog"; return }

Click-Btn (Find-Child $dlg "Button\|V&alue")
Start-Sleep -Milliseconds 2000

$search = Find-Child $dlg "Edit\|"
$tree = Find-Child $dlg "SysTreeView32\|"
Write-Output ("search = " + $search + "  tree = " + $tree)

Write-Output "=== 搜索前 ==="
Show-Tree $tree 20

Write-Output "=== 写入 Marine ==="
Set-EditText $search "Marine"
Start-Sleep -Milliseconds 1500
Write-Output ("搜索框内容 = [" + (Read-ControlText $search 256) + "]")
Show-Tree $tree 20

Write-Output "=== 展开 Unit 根节点 ==="
$node = Get-Root $tree
while ($node -ne [IntPtr]::Zero) {
  if ((Get-NodeText $tree $node) -eq "Unit") {
    [void][SC2]::SendMessage($tree, 0x1102, [IntPtr]2, $node)
    Start-Sleep -Milliseconds 1200
    $c = Get-Child $tree $node
    $n = 0
    while ($c -ne [IntPtr]::Zero -and $n -lt 30) {
      Write-Output ("    Unit > " + (Get-NodeText $tree $c))
      $c = Get-Next $tree $c
      $n++
    }
  }
  $node = Get-Next $tree $node
}

Write-Output "=== 取消 ==="
Click-Btn (Find-Child $dlg "Button\|Cancel")
Start-Sleep -Milliseconds 800
