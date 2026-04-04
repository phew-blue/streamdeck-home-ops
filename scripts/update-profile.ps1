$url = "https://github.com/phew-blue/streamdeck-home-ops/releases/latest/download/home-ops.streamDeckProfile"
$dest = "$env:TEMP\home-ops.streamDeckProfile"
Write-Host "Downloading latest profile..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $url -OutFile $dest
Write-Host "Opening profile for import..." -ForegroundColor Green
Start-Process $dest
