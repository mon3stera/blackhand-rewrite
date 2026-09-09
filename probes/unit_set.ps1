# Commit: set the unit-type parameter of the last action of "Untitled Trigger 002"
# to Marine through the Value-mode game-link browser, then save the map.
#
# Flow: select trigger -> select action -> click the unit-type parameter button
#       -> V&alue -> search "Marine" -> select the exact node -> OK -> Ctrl+S(15).

$TRIGGER = "Untitled Trigger 002"
$UNIT = "Marine"

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

function Find-NodeExact([IntPtr]$tree, [IntPtr]$parent, [string]$text, [int]$depth) {
  if ($parent -eq [IntPtr]::Zero -or $depth -gt 6) { return [IntPtr]::Zero }
  $cur = $parent
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -eq $text) { return $cur }
    $c = Get-Child $tree $cur
    if ($c -ne [IntPtr]::Zero) {
      $hit = Find-NodeExact $tree $c $text ($depth + 1)
      if ($hit -ne [IntPtr]::Zero) { return $hit }
    }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
$actions = Get-ActionNodes $elemTree $TRIGGER
Click-Node $elemTree $actions[$actions.Count - 1]
Start-Sleep -Milliseconds 1800

$unitBtn = [IntPtr]::Zero
foreach ($k in [SC2]::Kids($main)) {
  if ($k -match "\|Button\|\x22") { $unitBtn = [IntPtr][int64]($k.Split("|")[0]) }
}
Write-Output ("unit button = " + $unitBtn)
Click-Btn $unitBtn
Start-Sleep -Milliseconds 2500

$dlg = [IntPtr]::Zero
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  if ($a -match "Game Link - Unit$") { $dlg = [IntPtr][int64]($a.Split("|")[0]) }
}
if ($dlg -eq [IntPtr]::Zero) { Write-Output "FAIL: no dialog"; return }

Click-Btn (Find-Child $dlg "Button\|V&alue")
Start-Sleep -Milliseconds 2000

$search = Find-Child $dlg "Edit\|"
$tree = Find-Child $dlg "SysTreeView32\|"
Set-EditText $search $UNIT
Start-Sleep -Milliseconds 1800

# make sure the matching branch is expanded, then locate the exact node
$node = Get-Root $tree
while ($node -ne [IntPtr]::Zero) {
  [void][SC2]::SendMessage($tree, 0x1102, [IntPtr]2, $node)   # TVM_EXPAND / TVE_EXPAND
  $node = Get-Next $tree $node
}
Start-Sleep -Milliseconds 1200

$hit = Find-NodeExact $tree (Get-Root $tree) $UNIT 0
Write-Output ("found node = " + $hit + " text='" + (Get-NodeText $tree $hit) + "'")
if ($hit -eq [IntPtr]::Zero) { Click-Btn (Find-Child $dlg "Button\|Cancel"); return }

Select-Node $tree $hit
Start-Sleep -Milliseconds 600
$caret = Get-Sel $tree
Write-Output ("caret = " + $caret + " text='" + (Get-NodeText $tree $caret) + "'")

Write-Output "=== OK ==="
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 3000

foreach ($a in [SC2]::Tops([uint32]$P.Id)) { Write-Output ("  WIN: " + $a) }

# re-read the action text: a complete action no longer shows "(No Options)"-style placeholders
$actions2 = Get-ActionNodes $elemTree $TRIGGER
foreach ($a in $actions2) { Write-Output ("  ACTION: " + (Get-NodeText $elemTree $a)) }

Write-Output "=== 保存 (WM_COMMAND 15) ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 5000
foreach ($a in [SC2]::Tops([uint32]$P.Id)) { Write-Output ("  WIN: " + $a) }
Write-Output "done"
