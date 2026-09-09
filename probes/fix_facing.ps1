# Replace the "facing" argument of the Create Units action with a concrete point.
# The facing expression renders as "(" followed by its nested unit argument
# ("Triggering unit"), which is how we locate the parameter button.

$TRIGGER = "Untitled Trigger 002"
$ACTION_INDEX = 1

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

Click-Node $listTree (Find-TriggerNode $listTree $TRIGGER)
Start-Sleep -Milliseconds 1500
$acts = Get-ActionNodes $elemTree $TRIGGER
$action = $acts[$ACTION_INDEX]
Click-Node $elemTree $action
Start-Sleep -Milliseconds 1800

$btns = Get-ParamButtons $main
$faceIdx = -1
for ($i = 0; $i -lt $btns.Count - 1; $i++) {
  if ((Get-WindowTitle $btns[$i]) -eq "(" -and (Get-WindowTitle $btns[$i + 1]) -eq "Triggering unit") { $faceIdx = $i }
}
Write-Output ("朝向参数按钮索引 = " + $faceIdx)
if ($faceIdx -lt 0) { Write-Output "没找到朝向按钮，放弃"; return }

Click-Btn $btns[$faceIdx]
Start-Sleep -Milliseconds 2500
$dlg = Find-Dialog
Write-Output ("dialog = " + $dlg + " '" + (Get-WindowTitle $dlg) + "'")
if ($dlg -eq [IntPtr]::Zero) { return }

[void](Set-DialogPointFunc $dlg "Start Location Of Player" "Start Location")
Start-Sleep -Milliseconds 1000
foreach ($a in Get-ActionNodes $elemTree $TRIGGER) { Write-Output ("ACTION: " + (Get-NodeText $elemTree $a)) }

Write-Output "=== 保存 ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
Write-Output ("title: " + (Get-WindowTitle $main))
