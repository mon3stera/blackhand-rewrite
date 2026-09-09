$main = Find-Main
Write-Output ("main = " + (Get-WindowTitle $main))
foreach ($pat in @("^&?Save$", "^&?Open", "New &Trigger", "^&?Delete", "^&?Triggers", "Test Document", "^&?Rename", "^&?Variables")) {
  Write-Output ("  " + $pat + " -> " + (Get-MenuId $main $pat))
}
