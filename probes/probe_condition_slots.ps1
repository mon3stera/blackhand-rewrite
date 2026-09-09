# Explore the Comparison condition sentence: what do the parameter slots offer?

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

function Dump-Sentence([IntPtr]$dlg, [string]$label) {
  Write-Output ("--- " + $label + " ---")
  foreach ($k in [SC2]::KidsAll($dlg)) {
    if ($k -match "\|Button\||\|Static\|") {
      $h = [IntPtr][int64]($k.Split("|")[0])
      $r = (Get-RectStr $h).Split(",")
      if ([int]$r[1] -ge 575) { Write-Output ("  " + $k) }
    }
  }
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
Write-Output ("dialog = '" + (Get-WindowTitle $dlg) + "'")

$lv = Find-ListByCtlId $dlg 147
$idx = Find-ListIndexByText $lv "Comparison"
Set-ListSel $lv $idx
Start-Sleep -Milliseconds 1500
Dump-Sentence $dlg "默认句子"

# click the leftmost parameter button "("
$targets = @()
foreach ($k in [SC2]::KidsAll($dlg)) {
  if ($k -match "\|Button\|") {
    $h = [IntPtr][int64]($k.Split("|")[0])
    $r = (Get-RectStr $h).Split(",")
    if ([int]$r[1] -ge 575 -and [int]$r[1] -lt 620) { $targets += $h }
  }
}
Write-Output ("句子按钮: " + (($targets | ForEach-Object { $_ }) -join ","))

foreach ($b in $targets) {
  $title = Get-WindowTitle $b
  Write-Output ("=== 点击 '" + $title + "' ===")
  Click-Btn $b
  Start-Sleep -Milliseconds 2200
  $d2 = Find-Dialog
  if ($d2 -eq $dlg) { Write-Output "  （没有新对话框）"; continue }
  Write-Output ("  dialog = '" + (Get-WindowTitle $d2) + "'")
  foreach ($k in [SC2]::KidsAll($d2)) {
    if ($k -match "\|Button\||\|Edit\||\|SysListView32\||\|ComboBox\|") {
      Write-Output ("    " + $k)
      $h = [IntPtr][int64]($k.Split("|")[0])
      if ($k -match "\|SysListView32\|") {
        $cnt = List-Count $h
        for ($j = 0; $j -lt [Math]::Min($cnt, 8); $j++) { Write-Output ("        [" + $j + "] " + (Read-ListItem $h $j)) }
      }
    }
  }
  $cancel = Find-Child $d2 "Button\|Cancel"
  if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel; Start-Sleep -Milliseconds 1000 }
}

$cancel = Find-Child $dlg "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
