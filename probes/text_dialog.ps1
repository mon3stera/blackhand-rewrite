# Dump the Text parameter dialog (Value / Function modes, function browser ids).

$TRIGGER = "Untitled Trigger 004"
$ACTION_INDEX = 0
$PARAM_INDEX = 0

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

function Get-ActionNodes([IntPtr]$tree, [string]$name) {
  $t = Find-TriggerNode $tree $name
  if ($t -eq [IntPtr]::Zero) { return @() }
  $c = Get-Child $tree $t
  while ($c -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $c) -eq "Actions") {
      $res = @(); $a = Get-Child $tree $c
      while ($a -ne [IntPtr]::Zero) { $res += $a; $a = Get-Next $tree $a }
      return $res
    }
    $c = Get-Next $tree $c
  }
  return @()
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

$acts = Get-ActionNodes $elemTree $TRIGGER
Click-Node $elemTree $acts[$ACTION_INDEX]
Start-Sleep -Milliseconds 1500

$btns = Get-ParamButtons $main
Click-Btn $btns[$PARAM_INDEX]
Start-Sleep -Milliseconds 2500

$dlg = Find-Dialog
Write-Output ("dialog = " + $dlg + "  title='" + (Get-WindowTitle $dlg) + "'")
foreach ($k in [SC2]::KidsAll($dlg)) {
  Write-Output ("  " + $k)
  $h = [IntPtr][int64]($k.Split("|")[0])
  if ($k -match "\|SysListView32\|") {
    $cnt = List-Count $h
    Write-Output ("    LIST count=" + $cnt)
    for ($j = 0; $j -lt [Math]::Min($cnt, 15); $j++) { Write-Output ("      [" + $j + "] " + (Read-ListItem $h $j)) }
  }
  if ($k -match "\|ComboBox\|") { Read-Combo $h }
  if ($k -match "\|Edit\||\|RichEdit20W\|") { Write-Output ("    text=[" + (Read-ControlText $h 256) + "]") }
}

$cancel = Find-Child $dlg "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
Start-Sleep -Milliseconds 800
