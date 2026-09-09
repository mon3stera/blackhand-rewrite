# Search the New Action picker for several terms and print the matches.

$TRIGGER = "Untitled Trigger 004"
$TERMS = @("Bank Store Integer", "Bank Save", "Store Integer", "Bank")

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

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
$acts = Get-ActionNodes $elemTree $TRIGGER
Click-Node $elemTree $acts[0]
Start-Sleep -Milliseconds 1200

[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000

$dlg = Find-Dialog
$lv = Find-ListByCtlId $dlg 20
Write-Output ("dialog = '" + (Get-WindowTitle $dlg) + "'  lv = " + $lv)

foreach ($term in $TERMS) {
  $null = Set-FilterText $dlg $term 1
  Start-Sleep -Milliseconds 600
  $cnt = List-Count $lv
  Write-Output ("--- [" + $term + "] matches = " + $cnt)
  for ($i = 0; $i -lt [Math]::Min($cnt, 25); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }
}

$cancel = Find-Child $dlg "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
Start-Sleep -Milliseconds 800
