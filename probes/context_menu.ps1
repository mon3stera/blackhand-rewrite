# Discover the trigger-list context menu: right-click a node and read the popup
# menu (class #32768) so we can find the Delete command id.

$trees = Get-Trees
$listTree = $trees[0]
$main = Find-Main

function Find-TriggerNode([IntPtr]$tree, [string]$name) {
  $cur = Get-Root $tree
  while ($cur -ne [IntPtr]::Zero) {
    if ((Get-NodeText $tree $cur) -eq $name) { return $cur }
    $cur = Get-Next $tree $cur
  }
  return [IntPtr]::Zero
}

function Show-Menu([IntPtr]$hMenu, [string]$indent) {
  $cnt = [SC2]::GetMenuItemCount($hMenu)
  Write-Output ($indent + "items = " + $cnt)
  for ($i = 0; $i -lt $cnt; $i++) {
    $sb = New-Object System.Text.StringBuilder 256
    [void][SC2]::GetMenuStringW($hMenu, $i, $sb, 256, 0x400)
    $id = [SC2]::GetMenuItemID($hMenu, $i)
    $sub = [SC2]::GetSubMenu($hMenu, $i)
    $txt = $sb.ToString()
    Write-Output ($indent + "  [" + $i + "] id=" + $id + " sub=" + $sub + " text=[" + $txt + "]")
    if ($sub -ne [IntPtr]::Zero) { Show-Menu $sub ($indent + "    ") }
  }
}

$node = Find-TriggerNode $listTree "Untitled Trigger 005"
Write-Output ("node = " + $node)
Select-Node $listTree $node
Start-Sleep -Milliseconds 500

# right-click inside the tree client area
$lp = [IntPtr]((300 -bor (300 -shl 16)))
[void][SC2]::SendMessage($listTree, 0x0204, [IntPtr]2, $lp)   # WM_RBUTTONDOWN
[void][SC2]::SendMessage($listTree, 0x0205, [IntPtr]0, $lp)   # WM_RBUTTONUP
Start-Sleep -Milliseconds 1500

Write-Output "=== 顶层窗口（找 #32768 菜单）==="
foreach ($a in [SC2]::Tops([uint32]$P.Id)) { Write-Output ("  " + $a) }

foreach ($a in [SC2]::Tops([uint32]$P.Id)) {
  if ($a -match "\|#32768\|") {
    $h = [IntPtr][int64]($a.Split("|")[0])
    Write-Output ("=== 菜单窗口 " + $h + " ===")
    $m = [SC2]::SendMessage($h, 0x01E1, [IntPtr]0, [IntPtr]::Zero)   # MN_GETHMENU
    Write-Output ("  MN_GETHMENU = " + $m)
    if ($m -ne [IntPtr]::Zero) { Show-Menu $m "    " }
  }
}

# dismiss the popup
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]0, [IntPtr]::Zero)
[void][SC2]::PostMessage($listTree, 0x0100, [IntPtr]0x1B, [IntPtr]1)   # ESC
Start-Sleep -Milliseconds 800
