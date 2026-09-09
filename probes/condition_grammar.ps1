# Explore the Configure Condition grammar editor: select "Comparison" and dump
# the resulting sentence slots.

$TRIGGER = "BuffChoice"

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

function Show-Grammar([IntPtr]$dlg, [string]$label) {
  Write-Output ("--- " + $label + " ---")
  foreach ($k in [SC2]::KidsAll($dlg)) {
    if ($k -match "\|Static\||\|Button\||\|Edit\||\|SysTreeView32\|") {
      $h = [IntPtr][int64]($k.Split("|")[0])
      if ($h -eq $dlg) { continue }
      Write-Output ("  " + $k)
    }
  }
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
$root = Get-Root $elemTree
$c = Get-Child $elemTree $root
while ($c -ne [IntPtr]::Zero) {
  if ((Get-NodeText $elemTree $c) -eq "Conditions") { Click-Node $elemTree $c }
  $c = Get-Next $elemTree $c
}
Start-Sleep -Milliseconds 1200

[void][SC2]::SendMessage($main, 0x0111, [IntPtr]582, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000

$dlg = Find-Dialog
Write-Output ("dialog = '" + (Get-WindowTitle $dlg) + "'")
Show-Grammar $dlg "初始"

$lv = Find-ListByCtlId $dlg 147
$idx = Find-ListIndexByText $lv "Comparison"
Write-Output ("Comparison index = " + $idx)
if ($idx -lt 0) { return }
Set-ListSel $lv $idx
Start-Sleep -Milliseconds 1500

Show-Grammar $dlg "选中 Comparison 后"

# click each grammar button in the bottom area to see what dialogs they open
$btns = @()
foreach ($k in [SC2]::KidsAll($dlg)) {
  if ($k -match "\|Button\|") {
    $h = [IntPtr][int64]($k.Split("|")[0])
    $r = (Get-RectStr $h).Split(",")
    if ([int]$r[1] -ge 580) { $btns += $h }
  }
}
Write-Output ("底部按钮数 = " + $btns.Count)
foreach ($b in $btns) {
  Write-Output ("  按钮 " + $b + " '" + (Get-WindowTitle $b) + "' rect=" + (Get-RectStr $b))
}
