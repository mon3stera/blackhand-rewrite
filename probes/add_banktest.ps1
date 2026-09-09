# Create a temporary BankTest trigger (Map initialization -> open/store/save a
# bank) so the bank pipeline can be verified without any user input.

$TRIGGER = "BankTest"
$AFTER = "Untitled Trigger 004"

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

function Get-GroupNode([string]$trigger, [string]$group) {
  $root = Get-Root $elemTree
  if ((Get-NodeText $elemTree $root) -ne $trigger) { return [IntPtr]::Zero }
  $c = Get-Child $elemTree $root
  while ($c -ne [IntPtr]::Zero) {
    if ((Get-NodeText $elemTree $c) -eq $group) { return $c }
    $c = Get-Next $elemTree $c
  }
  return [IntPtr]::Zero
}

function Add-Event([string]$trigger, [string]$search) {
  Click-Node $elemTree (Get-GroupNode $trigger "Events")
  Start-Sleep -Milliseconds 1100
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]581, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 3000
  $dlg = Find-Dialog
  if (-not (Select-ListItemByText $dlg $search 20 19)) {
    Write-Output ("  !! 找不到事件 " + $search)
    Click-Btn (Find-Child $dlg "Button\|Cancel")
    return
  }
  Click-Btn (Find-Child $dlg "Button\|&OK")
  Start-Sleep -Milliseconds 2000
}

function Add-Action([string]$trigger, [string]$search) {
  $acts = Get-GroupChildren $trigger "Actions"
  if ($acts.Count -gt 0) { Click-Node $elemTree $acts[$acts.Count - 1] } else { Click-Node $elemTree (Get-GroupNode $trigger "Actions") }
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

$stale = Find-Dialog
if ($stale -ne [IntPtr]::Zero) { Click-Btn (Find-Child $stale "Button\|Cancel"); Start-Sleep -Milliseconds 1000 }

if ((Find-TriggerNode $TRIGGER) -ne [IntPtr]::Zero) {
  Write-Output ($TRIGGER + " 已存在，先删除")
  Select-Trigger $TRIGGER
  [void][SC2]::SendMessage($main, 0x0111, [IntPtr]536, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 1500
}

Write-Output "=== 新建 BankTest ==="
Select-Trigger $AFTER
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]580, [IntPtr]::Zero)
Start-Sleep -Milliseconds 2500
foreach ($k in [SC2]::KidsAll($main)) {
  if ($k -match "\|Edit\|" -and $k -match "Untitled Trigger") {
    $edit = [IntPtr][int64]($k.Split("|")[0])
    Set-EditText $edit $TRIGGER
    Start-Sleep -Milliseconds 500
    [void][SC2]::PostMessage($edit, 0x0100, [IntPtr]0x0D, [IntPtr]1)
    [void][SC2]::PostMessage($edit, 0x0101, [IntPtr]0x0D, [IntPtr]1)
    Start-Sleep -Milliseconds 1500
  }
}
Select-Trigger $TRIGGER

Add-Event $TRIGGER "Map Initialization"

$n = Add-Action $TRIGGER "Open Bank"
if ($n -ne [IntPtr]::Zero) {
  Set-ParamText $n 0 "verify"
  Write-Output ("  " + (Get-NodeText $elemTree $n))
}

$n = Add-Action $TRIGGER "Store Integer"
if ($n -ne [IntPtr]::Zero) {
  Click-Node $elemTree $n; Start-Sleep -Milliseconds 1000
  $i = 0; foreach ($b in (Get-ParamButtons $main)) { Write-Output ("    param[" + $i + "] '" + (Get-WindowTitle $b) + "'"); $i++ }
  Set-ParamInt $n 0 "7"
  Set-ParamText $n 1 "k"
  Set-ParamText $n 2 "s"
  Write-Output ("  " + (Get-NodeText $elemTree $n))
}

$n = Add-Action $TRIGGER "Save Bank"
if ($n -ne [IntPtr]::Zero) { Write-Output ("  " + (Get-NodeText $elemTree $n)) }

Write-Output "=== BankTest 内容 ==="
foreach ($g in @("Events", "Actions")) {
  foreach ($a in (Get-GroupChildren $TRIGGER $g)) { Write-Output ("  " + (Get-NodeText $elemTree $a)) }
}

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
