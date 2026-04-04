# build-plugin.ps1
param([switch]$Install)

$PluginUUID = "com.phewblue.homeops"
$PluginsDir = "$env:APPDATA\Elgato\StreamDeck\Plugins"

Set-Location $PSScriptRoot

Write-Host "Building TypeScript..." -ForegroundColor Cyan
npm run build

if ($Install) {
    $Dest = "$PluginsDir\$PluginUUID.sdPlugin"
    Write-Host "Installing plugin to $Dest..." -ForegroundColor Yellow
    if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force }
    New-Item -ItemType Directory -Path $Dest | Out-Null
    Copy-Item -Path "dist\*"        -Destination $Dest -Recurse
    Copy-Item -Path "imgs\*"        -Destination "$Dest\imgs\" -Recurse
    Copy-Item -Path "manifest.json" -Destination $Dest
    Copy-Item -Path "package.json"  -Destination $Dest
    Copy-Item -Path "node_modules\" -Destination "$Dest\node_modules\" -Recurse
    Write-Host "Plugin installed. Restart Stream Deck software to load it." -ForegroundColor Green
}
