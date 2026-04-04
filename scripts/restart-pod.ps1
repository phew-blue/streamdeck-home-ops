param([string]$App, [string]$Namespace)
Write-Host "Restarting $App in $Namespace..." -ForegroundColor Yellow
kubectl rollout restart deployment/$App -n $Namespace
Write-Host "Done." -ForegroundColor Green
Read-Host "`nPress Enter to close"
