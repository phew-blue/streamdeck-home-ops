# build-plugin.ps1
param([switch]$Install)

$PluginUUID = "com.phew.blue.homeops"
$PluginsDir = "$env:APPDATA\Elgato\StreamDeck\Plugins"

Set-Location $PSScriptRoot

# Ensure dependencies are installed
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Cyan
    npm install
}

Write-Host "Building TypeScript..." -ForegroundColor Cyan
npm run build

if ($Install) {
    $Dest = "$PluginsDir\$PluginUUID.sdPlugin"
    Write-Host "Installing plugin to $Dest..." -ForegroundColor Yellow
    if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force }

    # Create destination directories
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    New-Item -ItemType Directory -Force -Path "$Dest\imgs" | Out-Null
    New-Item -ItemType Directory -Force -Path "$Dest\node_modules" | Out-Null

    Copy-Item -Path "dist\*"        -Destination $Dest -Recurse -Force
    Copy-Item -Path "imgs\*"        -Destination "$Dest\imgs\" -Recurse -Force
    Copy-Item -Path "manifest.json" -Destination $Dest -Force
    Copy-Item -Path "package.json"  -Destination $Dest -Force
    Copy-Item -Path "node_modules\*" -Destination "$Dest\node_modules\" -Recurse -Force
    Write-Host "Plugin installed. Restart Stream Deck software to load it." -ForegroundColor Green
}
