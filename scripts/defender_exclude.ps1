@' 
  defender_exclude.ps1
  Adds project build output to Windows Defender exclusion list.
  Run as Administrator: right-click → "Run with PowerShell"
'@

$paths = @(
    "$PSScriptRoot\out",
    "$PSScriptRoot\build",
    "$PSScriptRoot\Indonime.exe"
)

$count = 0
foreach ($p in $paths) {
    $resolved = (Resolve-Path $p -ErrorAction SilentlyContinue).Path
    $target = if ($resolved) { $resolved } else { $p }
    
    $exists = Get-MpPreference | Select-Object -ExpandProperty ExclusionPath | Where-Object { $_ -eq $target }
    if (-not $exists) {
        Add-MpPreference -ExclusionPath $target -ErrorAction SilentlyContinue
        Write-Host "[+] Added: $target"
        $count++
    } else {
        Write-Host "[=] Already excluded: $target"
    }
}

Write-Host "Done. $count path(s) added to Defender exclusions."
pause