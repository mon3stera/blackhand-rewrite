# Probe: Win32 view of the "Game Link - Unit" dialog in Value mode.
# Value mode swaps the dialog to a game-link browser (search + tree/list).

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

Write-Output "=== Value 模式下的全部控件 ==="
foreach ($k in [SC2]::KidsAll($dlg)) { Write-Output ("  " + $k) }

Write-Output "=== 列表/树内容 ==="
foreach ($k in [SC2]::KidsAll($dlg)) {
  $h = [IntPtr][int64]($k.Split("|")[0])
  if ($k -match "\|SysListView32\|") {
    $cnt = List-Count $h
    Write-Output ("  LIST " + $h + " count=" + $cnt)
    for ($i = 0; $i -lt [Math]::Min($cnt, 25); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $h $i)) }
  }
  if ($k -match "\|SysTreeView32\|") {
    Write-Output ("  TREE " + $h)
    $node = Get-Root $h
    $n = 0
    while ($node -ne [IntPtr]::Zero -and $n -lt 40) {
      Write-Output ("    " + (Get-NodeText $h $node))
      $node = Get-Next $h $node
      $n++
    }
  }
  if ($k -match "\|Edit\||\|RichEdit20W\|") {
    Write-Output ("  EDIT " + $h + " text=[" + (Read-ControlText $h 512) + "]")
  }
}

Write-Output "=== 取消 ==="
Click-Btn (Find-Child $dlg "Button\|Cancel")
Start-Sleep -Milliseconds 800
