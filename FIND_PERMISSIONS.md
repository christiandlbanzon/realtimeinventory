# How to Find Permissions for Cloud Run Job

## Method 1: From Cloud Run Jobs List (RECOMMENDED)

1. **Go to Cloud Run Jobs list:**
   https://console.cloud.google.com/run/jobs?project=boxwood-chassis-332307

2. **Click on `inventory-updater`** (the job name itself, not a link)

3. **On the job details page**, look for tabs at the top:
   - You should see tabs like: "EXECUTIONS", "PERMISSIONS", "YAML", etc.
   - Click the **"PERMISSIONS"** tab

4. **Click "GRANT ACCESS"** button

5. **Add:**
   - **New principals**: `703996360436-compute@developer.gserviceaccount.com`
   - **Select a role**: Choose `Cloud Run Invoker`
   - Click **"SAVE"**

## Method 2: Via IAM & Admin (Alternative)

1. **Go to IAM & Admin:**
   https://console.cloud.google.com/iam-admin/iam?project=boxwood-chassis-332307

2. **Click "GRANT ACCESS"** at the top

3. **Add:**
   - **New principals**: `703996360436-compute@developer.gserviceaccount.com`
   - **Select a role**: Search for and select `Cloud Run Invoker`
   - **Condition**: Leave empty (or set to apply to this specific job if needed)
   - Click **"SAVE"**

## Method 3: Using gcloud CLI (If you have it)

```bash
gcloud run jobs add-iam-policy-binding inventory-updater \
  --region=us-east1 \
  --member=serviceAccount:703996360436-compute@developer.gserviceaccount.com \
  --role=roles/run.invoker \
  --project=boxwood-chassis-332307
```

## What to Look For

The permissions page should show:
- Current IAM bindings
- Who has what roles
- A button to "GRANT ACCESS" or "ADD PRINCIPAL"

If you don't see a PERMISSIONS tab on the job details page, try Method 2 (IAM & Admin) instead.
