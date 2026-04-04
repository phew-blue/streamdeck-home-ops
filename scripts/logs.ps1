param([string]$App, [string]$Namespace)
Write-Host "Fetching logs for $App in $Namespace..." -ForegroundColor Cyan
kubectl logs -n $Namespace -l app.kubernetes.io/name=$App --tail=50 -f
Read-Host "`nPress Enter to close"
