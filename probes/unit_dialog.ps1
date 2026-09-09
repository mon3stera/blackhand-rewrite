# Probe: read-only inspection of the "Game Link - Unit" value dialog.
# Opens the dialog for the unit-type parameter, dumps combo boxes + RichEdit,
# switches to V&alue mode, re-reads the edit, then cancels without committing.

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
$target = $actions[$actions.Count - 1]
Click-Node $elemTree $target
Start-Sleep -Milliseconds 1800

# the unit-type button shows the current gamelink text, e.g. "Marine" (with quotes)
$unitBtn = [IntPtr]::Zero
foreach ($k in [SC2]::Kids($main)) {
  if ($k -match "\|Button\|\x22") { $unitBtn = [IntPtr][int64]($k.Split("|")[0]) }
}
Write-Output ("unit button = " + $unitBtn)
Click-Btn $unitBtn
Start-Sleep -Milliseconds 2200

$dlg = [IntPtr]::Zero
foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  if ($a -match "Game Link - Unit$") { $dlg = [IntPtr][int64]($a.Split("|")[0]) }
}
Write-Output ("dialog = " + $dlg)
if ($dlg -eq [IntPtr]::Zero) { return }

function Dump-Dialog([IntPtr]$d, [string]$label) {
  Write-Output ("=== " + $label + " ===")
  foreach ($k in [SC2]::KidsAll($d)) {
    $h = [IntPtr][int64]($k.Split("|")[0])
    if ($k -match "\|ComboBox\|") { Write-Output ("  " + $k); Read-Combo $h }
    elseif ($k -match "\|RichEdit20W\||\|Edit\|") { Write-Output ("  " + $k + "  text=[" + (Read-ControlText $h 512) + "]") }
    else { Write-Output ("  " + $k) }
  }
}

Dump-Dialog $dlg "初始状态"

Write-Output "=== 点击 V&alue ==="
$val = Find-Child $dlg "Button\|V&alue"
Write-Output ("value btn = " + $val)
Click-Btn $val
Start-Sleep -Milliseconds 1500
Dump-Dialog $dlg "Value 模式"

Write-Output "=== 点击 &Preset ==="
Click-Btn (Find-Child $dlg "Button\|&Preset")
Start-Sleep -Milliseconds 1500
Dump-Dialog $dlg "Preset 模式"

Write-Output "=== 点击 &Function ==="
Click-Btn (Find-Child $dlg "Button\|&Function")
Start-Sleep -Milliseconds 1500
Dump-Dialog $dlg "Function 模式"

Write-Output "=== 取消 ==="
Click-Btn (Find-Child $dlg "Button\|Cancel")
Start-Sleep -Milliseconds 800
