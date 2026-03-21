# Rename VM to real-time-inventory

## Current Status
- **Old Name:** `inventory-updater-vm-new`
- **New Name:** `real-time-inventory`
- **Status:** VM is stopped (TERMINATED)

## Rename Command

Run this command in your terminal:

```bash
gcloud compute instances set-name inventory-updater-vm-new --zone=us-central1-a --project=boxwood-chassis-332307 --new-name=real-time-inventory
```

## After Renaming

Start the VM:

```bash
gcloud compute instances start real-time-inventory --zone=us-central1-a --project=boxwood-chassis-332307
```

## Verify

```bash
gcloud compute instances list --filter="name=real-time-inventory" --project=boxwood-chassis-332307
```

## Update Deployment Scripts

After renaming, update any scripts that reference the old name:
- `create_and_deploy_new_vm.py` - Update VM_NAME
- `deploy_to_any_vm.py` - Update default VM_NAME
- `cleanup_and_deploy.py` - Update VM_NAME
