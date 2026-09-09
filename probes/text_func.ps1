# Text param -> Function mode -> pick "Convert Integer To Text".

$TRIGGER = "Untitled Trigger 004"
$ACTION_INDEX = 0
$PARAM_INDEX = 0
$SEARCH = "Integer To Text"

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

function Show-Row([IntPtr]$main) {
  $i = 0
  foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
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
Write-Output ("dialog = " + $dlg + " title='" + (Get-WindowTitle $dlg) + "'")

Write-Output "=== 点击 &Function ==="
Click-Btn (Find-Child $dlg "Button\|&Function")
Start-Sleep -Milliseconds 2500

foreach ($k in [SC2]::KidsAll($dlg)) {
  if ($k -match "\|Edit\||\|SysListView32\||\|Button\||\|ComboBox\|") { Write-Output ("  " + $k) }
}

$lv = Find-ListByCtlId $dlg 43
if ($lv -eq [IntPtr]::Zero) { $lv = Find-ChildAll $dlg "SysListView32\|.*\|id=43" }
$find = Find-ChildAll $dlg "Edit\|.*\|id=42"
Write-Output ("lv = " + $lv + " find = " + $find)

if ($lv -ne [IntPtr]::Zero -and $find -ne [IntPtr]::Zero) {
  Set-EditText $find $SEARCH -Nudge
  Start-Sleep -Milliseconds 1800
  $cnt = List-Count $lv
  Write-Output ("matches = " + $cnt)
  for ($i = 0; $i -lt [Math]::Min($cnt, 15); $i++) { Write-Output ("  [" + $i + "] " + (Read-ListItem $lv $i)) }
}

$cancel = Find-Child $dlg "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
Start-Sleep -Milliseconds 800
