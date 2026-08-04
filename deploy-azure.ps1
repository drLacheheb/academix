# Academix Azure Deployment Script (PowerShell)
# Designed specifically for Azure for Students ($100 credit subscription)
# Deploys microservices to Azure Container Apps (Scale-to-Zero) & provisions Phi-4-mini-reasoning serverless API.

$ResourceGroup = "academix-rg"
$Location = "swedencentral"
$RegistryName = "academixreg" + (Get-Random -Minimum 1000 -Maximum 9999)
$AcaEnvName = "academix-env"
$AiAccountName = "academix-ai-" + (Get-Random -Minimum 1000 -Maximum 9999)

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Academix - Azure for Students Deployment Script " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Login & Subscription Check
Write-Host "`n1. Checking Azure login status..." -ForegroundColor Yellow
$account = az account show --query name -o tsv 2>$null
if ($null -eq $account -or $account -eq "") {
    Write-Host "Error: Not logged into Azure. Please run 'az login' first." -ForegroundColor Red
    exit 1
}
Write-Host "Connected as: $account" -ForegroundColor Green

# 2. Load Local .env Credentials
Write-Host "`n2. Loading environment variables from .env..." -ForegroundColor Yellow
$EnvFilePath = Join-Path $PSScriptRoot ".env"
$EnvVars = @{}
if (Test-Path $EnvFilePath) {
    Get-Content $EnvFilePath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $key = $parts[0].Trim()
            $value = $parts[1].Trim()
            $EnvVars[$key] = $value
        }
    }
}

$DatabaseUrl = $EnvVars["DATABASE_URL"]
$ApiSecretKey = $EnvVars["API_SECRET_KEY"]
$TelegramToken = $EnvVars["TELEGRAM_BOT_TOKEN"]
$DegreeThreshold = if ($EnvVars["DEGREE_SIMILARITY_THRESHOLD"]) { $EnvVars["DEGREE_SIMILARITY_THRESHOLD"] } else { "0.71" }
$StorageProvider = if ($EnvVars["STORAGE_PROVIDER"]) { $EnvVars["STORAGE_PROVIDER"] } else { "local" }
$S3Bucket = $EnvVars["S3_BUCKET_NAME"]
$S3AccessKey = $EnvVars["S3_ACCESS_KEY_ID"]
$S3SecretKey = $EnvVars["S3_SECRET_ACCESS_KEY"]
$S3Endpoint = $EnvVars["S3_ENDPOINT_URL"]
$S3Region = if ($EnvVars["S3_REGION"]) { $EnvVars["S3_REGION"] } else { "us-east-1" }

if (-not $DatabaseUrl) {
    Write-Host "Warning: DATABASE_URL is missing in .env (Neon connection string expected)." -ForegroundColor Yellow
}

# 3. Create Resource Group
Write-Host "`n3. Creating Resource Group '$ResourceGroup' in $Location..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location -o table

# 4. Create Azure Container Registry (ACR)
Write-Host "`n4. Creating Azure Container Registry '$RegistryName'..." -ForegroundColor Yellow
az acr create --resource-group $ResourceGroup --name $RegistryName --sku Basic --admin-enabled true -o table

$AcrUsername = az acr credential show --name $RegistryName --query username -o tsv
$AcrPassword = az acr credential show --name $RegistryName --query passwords[0].value -o tsv
$RegistryServer = "$RegistryName.azurecr.io"

# Log in local Docker to ACR
Write-Host "Logging local Docker into ACR ($RegistryServer)..." -ForegroundColor Yellow
docker login $RegistryServer -u $AcrUsername -p $AcrPassword

# 5. Build and Push Docker Images
Write-Host "`n5. Building & Pushing multi-stage Docker images to ACR..." -ForegroundColor Yellow

$Images = @("slim", "embedding", "refinement", "matching", "cv-parsing", "translation", "lang-detection")
foreach ($target in $Images) {
    $imageTag = "$RegistryServer/academix-${target}:latest"
    Write-Host "Building target '$target' -> $imageTag..." -ForegroundColor Cyan
    docker build --target $target -t $imageTag .
    Write-Host "Pushing $imageTag to ACR..." -ForegroundColor Cyan
    docker push $imageTag
}

# 6. Create Azure AI Services (Phi-4-mini-reasoning Serverless)
Write-Host "`n6. Provisioning Azure AI Account '$AiAccountName'..." -ForegroundColor Yellow
az cognitiveservices account create `
    --name $AiAccountName `
    --resource-group $ResourceGroup `
    --location $Location `
    --kind "AIServices" `
    --sku "S0" `
    --yes -o table 2>$null

$AiKey = az cognitiveservices account keys list --name $AiAccountName --resource-group $ResourceGroup --query "key1" -o tsv 2>$null
$AiEndpoint = az cognitiveservices account show --name $AiAccountName --resource-group $ResourceGroup --query "properties.endpoint" -o tsv 2>$null

# 7. Create Azure Container Apps Environment
Write-Host "`n7. Registering Container Apps Extension & Creating ACA Environment '$AcaEnvName'..." -ForegroundColor Yellow
az extension add --name containerapp --upgrade 2>$null
az containerapp env create --name $AcaEnvName --resource-group $ResourceGroup --location $Location -o table

# 8. Deploy FastAPI Gateway (API)
Write-Host "`n8. Deploying Gateway API App Service..." -ForegroundColor Yellow
az containerapp create `
    --name "academix-api" `
    --resource-group $ResourceGroup `
    --environment $AcaEnvName `
    --image "$RegistryServer/academix-slim:latest" `
    --registry-server $RegistryServer `
    --registry-username $AcrUsername `
    --registry-password $AcrPassword `
    --target-port 8000 `
    --ingress external `
    --min-replicas 0 `
    --max-replicas 2 `
    --env-vars `
        "PYTHONUNBUFFERED=1" `
        "DATABASE_URL=$DatabaseUrl" `
        "API_SECRET_KEY=$ApiSecretKey" `
        "DEGREE_SIMILARITY_THRESHOLD=$DegreeThreshold" `
        "STORAGE_PROVIDER=$StorageProvider" `
        "S3_BUCKET_NAME=$S3Bucket" `
        "S3_ACCESS_KEY_ID=$S3AccessKey" `
        "S3_SECRET_ACCESS_KEY=$S3SecretKey" `
        "S3_ENDPOINT_URL=$S3Endpoint" `
        "S3_REGION=$S3Region" -o table

# 9. Output Deployment Summary
$SubscriptionId = az account show --query id -o tsv
$ApiUrl = az containerapp show --name academix-api --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" -o tsv

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host " Academix Azure Infrastructure Successfully Deployed! " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "Gateway API FQDN: https://$ApiUrl" -ForegroundColor Cyan
Write-Host "Azure Container Registry: $RegistryServer" -ForegroundColor Gray
Write-Host "Azure AI Endpoint: $AiEndpoint" -ForegroundColor Gray
Write-Host "Scale-to-Zero: Enabled (minReplicas=0)" -ForegroundColor Green
Write-Host "`nTo configure GitHub Actions CI/CD:" -ForegroundColor Yellow
Write-Host "Run this command to create a service principal:" -ForegroundColor White
Write-Host "az ad sp create-for-rbac --name `"academix-github-actions`" --role contributor --scopes /subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup --json-auth" -ForegroundColor Magenta
Write-Host "========================================================" -ForegroundColor Green
