# After setting the left side to "Used dialog item", what are the remaining
# sentence slots?

$TRIGGER = "Buff1"

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

function Get-GroupNode([IntPtr]$tree, [string]$trigger, [string]$group) {
  $t = Find-TriggerNode $tree $trigger
  if ($t -eq [IntPtr]::Zero) { return [IntPtr]::Zero }
  $c = Get-Child $tree $t
  while ($c -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $c) -eq $group) { return $c }
    $c = Get-Next $tree $c
  }
  return [IntPtr]::Zero
}

function Get-SentenceButtons([IntPtr]$dlg) {
  $res = @()
  foreach ($k in [SC2]::KidsAll($dlg)) {
    if ($k -match "\|Button\|") {
      $h = [IntPtr][int64]($k.Split("|")[0])
      $r = (Get-RectStr $h).Split(",")
      if ([int]$r[1] -ge 570 -and [int]$r[1] -lt 625) { $res += ,@($h, (Get-WindowTitle $h), $r) }
    }
  }
  return $res
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
Click-Node $elemTree (Get-GroupNode $elemTree $TRIGGER "Conditions")
Start-Sleep -Milliseconds 1200
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]582, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000
$dlg = Find-Dialog
$lv = Find-ListByCtlId $dlg 147
Set-ListSel $lv (Find-ListIndexByText $lv "Comparison")
Start-Sleep -Milliseconds 1500

$btns = Get-SentenceButtons $dlg
Write-Output ("初始按钮: " + (($btns | ForEach-Object { $_[1] }) -join " | "))

Click-Btn $btns[0][0]
Start-Sleep -Milliseconds 2200
$d2 = Find-Dialog
Click-Btn (Find-Child $d2 "Button\|&Function")
Start-Sleep -Milliseconds 2000
if (Select-ListItemByText $d2 "Used Dialog Item" 43 42) { Write-Output "已选 Used Dialog Item" }
Click-Btn (Find-Child $d2 "Button\|&OK")
Start-Sleep -Milliseconds 2200

$btns = Get-SentenceButtons $dlg
Write-Output "=== 左槽设置后的按钮 ==="
foreach ($x in $btns) { Write-Output ("  '" + $x[1] + "'  rect=" + ($x[2] -join ",")) }

Write-Output "=== 逐个点击看打开什么 ==="
foreach ($x in $btns) {
  if ($x[1] -eq "==") { continue }
  Write-Output ("--- '" + $x[1] + "' ---")
  Click-Btn $x[0]
  Start-Sleep -Milliseconds 2000
  $d3 = Find-Dialog
  if ($d3 -eq $dlg) { Write-Output "  （无新对话框）"; continue }
  Write-Output ("  dialog = '" + (Get-WindowTitle $d3) + "'")
  foreach ($k in [SC2]::KidsAll($d3)) {
    if ($k -match "\|Button\||\|SysListView32\|") {
      Write-Output ("    " + $k)
      $h = [IntPtr][int64]($k.Split("|")[0])
      if ($k -match "\|SysListView32\|") {
        $cnt = List-Count $h
        for ($j = 0; $j -lt [Math]::Min($cnt, 6); $j++) { Write-Output ("        [" + $j + "] " + (Read-ListItem $h $j)) }
      }
    }
  }
  $cancel = Find-Child $d3 "Button\|Cancel"
  if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel; Start-Sleep -Milliseconds 1000 }
  Start-Sleep -Milliseconds 500
  $btns = Get-SentenceButtons $dlg
}

$cancel = Find-Child $dlg "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
