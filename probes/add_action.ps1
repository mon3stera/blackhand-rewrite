# Reusable: add an action to a trigger by searching the New Action dialog.
# Configure the four variables below, then run through tools/sc2gui.py.

$TRIGGER = "Untitled Trigger 004"      # trigger that receives the action
$SEARCH = "Modify Variable"            # text typed into the dialog's Find box
$PICK = 0                              # index inside the filtered result list
$PICK_TEXT = "Modify Variable (Integer)"  # exact item text (overrides $PICK when found)
$SELECT_ACTION_INDEX = 0               # action selected before inserting (new one lands after it)

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

function Show-Actions([IntPtr]$tree, [string]$name) {
  $i = 0
  foreach ($a in (Get-ActionNodes $tree $name)) { Write-Output ("    [" + $i + "] " + (Get-NodeText $tree $a)); $i++ }
}

function Show-Row([IntPtr]$main) {
  $i = 0
  foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) {
  $c = Find-Child $stale "Button\|Cancel"
  if ($c -ne [IntPtr]::Zero) { Click-Btn $c }
  Start-Sleep -Milliseconds 1200
}

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
$acts = Get-ActionNodes $elemTree $TRIGGER
Write-Output ("=== 现有动作 ===")
Show-Actions $elemTree $TRIGGER
Click-Node $elemTree $acts[$SELECT_ACTION_INDEX]
Start-Sleep -Milliseconds 1200

Write-Output ("=== New Action: 搜索 '" + $SEARCH + "' 选 [" + $PICK + "] ===")
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000

$dlg = Find-Dialog
$lv = Set-FilterText $dlg $SEARCH 1

$cnt = List-Count $lv
Write-Output ("matches = " + $cnt)
for ($i = 0; $i -lt [Math]::Min($cnt, 12); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }

if ($PICK_TEXT -ne "") {
  $idx = Find-ListIndexByText $lv $PICK_TEXT
  if ($idx -ge 0) { $PICK = $idx; Write-Output ("按文本定位: " + $PICK_TEXT + " -> [" + $idx + "]") }
}
if ($cnt -le $PICK) { Write-Output "结果不足，取消"; $cancel = Find-Child $dlg "Button\|Cancel"; Click-Btn $cancel; return }

Set-ListSel $lv $PICK
Start-Sleep -Milliseconds 800
$desc = Find-ChildAll $dlg "RichEdit20W\|.*\|id=21"
Write-Output ("选中: " + (Read-ListItem $lv $PICK) + "   描述=[" + (Read-ControlText $desc 1024) + "]")
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2500

Write-Output "=== 添加后动作 ==="
Show-Actions $elemTree $TRIGGER
Write-Output "=== 新动作参数 ==="
Show-Row $main
