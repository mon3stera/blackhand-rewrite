# Dump the editor's menu tree (labels + command ids) so we can find Delete etc.

$main = Find-Main
$menu = [SC2]::GetMenu($main)
Write-Output ("main = " + $main + "  menu = " + $menu)

function Show-Menu([IntPtr]$hMenu, [string]$indent) {
  $cnt = [SC2]::GetMenuItemCount($hMenu)
  for ($i = 0; $i -lt $cnt; $i++) {
    $sb = New-Object System.Text.StringBuilder 256
    [void][SC2]::GetMenuStringW($hMenu, $i, $sb, 256, 0x400)
    $id = [SC2]::GetMenuItemID($hMenu, $i)
    $sub = [SC2]::GetSubMenu($hMenu, $i)
    Write-Output ($indent + "[" + $i + "] id=" + $id + " text=[" + $sb.ToString() + "]")
    if ($sub -ne [IntPtr]::Zero) { Show-Menu $sub ($indent + "    ") }
  }
}

Show-Menu $menu ""
