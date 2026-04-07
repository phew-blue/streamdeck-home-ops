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
if ($LASTEXITCODE -ne 0) { Write-Error "Build failed"; exit 1 }

if ($Install) {
    $Dest = "$PluginsDir\$PluginUUID.sdPlugin"
    Write-Host "Installing plugin to $Dest..." -ForegroundColor Yellow
    if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force }

    # Create destination directories
    New-Item -ItemType Directory -Force -Path "$Dest\bin" | Out-Null
    New-Item -ItemType Directory -Force -Path "$Dest\imgs" | Out-Null

    Copy-Item -Path "dist\plugin.js"        -Destination "$Dest\bin\plugin.js" -Force
    Copy-Item -Path "dist\plugin.js.map"    -Destination "$Dest\bin\plugin.js.map" -Force -ErrorAction SilentlyContinue
    Copy-Item -Path "imgs\*"               -Destination "$Dest\imgs\" -Recurse -Force
    Copy-Item -Path "manifest.json"        -Destination $Dest -Force
    Write-Host "Plugin installed. Restart Stream Deck software to load it." -ForegroundColor Green
}
