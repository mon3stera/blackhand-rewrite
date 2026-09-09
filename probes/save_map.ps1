# Save the current document (menu command 15) and report the window title
# before/after so we can tell whether the dirty marker (*) cleared.

$main = Find-Main
Write-Output ("before: " + (Get-WindowTitle $main))
[void][SC2]::SendMessage($main, 0x0111, [IntPtr]15, [IntPtr]::Zero)
Start-Sleep -Milliseconds 6000
foreach ($a in [SC2]::Tops([uint32]$P.Id)) { Write-Output ("  WIN: " + $a) }
Write-Output ("after: " + (Get-WindowTitle $main))
