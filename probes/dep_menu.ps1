$main = Find-Main
$bar = [SC2]::GetMenu($main)
$n = [SC2]::GetMenuItemCount($bar)
for ($i = 0; $i -lt $n; $i++) {
  $sb = New-Object System.Text.StringBuilder 256
  [void][SC2]::GetMenuStringW($bar, $i, $sb, 256, 0x0400)
  $top = $sb.ToString()
  $sub = [SC2]::GetSubMenu($bar, $i)
  if ($sub -ne [IntPtr]::Zero) {
    $m = [SC2]::GetMenuItemCount($sub)
    for ($j = 0; $j -lt $m; $j++) {
      $sb2 = New-Object System.Text.StringBuilder 256
      [void][SC2]::GetMenuStringW($sub, $j, $sb2, 256, 0x0400)
      $lbl = $sb2.ToString()
      if ($lbl.Trim() -ne "") { Write-Output ($top + " > " + $lbl + "  id=" + [SC2]::GetMenuItemID($sub, $j)) }
    }
  }
}
