param([string]$App, [string]$Namespace)
Write-Host "Reconciling HelmRelease $App in $Namespace..." -ForegroundColor Yellow
flux reconcile helmrelease $App -n $Namespace --with-source
Write-Host "Done." -ForegroundColor Green
Read-Host "`nPress Enter to close"
