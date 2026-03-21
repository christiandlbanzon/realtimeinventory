# Final Fix for Authentication Issue

## Current Status
- ✅ Cloud Run Invoker: Granted
- ✅ Service Account Token Creator: Granted  
- ❌ Still getting UNAUTHENTICATED (401)

## Additional Role Needed

The service account might need **"Service Account User"** role on itself to generate OIDC tokens.

### Grant Service Account User Role

1. Go to: https://console.cloud.google.com/iam-admin/iam?project=boxwood-chassis-332307

2. Click "+ GRANT ACCESS"

3. Add:
   - **Principal**: `703996360436-compute@developer.gserviceaccount.com`
   - **Role**: `Service Account User`
   - Click "SAVE"

## Why This Might Be Needed

When a service account needs to generate OIDC tokens for itself (which Cloud Scheduler does), it sometimes needs the "Service Account User" role to act as itself.

## After Granting

1. Wait 2-3 minutes for role propagation
2. Manually trigger scheduler:
   - Go to Cloud Scheduler
   - Click `inventory-updater-schedule`
   - Click "RUN NOW" or "TEST" button
3. Check if status changes to "Succeeded"

## If Still Failing

We can convert the Cloud Run Job to a Cloud Run Service, which:
- Can use Pub/Sub (more reliable than HTTP)
- Avoids OIDC token issues
- Is better suited for scheduled tasks

Let me know if you want to try the Service Account User role first, or if you want to convert to Cloud Run Service instead.
