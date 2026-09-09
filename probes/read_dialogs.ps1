# Read text from the editor's modal error dialogs (no clicks, no focus change).

function Dump-Dialog([string]$title) {
  foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
    $f = $w.Split("|")
    if ($f[4] -ne $title) { continue }
    Write-Output ("=== " + $title + " ===")
    foreach ($k in [SC2]::KidsAll([IntPtr][int64]$f[0])) {
      $g = $k.Split("|")
      if ($g[5] -ne "") { Write-Output ("  " + $g[1] + " " + $g[4] + " : " + $g[5]) }
    }
  }
}

Dump-Dialog "Script Compile Errors"
Dump-Dialog "Errors"
