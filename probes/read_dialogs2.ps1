foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[4] -ne "Script Compile Errors" -and $f[4] -ne "Errors") { continue }
  Write-Output ("=== " + $f[4] + " ===")
  foreach ($k in [SC2]::KidsAll([IntPtr][int64]$f[0])) {
    $g = $k.Split("|")
    Write-Output ("  " + $g[1] + " " + $g[4] + " vis=" + $g[2] + " rect=" + $g[3] + " text='" + $g[5] + "'")
  }
}
