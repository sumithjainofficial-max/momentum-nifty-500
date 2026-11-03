# Deployment script for Google Cloud Run & Cloud Scheduler
# Run this PowerShell script to deploy your container to Google Cloud

$PROJECT_ID = "momentum-based-nifty-500"
$REGION = "asia-south1"
$SERVICE_NAME = "nifty500-quant-engine"
$GCLOUD_PATH = "C:\Users\sumit\AppData\Local\Google\ct4j-cloud-sdk\LATEST\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "=========================================================="
Write-Host " DEPLOYING NIFTY 500 ENGINE TO GOOGLE CLOUD RUN"
Write-Host " Project: $PROJECT_ID | Region: $REGION"
Write-Host "=========================================================="

# 1. Enable Required Cloud APIs
& $GCLOUD_PATH services enable run.googleapis.com cloudscheduler.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project=$PROJECT_ID

# 2. Deploy from Source to Cloud Run
& $GCLOUD_PATH run deploy $SERVICE_NAME `
    --source="." `
    --region=$REGION `
    --project=$PROJECT_ID `
    --platform=managed `
    --allow-unauthenticated `
    --memory=1Gi `
    --cpu=1 `
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID"

# 3. Retrieve Cloud Run URL
$SERVICE_URL = (& $GCLOUD_PATH run services describe $SERVICE_NAME --platform=managed --region=$REGION --project=$PROJECT_ID --format="value(status.url)")
Write-Host "Cloud Run Service URL: $SERVICE_URL"

# 4. Schedule Automated Run at 3:35 PM IST (Mon-Fri) via Cloud Scheduler
& $GCLOUD_PATH scheduler jobs create http nifty500-daily-scanner `
    --location=$REGION `
    --project=$PROJECT_ID `
    --schedule="35 15 * * 1-5" `
    --time-zone="Asia/Kolkata" `
    --uri="$SERVICE_URL/run-daily-pipeline" `
    --http-method=POST `
    --description="Triggers Nifty 500 Momentum Scan and BigQuery update at 3:35 PM IST every market day."

Write-Host "[✓] Deployment Complete! Pipeline is live and scheduled at 3:35 PM IST every market day."

