# Service Account Setup - Best Practices

## Current Setup

**Service Account Email:** `703996360436-compute@developer.gserviceaccount.com`

This is the same service account used for:
- Google Cloud Compute Engine (VM access)
- Google Sheets API (inventory updates)

## Option 1: Share Once Per Sheet (Current Method) ✅ Recommended

**How it works:**
- Share each new sheet (January, February, March, etc.) with the service account email **once**
- The service account will have access to all sheets you've shared with it
- Simple and secure

**Pros:**
- ✅ Simple setup
- ✅ Secure (only sheets you explicitly share)
- ✅ Works immediately
- ✅ No additional configuration needed

**Cons:**
- ⚠️ Need to remember to share each new sheet

**Best Practice:**
- Keep a list of the service account email handy
- When creating a new monthly sheet, share it immediately
- Or create a template/checklist for new sheets

---

## Option 2: Domain-Wide Delegation (Advanced)

**How it works:**
- Configure the service account with domain-wide delegation
- Grant it access to all Google Sheets in your Google Workspace domain
- No need to share individual sheets

**Pros:**
- ✅ No need to share each sheet
- ✅ Automatic access to all sheets in domain

**Cons:**
- ⚠️ Requires Google Workspace (not personal Gmail)
- ⚠️ More complex setup
- ⚠️ Less secure (access to ALL sheets)
- ⚠️ Requires admin access

**When to use:**
- Only if you have Google Workspace
- Only if you want automatic access to all sheets
- Only if you're comfortable with broader permissions

---

## Option 3: Use Same Service Account for All Operations ✅ Current

**How it works:**
- Use the same service account (`703996360436-compute@developer.gserviceaccount.com`) for:
  - VM operations
  - Google Sheets updates
  - All Google Cloud services

**Pros:**
- ✅ One service account to manage
- ✅ Consistent permissions
- ✅ Easy to track what has access

**Cons:**
- ⚠️ Still need to share each sheet (but only once per sheet)

---

## Recommended Approach

**Use Option 1 + Option 3 together:**

1. ✅ **Keep using the same service account** (you're already doing this)
2. ✅ **Share each new sheet once** with Editor permissions
3. ✅ **Create a checklist** for new monthly sheets:
   - Create sheet
   - Share with: `703996360436-compute@developer.gserviceaccount.com` (Editor)
   - Update code if needed (usually automatic)

## Quick Reference

**Service Account Email:**
```
703996360436-compute@developer.gserviceaccount.com
```

**Required Permission:**
- Editor (not Viewer)

**When to Share:**
- When creating a new monthly sheet
- When creating a new inventory sheet
- Any time you need the VM to update a sheet

## Automation Option

You could create a script that:
1. Creates a new monthly sheet
2. Automatically shares it with the service account
3. Updates the code if needed

But for now, sharing manually is the simplest and most secure approach.
