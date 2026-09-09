# Reusable: bind a Text parameter to an Integer variable via
# Function -> "Convert Integer To Text" -> nested param -> Variable mode.

$TRIGGER = "Untitled Trigger 004"
$ACTION_INDEX = 0
$PARAM_INDEX = 0
$VAR = "KillCount"
$PREFIX = ""        # optional literal text placed before the number

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
Write-Output ("param[" + $PARAM_INDEX + "] = '" + (Get-WindowTitle $btns[$PARAM_INDEX]) + "'")
Click-Btn $btns[$PARAM_INDEX]
Start-Sleep -Milliseconds 2500

$dlg = Find-Dialog
Write-Output ("dialog = '" + (Get-WindowTitle $dlg) + "'")

Write-Output "=== Function 模式: Convert Integer To Text ==="
Click-Btn (Find-Child $dlg "Button\|&Function")
Start-Sleep -Milliseconds 2200
$lv = Find-ListByCtlId $dlg 43
$find = Find-ChildAll $dlg "Edit\|.*\|id=42"
Set-EditText $find "Convert Integer To Text" -Nudge
Start-Sleep -Milliseconds 1800
$cnt = List-Count $lv
Write-Output ("matches = " + $cnt)
for ($i = 0; $i -lt [Math]::Min($cnt, 8); $i++) { Write-Output ("  [" + $i + "] " + (Read-ListItem $lv $i)) }
$idx = Find-ListIndexByText $lv "Convert Integer To Text"
if ($idx -lt 0) { Write-Output "找不到函数，取消"; Click-Btn (Find-Child $dlg "Button\|Cancel"); return }
Set-ListSel $lv $idx
Start-Sleep -Milliseconds 700
Click-Btn (Find-Child $dlg "Button\|&OK")
Start-Sleep -Milliseconds 2500

Click-Node $elemTree $acts[$ACTION_INDEX]
Start-Sleep -Milliseconds 1500
$btns = Get-ParamButtons $main
Show-Row $main

$paren = -1
for ($i = 0; $i -lt $btns.Count; $i++) { if ((Get-WindowTitle $btns[$i]) -eq "(") { $paren = $i } }
if ($paren -lt 0) { Write-Output "没有找到函数参数"; return }

$nested = $paren + 1
Write-Output ("=== 嵌套参数 [" + $nested + "] '" + (Get-WindowTitle $btns[$nested]) + "' -> 变量 " + $VAR + " ===")
Click-Btn $btns[$nested]
Start-Sleep -Milliseconds 2500
$d2 = Find-Dialog
Write-Output ("nested dialog = '" + (Get-WindowTitle $d2) + "'")
Click-Btn (Find-Child $d2 "Button\|&Variable")
Start-Sleep -Milliseconds 2000
Set-DialogVariable $d2 $VAR
Start-Sleep -Milliseconds 1500

Write-Output "=== 结果 ==="
Click-Node $elemTree $acts[$ACTION_INDEX]
Start-Sleep -Milliseconds 1200
Show-Row $main
foreach ($a in (Get-ActionNodes $elemTree $TRIGGER)) { Write-Output ("    " + (Get-NodeText $elemTree $a)) }

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
