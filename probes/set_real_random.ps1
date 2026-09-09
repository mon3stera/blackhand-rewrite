# Reusable: replace a Real parameter with Random Real(min, max).

$TRIGGER = "Untitled Trigger 003"
$ACTION_INDEX = 1
$PARAM_INDEX = 7
$FUNC = "Random Real"
$MIN = "16"
$MAX = "112"

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

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
$acts = Get-ActionNodes $elemTree $TRIGGER
Click-Node $elemTree $acts[$ACTION_INDEX]
Start-Sleep -Milliseconds 1500

$btns = Get-ParamButtons $main
Write-Output ("param[" + $PARAM_INDEX + "] = '" + (Get-WindowTitle $btns[$PARAM_INDEX]) + "'")
Click-Btn $btns[$PARAM_INDEX]
Start-Sleep -Milliseconds 2500

$dlg = Find-Dialog
Write-Output ("dialog = '" + (Get-WindowTitle $dlg) + "'")
Click-Btn (Find-Child $dlg "Button\|&Function")
Start-Sleep -Milliseconds 2200

$lv = Find-ListByCtlId $dlg 43
$find = Find-ChildAll $dlg "Edit\|.*\|id=42"
Set-EditText $find $FUNC -Nudge
Start-Sleep -Milliseconds 1800
$cnt = List-Count $lv
Write-Output ("matches = " + $cnt)
for ($i = 0; $i -lt [Math]::Min($cnt, 8); $i++) { Write-Output ("  [" + $i + "] " + (Read-ListItem $lv $i)) }
$idx = Find-ListIndexByText $lv $FUNC
if ($idx -lt 0) { Write-Output "找不到函数"; Click-Btn (Find-Child $dlg "Button\|Cancel"); return }
Set-ListSel $lv $idx
Start-Sleep -Milliseconds 700
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2500

Click-Node $elemTree $acts[$ACTION_INDEX]
Start-Sleep -Milliseconds 1500
$btns = Get-ParamButtons $main
Write-Output "=== 转换后 ==="
Show-Row $main

foreach ($off in @(1, 2)) {
  $target = $PARAM_INDEX + $off
  if ($target -ge $btns.Count) { continue }
  $val = if ($off -eq 1) { $MIN } else { $MAX }
  Write-Output ("=== 设置 param[" + $target + "] '" + (Get-WindowTitle $btns[$target]) + "' -> " + $val + " ===")
  Click-Btn $btns[$target]
  Start-Sleep -Milliseconds 2200
  $d = Find-Dialog
  Write-Output ("  dialog = '" + (Get-WindowTitle $d) + "'")
  Set-DialogInt $d $val
  Start-Sleep -Milliseconds 1000
  $btns = Get-ParamButtons $main
}

Write-Output "=== 结果 ==="
Click-Node $elemTree $acts[$ACTION_INDEX]
Start-Sleep -Milliseconds 1200
Show-Row $main
foreach ($a in (Get-ActionNodes $elemTree $TRIGGER)) { Write-Output ("    " + (Get-NodeText $elemTree $a)) }

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
