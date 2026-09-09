# Probe the New Action dialog's filter box with several search terms.

$TRIGGER = "Untitled Trigger 004"

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
if ($stale -ne [IntPtr]::Zero) {
  $c = Find-Child $stale "Button\|Cancel"
  if ($c -ne [IntPtr]::Zero) { Click-Btn $c }
  Start-Sleep -Milliseconds 1200
}

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
$acts = Get-ActionNodes $elemTree $TRIGGER
Click-Node $elemTree $acts[0]
Start-Sleep -Milliseconds 1200

Write-Output "=== New Action (583) ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
Start-Sleep -Milliseconds 3000

$dlg = Find-Dialog
Write-Output ("dialog = " + $dlg + " title='" + (Get-WindowTitle $dlg) + "'")
$lv = Find-ListByCtlId $dlg 20
$search = Find-ChildAll $dlg "Edit\|.*\|id=19"
$desc = Find-ChildAll $dlg "RichEdit20W\|.*\|id=21"
Write-Output ("lv = " + $lv + "  search = " + $search + "  desc = " + $desc)

foreach ($term in @("Modify", "Modify Variable", "Integer", "Set Variable")) {
  Set-EditText $search $term -Nudge
  Start-Sleep -Milliseconds 1800
  $cnt = List-Count $lv
  Write-Output ("--- 搜索 [" + $term + "] matches = " + $cnt)
  for ($i = 0; $i -lt [Math]::Min($cnt, 20); $i++) { Write-Output ("    [" + $i + "] " + (Read-ListItem $lv $i)) }
  if ($cnt -gt 0) {
    Set-ListSel $lv 0
    Start-Sleep -Milliseconds 900
    Write-Output ("    描述 = [" + (Read-ControlText $desc 1024) + "]")
  }
}

$cancel = Find-Child $dlg "Button\|Cancel"
if ($cancel -ne [IntPtr]::Zero) { Click-Btn $cancel }
Start-Sleep -Milliseconds 800
