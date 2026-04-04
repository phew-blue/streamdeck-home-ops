param([string]$InstallPath = "C:\StreamDeck-HomeOps")

Write-Host "Installing StreamDeck Home Ops scripts to $InstallPath..." -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path "$InstallPath\scripts\launchers" | Out-Null

Copy-Item -Path "$PSScriptRoot\*.ps1" -Destination "$InstallPath\scripts\" -Exclude "install.ps1"

if (Test-Path "$PSScriptRoot\launchers\") {
    Copy-Item -Path "$PSScriptRoot\launchers\*" -Destination "$InstallPath\scripts\launchers\" -Recurse
}

Write-Host "Done! Scripts installed to $InstallPath\scripts\" -ForegroundColor Green
Write-Host "Next: import profile\home-ops.streamDeckProfile in the Elgato Stream Deck app." -ForegroundColor Cyan
