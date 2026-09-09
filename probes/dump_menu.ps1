# Dump the editor main menu (with command ids) so menu commands can be sent
# via WM_COMMAND instead of keystrokes.

$main = Find-Main
$bar = [SC2]::GetMenu($main)
Write-Output ("menubar = " + $bar)

function Dump-Menu([IntPtr]$menu, [string]$prefix) {
  $n = [SC2]::GetMenuItemCount($menu)
  for ($i = 0; $i -lt $n; $i++) {
    $sb = New-Object System.Text.StringBuilder 256
    [void][SC2]::GetMenuStringW($menu, $i, $sb, 256, 0x0400)   # MF_BYPOSITION
    $id = [SC2]::GetMenuItemID($menu, $i)
    $sub = [SC2]::GetSubMenu($menu, $i)
    $label = $sb.ToString()
    if ($sub -ne [IntPtr]::Zero) {
      Write-Output ($prefix + $label + "  [submenu]")
      if ($prefix.Length -lt 4) { Dump-Menu $sub ($prefix + "  ") }
    } else {
      Write-Output ($prefix + $label + "  id=" + $id)
    }
  }
}
Dump-Menu $bar ""
