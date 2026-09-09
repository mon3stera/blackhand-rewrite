# Probe: create a variable (Data > New > New Variable, id 593) and dump its dialog.

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

function Dump-Dialog([IntPtr]$dlg) {
  Write-Output ("=== 对话框 '" + (Get-WindowTitle $dlg) + "' ===")
  foreach ($k in [SC2]::KidsAll($dlg)) {
    Write-Output ("  " + $k)
    $h = [IntPtr][int64]($k.Split("|")[0])
    if ($k -match "\|ComboBox\|") { Read-Combo $h }
    if ($k -match "\|SysListView32\|") {
      $cnt = List-Count $h
      Write-Output ("    LIST count=" + $cnt)
      for ($i = 0; $i -lt [Math]::Min($cnt, 30); $i++) { Write-Output ("      [" + $i + "] " + (Read-ListItem $h $i)) }
    }
    if ($k -match "\|Edit\||\|RichEdit20W\|") { Write-Output ("    text=[" + (Read-ControlText $h 256) + "]") }
  }
}

Click-Node $listTree (Find-TriggerNode $listTree "Untitled Trigger 004")
Start-Sleep -Milliseconds 1500

# select the "Local Variables" node so the new variable lands in this trigger
$root = Get-Root $elemTree
$child = Get-Child $elemTree $root
$lvNode = [IntPtr]::Zero
while ($child -ne [IntPtr]::Zero) {
  if ((Get-NodeText $elemTree $child) -eq "Local Variables") { $lvNode = $child }
  $child = Get-Next $elemTree $child
}
Write-Output ("Local Variables node = " + $lvNode)
if ($lvNode -ne [IntPtr]::Zero) { Click-Node $elemTree $lvNode; Start-Sleep -Milliseconds 1200 }

Write-Output "=== 发送 New Variable (593) ==="
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]593, [IntPtr]::Zero)
Start-Sleep -Milliseconds 2500

foreach ($a in [SC2]::Tops([uint32]$P.Id)) { Write-Output ("  WIN: " + $a) }

$dlg = Find-Dialog
if ($dlg -ne [IntPtr]::Zero) { Dump-Dialog $dlg } else { Write-Output "没有对话框" }

Write-Output "=== 元素树 ==="
Dump-Tree $elemTree ([IntPtr]::Zero) 0 3
