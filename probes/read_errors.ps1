# Read the compile-error list and the Scintilla preview from the error dialog.

foreach ($w in [SC2]::Tops([uint32]$P.Id)) {
  $f = $w.Split("|")
  if ($f[4] -ne "Script Compile Errors") { continue }
  $dlg = [IntPtr][int64]$f[0]
  foreach ($k in [SC2]::KidsAll($dlg)) {
    $g = $k.Split("|")
    $h = [IntPtr][int64]$g[0]
    if ($g[1] -eq "SysListView32" -and $g[2] -eq "True") {
      $n = List-Count $h
      Write-Output ("--- 列表 " + $g[4] + " 项数=" + $n)
      for ($i = 0; $i -lt [Math]::Min($n, 20); $i++) {
        Write-Output ("  [" + $i + "] " + (Read-ListItem $h $i))
      }
    }
    if ($g[1] -eq "Scintilla") {
      [void][SC2]::SendMessage($h, 0x000D, [IntPtr]4096, $RTEXT)
      Start-Sleep -Milliseconds 300
      $txt = Read-RemoteString 4096
      Write-Output "--- Scintilla 文本 ---"
      Write-Output $txt
    }
  }
}
