$main = Find-Main
$bar = [SC2]::GetMenu($main)
$n = [SC2]::GetMenuItemCount($bar)
for ($i = 0; $i -lt $n; $i++) {
  $sb = New-Object System.Text.StringBuilder 256
  [void][SC2]::GetMenuStringW($bar, $i, $sb, 256, 0x0400)
  if ($sb.ToString() -notmatch "Module") { continue }
  $sub = [SC2]::GetSubMenu($bar, $i)
  $c = [SC2]::GetMenuItemCount($sub)
  for ($j = 0; $j -lt $c; $j++) {
    $t = New-Object System.Text.StringBuilder 256
    [void][SC2]::GetMenuStringW($sub, $j, $t, 256, 0x0400)
    Write-Output ("  " + $t.ToString() + "  id=" + [SC2]::GetMenuItemID($sub, $j))
  }
}
