$ErrorActionPreference = "Stop"

Write-Host "Checking Docker Compose configuration..."
docker compose config --quiet

if (Get-Command terraform -ErrorAction SilentlyContinue) {
    Write-Host "Checking Terraform formatting..."
    terraform -chdir=terraform fmt -check
} else {
    Write-Warning "Terraform is not installed; skipped Terraform check."
}

Write-Host "Project structure looks good."

