$main = Find-Main
Write-Output ("main = " + (Get-WindowTitle $main))

function Dump-Menu([IntPtr]$menu, [string]$prefix) {
  $n = [SC2]::GetMenuItemCount($menu)
  for ($i = 0; $i -lt $n; $i++) {
    $sb = New-Object System.Text.StringBuilder 256
    [void][SC2]::GetMenuStringW($menu, $i, $sb, 256, 0x0400)
    $id = [SC2]::GetMenuItemID($menu, $i)
    $sub = [SC2]::GetSubMenu($menu, $i)
    if ($sub -ne [IntPtr]::Zero) { if ($prefix.Length -lt 2) { Dump-Menu $sub ($prefix + "  ") } }
    else { if ($prefix.Length -lt 2) { Write-Output ($prefix + $sb.ToString() + " id=" + $id) } }
  }
}
Dump-Menu ([SC2]::GetMenu($main)) ""

[void][SC2]::SendMessage($main, 0x0111, [IntPtr]11, [IntPtr]::Zero)
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Seconds 1
  foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
    $f = $w.Split("|")
    if ($f[4] -eq "Open Document" -and $f[2] -eq "True") { Write-Output ("[open dialog " + ($i+1) + "s]"); exit }
  }
}
Write-Output "!! 20s 内没有 Open Document"
foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[2] -eq "True") { Write-Output ("  visible top: " + $f[4]) }
}
