# Add bank-based verification to Buff1: after creating the Marines, open a bank,
# store a marker and save it.  Reading the bank file proves the click path ran.

$trees = Get-Trees
$listTree = $trees[0]; $elemTree = $trees[1]
$main = Find-Main

function Find-TriggerNode([string]$name) {
  $cur = Get-Root $listTree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $listTree $cur) -eq $name) { return $cur }
    $cur = Get-Next $listTree $cur
  }
  return [IntPtr]::Zero
}

function Select-Trigger([string]$name) {
  $other = $null
  $cur = Get-Root $listTree
  while ($cur -ne [IntPtr]::Zero) {
    $t = Get-NodeText $listTree $cur
    if ($t -ne $name -and $t -notmatch "=") { $other = $cur; break }
    $cur = Get-Next $listTree $cur
  }
  if ($other -ne [IntPtr]::Zero) { Select-Node $listTree $other; Start-Sleep -Milliseconds 300; Click-Node $listTree $other; Start-Sleep -Milliseconds 1000 }
  $node = Find-TriggerNode $name
  if ($node -eq [IntPtr]::Zero) { return $false }
  Select-Node $listTree $node
  Start-Sleep -Milliseconds 300
  Click-Node $listTree $node
  Start-Sleep -Milliseconds 1600
  return ((Get-NodeText $elemTree (Get-Root $elemTree)) -eq $name)
}

function Get-GroupChildren([string]$trigger, [string]$group) {
  $root = Get-Root $elemTree
  if ((Get-NodeText $elemTree $root) -ne $trigger) { return @() }
  $c = Get-Child $elemTree $root
  while ($c -ne [IntPtr]::Zero) {
    if ((Get-NodeText $elemTree $c) -eq $group) {
      $res = @(); $a = Get-Child $elemTree $c
      while ($a -ne [IntPtr]::Zero) { $res += $a; $a = Get-Next $elemTree $a }
      return $res
    }
    $c = Get-Next $elemTree $c
  }
  return @()
}

function Add-Action([string]$trigger, [string]$search) {
  $acts = Get-GroupChildren $trigger "Actions"
  Click-Node $elemTree $acts[$acts.Count - 1]
  Start-Sleep -Milliseconds 1100
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]583, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 3000
  $dlg = Find-Dialog
  if (-not (Select-ListItemByText $dlg $search 20 19)) {
    Write-Output ("  !! 找不到动作 " + $search)
    Click-Btn (Find-Child $dlg "Button\|Cancel")
    return [IntPtr]::Zero
  }
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2200
  $acts = Get-GroupChildren $trigger "Actions"
  return $acts[$acts.Count - 1]
}

function Set-ParamText([IntPtr]$node, [int]$pi, [string]$text) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $pb = Get-ParamButtons $main
  Click-Btn $pb[$pi]; Start-Sleep -Milliseconds 1800
  Set-DialogText (Find-Dialog) $text
  Start-Sleep -Milliseconds 900
}

function Set-ParamInt([IntPtr]$node, [int]$pi, [string]$val) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $pb = Get-ParamButtons $main
  Click-Btn $pb[$pi]; Start-Sleep -Milliseconds 1800
  Set-DialogInt (Find-Dialog) $val
  Start-Sleep -Milliseconds 900
}

function Set-ParamFunc([IntPtr]$node, [int]$pi, [string]$func) {
  Click-Node $elemTree $node; Start-Sleep -Milliseconds 1000
  $pb = Get-ParamButtons $main
  Click-Btn $pb[$pi]; Start-Sleep -Milliseconds 2000
  $d = Find-Dialog
  $fb = Find-Child $d "Button\|&Function"
  if ($fb -ne [IntPtr]::Zero) { Click-Btn $fb; Start-Sleep -Milliseconds 1800 }
  $listId = 43; $editId = 42
  if (Find-ListByCtlId $d 43 -eq [IntPtr]::Zero) { $listId = 59; $editId = 58 }
  if (-not (Select-ListItemByText $d $func $listId $editId)) {
    Write-Output ("    !! 找不到函数 " + $func)
    Click-Btn (Find-Child $d "Button\|Cancel")
    return
  }
  Click-Btn (Find-Child $d "Button\|&OK")
  Start-Sleep -Milliseconds 2000
}

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

if (-not (Select-Trigger "Buff1")) { Write-Output "!! 选择 Buff1 失败"; return }

Write-Output "=== Open Bank ==="
$n = Add-Action "Buff1" "Open Bank"
if ($n -ne [IntPtr]::Zero) {
  Click-Node $elemTree $n; Start-Sleep -Milliseconds 1000
  $i = 0; foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
  Set-ParamText $n 0 "verify"
  Write-Output ("  -> " + (Get-NodeText $elemTree $n))
}

Write-Output "=== Store Integer ==="
$n = Add-Action "Buff1" "Store Integer"
if ($n -ne [IntPtr]::Zero) {
  Click-Node $elemTree $n; Start-Sleep -Milliseconds 1000
  $i = 0; foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
  Set-ParamFunc $n 0 "Last Created Bank"
  Set-ParamText $n 1 "buffs"
  Set-ParamText $n 2 "Buff1"
  Set-ParamInt $n 3 "1"
  Write-Output ("  -> " + (Get-NodeText $elemTree $n))
}

Write-Output "=== Save Bank ==="
$n = Add-Action "Buff1" "Save Bank"
if ($n -ne [IntPtr]::Zero) {
  Click-Node $elemTree $n; Start-Sleep -Milliseconds 1000
  $i = 0; foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
  Set-ParamFunc $n 0 "Last Created Bank"
  Write-Output ("  -> " + (Get-NodeText $elemTree $n))
}

Write-Output "=== Buff1 动作 ==="
foreach ($a in (Get-GroupChildren "Buff1" "Actions")) { Write-Output ("  " + (Get-NodeText $elemTree $a)) }

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
