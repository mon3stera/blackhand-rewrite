foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[4] -ne "Errors") { continue }
  foreach ($k in [SC2]::KidsAll([IntPtr][int64]$f[0])) {
    $g = $k.Split("|")
    if ($g[1] -ne "SysListView32") { continue }
    $lv = [IntPtr][int64]$g[0]
    Write-Output ("--- Errors 列表 项数=" + (List-Count $lv))
    for ($i = 0; $i -lt (List-Count $lv); $i++) { Write-Output ("  [" + $i + "] " + (Read-ListItem $lv $i)) }
  }
}
