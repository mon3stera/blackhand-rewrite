# Re-set the two Text Message strings (the previous run left a leading space),
# then save and report the resulting action texts.

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

function Set-ActionTextParam([IntPtr]$elemTree, [IntPtr]$action, [int]$idx, [string]$text) {
  Click-Node $elemTree $action
  Start-Sleep -Milliseconds 1500
  $btns = Get-ParamButtons (Find-Main)
  Click-Btn $btns[$idx]
  Start-Sleep -Milliseconds 2500
  $dlg = Find-Dialog
  if ($dlg -eq [IntPtr]::Zero) { Write-Host "    没有对话框"; return }
  Write-Host ("    dialog = " + $dlg + " '" + (Get-WindowTitle $dlg) + "'")
  Set-DialogText $dlg $text
}

foreach ($spec in @(@("Untitled Trigger 003", "spawn"), @("Untitled Trigger 004", "unit died"))) {
  $name = $spec[0]; $text = $spec[1]
  Click-Node $listTree (Find-TriggerNode $listTree $name)
  Start-Sleep -Milliseconds 1500
  $acts = Get-ActionNodes $elemTree $name
  Write-Output ("=== " + $name + " 文本 -> '" + $text + "' ===")
  Set-ActionTextParam $elemTree $acts[0] 0 $text
  foreach ($a in Get-ActionNodes $elemTree $name) { Write-Output ("    ACTION: " + (Get-NodeText $elemTree $a)) }
}

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
