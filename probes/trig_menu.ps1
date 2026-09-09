$main = Find-Main
$bar = [SC2]::GetMenu($main)
function Walk([IntPtr]$menu, [string]$prefix) {
  $n = [SC2]::GetMenuItemCount($menu)
  for ($i = 0; $i -lt $n; $i++) {
    $sb = New-Object System.Text.StringBuilder 256
    [void][SC2]::GetMenuStringW($menu, $i, $sb, 256, 0x0400)
    $label = $sb.ToString(); $id = [SC2]::GetMenuItemID($menu, $i); $sub = [SC2]::GetSubMenu($menu, $i)
    if ($sub -ne [IntPtr]::Zero) { Walk $sub ($prefix + "  ") }
    elseif ($label -match "Trigger|Variable|New") { Write-Output ($prefix + $label + "  id=" + $id) }
  }
}
Walk $bar ""
