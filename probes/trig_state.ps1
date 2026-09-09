$main = Find-Main
Write-Output ("title = " + (Get-WindowTitle $main))
$bar = [SC2]::GetMenu($main)
function Walk([IntPtr]$menu, [string]$prefix) {
  $n = [SC2]::GetMenuItemCount($menu)
  for ($i = 0; $i -lt $n; $i++) {
    $sb = New-Object System.Text.StringBuilder 256
    [void][SC2]::GetMenuStringW($menu, $i, $sb, 256, 0x0400)
    $sub = [SC2]::GetSubMenu($menu, $i)
    $id = [SC2]::GetMenuItemID($menu, $i)
    if ($sub -ne [IntPtr]::Zero) { Walk $sub ($prefix + "  ") }
    elseif ($id -eq 617 -or $id -eq 616 -or $id -eq 620) {
      $state = [SC2]::GetMenuState($menu, $i, 0x0400)
      $enabled = -not (($state -band 0x3) -eq 0x3)
      Write-Output ("  id=" + $id + "  state=0x" + $state.ToString("X") + "  enabled=" + $enabled + "  " + $sb.ToString())
    }
  }
}
Walk $bar ""
$focused = Get-Focus
Write-Output ("focused = " + $focused)
