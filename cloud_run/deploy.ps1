# Deployment script for Google Cloud Run & Cloud Scheduler
# Bulletproof path detection: works whether run from root or from within cloud_run directory

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $SCRIPT_DIR) { $SCRIPT_DIR = (Get-Location).Path }
$ROOT_DIR = (Resolve-Path "$SCRIPT_DIR\..").Path
$SOURCE_DIR = if (Test-Path "$SCRIPT_DIR\Dockerfile") { $SCRIPT_DIR } else { "$ROOT_DIR\cloud_run" }

$PROJECT_ID = "momentum-based-nifty-500"
$REGION = "asia-south1"
$SERVICE_NAME = "nifty500-quant-engine"
$GCLOUD_PATH = "C:\Users\sumit\AppData\Local\Google\ct4j-cloud-sdk\LATEST\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "=========================================================="
Write-Host " DEPLOYING NIFTY 500 ENGINE TO GOOGLE CLOUD RUN"
Write-Host " Project: $PROJECT_ID | Region: $REGION"
Write-Host " Source Directory: $SOURCE_DIR"
Write-Host "=========================================================="

# 1. Enable Required Cloud APIs
& $GCLOUD_PATH services enable run.googleapis.com cloudscheduler.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project=$PROJECT_ID

# 2. Deploy from Source to Cloud Run
& $GCLOUD_PATH run deploy $SERVICE_NAME `
    --source="$SOURCE_DIR" `
    --region=$REGION `
    --project=$PROJECT_ID `
    --platform=managed `
    --allow-unauthenticated `
    --memory=1Gi `
    --cpu=1 `
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID" `
    --quiet

# 3. Retrieve Cloud Run URL
$SERVICE_URL = (& $GCLOUD_PATH run services describe $SERVICE_NAME --platform=managed --region=$REGION --project=$PROJECT_ID --format="value(status.url)")
Write-Host "Cloud Run Service URL: $SERVICE_URL"

# 4. Schedule Automated Run at 3:35 PM IST (Mon-Fri) via Cloud Scheduler
# Check if job already exists; create or update
$JOB_EXISTS = (& $GCLOUD_PATH scheduler jobs list --location=$REGION --project=$PROJECT_ID --format="value(ID)" | Select-String "nifty500-daily-scanner")
if ($JOB_EXISTS) {
    Write-Host "Updating existing Cloud Scheduler job..."
    & $GCLOUD_PATH scheduler jobs update http nifty500-daily-scanner `
        --location=$REGION `
        --project=$PROJECT_ID `
        --schedule="35 15 * * 1-5" `
        --time-zone="Asia/Kolkata" `
        --uri="$SERVICE_URL/run-daily-pipeline" `
        --http-method=POST `
        --description="Triggers Nifty 500 Momentum Scan and BigQuery update at 3:35 PM IST every market day." `
        --quiet
} else {
    Write-Host "Creating new Cloud Scheduler job..."
    & $GCLOUD_PATH scheduler jobs create http nifty500-daily-scanner `
        --location=$REGION `
        --project=$PROJECT_ID `
        --schedule="35 15 * * 1-5" `
        --time-zone="Asia/Kolkata" `
        --uri="$SERVICE_URL/run-daily-pipeline" `
        --http-method=POST `
        --description="Triggers Nifty 500 Momentum Scan and BigQuery update at 3:35 PM IST every market day." `
        --quiet
}

Write-Host "[✓] Deployment Complete! Pipeline is live and scheduled at 3:35 PM IST every market day."


