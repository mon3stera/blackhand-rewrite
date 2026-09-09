# Text param -> Function: Convert Integer To Text -> then inspect the nested
# integer parameter's dialog (we want to bind it to the KillCount variable).

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
Click-Btn (Find-Child $dlg "Button\|&Function")
Start-Sleep -Milliseconds 2200

$lv = Find-ListByCtlId $dlg 43
$find = Find-ChildAll $dlg "Edit\|.*\|id=42"
Set-EditText $find $SEARCH -Nudge
Start-Sleep -Milliseconds 1800
Write-Output ("matches = " + (List-Count $lv))
Set-ListSel $lv 0
Start-Sleep -Milliseconds 800
Write-Output ("选中: " + (Read-ListItem $lv 0))
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2500

Write-Output ("dialog after OK = " + (Find-Dialog))
Write-Output "=== 参数行 ==="
Show-Row $main
Write-Output "=== 动作 ==="
foreach ($a in (Get-ActionNodes $elemTree $TRIGGER)) { Write-Output ("    " + (Get-NodeText $elemTree $a)) }

# inspect the nested integer parameter
$btns = Get-ParamButtons $main
$paren = -1
for ($i = 0; $i -lt $btns.Count; $i++) { if ((Get-WindowTitle $btns[$i]) -eq "(") { $paren = $i } }
Write-Output ("paren = " + $paren)
if ($paren -ge 0 -and $paren + 1 -lt $btns.Count) {
  Write-Output ("=== 点击嵌套参数 [" + ($paren + 1) + "] '" + (Get-WindowTitle $btns[$paren + 1]) + "' ===")
  Click-Btn $btns[$paren + 1]
  Start-Sleep -Milliseconds 2500
  $d2 = Find-Dialog
  Write-Output ("nested dialog = " + $d2 + " title='" + (Get-WindowTitle $d2) + "'")
  Write-Output "=== 点击 &Variable ==="
  Click-Btn (Find-Child $d2 "Button\|&Variable")
  Start-Sleep -Milliseconds 2500
  $d3 = Find-Dialog
  Write-Output ("variable dialog = " + $d3 + " title='" + (Get-WindowTitle $d3) + "'")
  foreach ($k in [SC2]::KidsAll($d3)) {
    if ($k -match "\|Edit\||\|SysListView32\||\|Button\|") { Write-Output ("  " + $k) }
    $h = [IntPtr][int64]($k.Split("|")[0])
    if ($k -match "\|SysListView32\|") {
      $cnt = List-Count $h
      for ($j = 0; $j -lt [Math]::Min($cnt, 10); $j++) { Write-Output ("      [" + $j + "] " + (Read-ListItem $h $j)) }
    }
  }
  foreach ($d in @($d3, $d2)) {
    $cancel = Find-Child $d "Button\|Cancel"
    if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel; Start-Sleep -Milliseconds 800 }
  }
}
