---
description: Deploy to production — verify tests pass, pre-deploy backup, zero-downtime restart, health check, rollback capability.
---

# /deploy

> Run this workflow to deploy the current `main` branch to production.
> Requires: GOV-008 configured with deployment target details.

## Prerequisites

Before deploying, verify:
1. All tests pass (`/test`)
2. Compliance check passes (`bin/compliance_check.sh`)
3. `GOV-008` has been completed with production environment details
4. Sprint audit (VER-001) has been completed for the sprint being deployed

---

## Step 1: Pre-Deploy Verification

// turbo
1. Run lint, typecheck, and tests:
```bash
npm run lint && npm run typecheck && npm run test
```

2. If any step fails, **STOP**. Do not deploy. Fix the issue first.

---

## Step 2: Pre-Deploy Backup

1. SSH to the production server and create a database backup:
```bash
ssh [PROD_HOST] "pg_dump -Fc [DB_NAME] > /var/backups/[PROJECT]/pre-deploy-$(date +%Y%m%d-%H%M%S).dump"
```

2. Note the backup filename for rollback if needed.

3. Record the current git commit on production:
```bash
ssh [PROD_HOST] "cd /opt/[PROJECT]/[SERVICE] && git rev-parse HEAD"
```

---

## Step 3: Deploy

1. Pull latest code on production:
```bash
ssh [PROD_HOST] "cd /opt/[PROJECT]/[SERVICE] && git pull origin main"
```

2. Install dependencies:
```bash
ssh [PROD_HOST] "cd /opt/[PROJECT]/[SERVICE] && npm install --production"
```

3. Run database migrations (if applicable):
```bash
ssh [PROD_HOST] "cd /opt/[PROJECT]/[SERVICE] && npx drizzle-kit migrate"
```

4. Zero-downtime restart:
```bash
ssh [PROD_HOST] "pm2 reload [SERVICE_NAME]"
```

---

## Step 4: Health Check

// turbo
1. Wait 5 seconds for the service to start, then verify:
```bash
sleep 5
curl -sf http://[PROD_HOST]:[PORT]/health && echo "✅ Health check passed" || echo "❌ Health check FAILED"
```

2. If health check fails, immediately run **Step 5: Rollback**.

---

## Step 5: Rollback (if needed)

Only run this if the health check failed or a critical issue is discovered.

1. Revert to previous commit:
```bash
ssh [PROD_HOST] "cd /opt/[PROJECT]/[SERVICE] && git checkout [PREVIOUS_COMMIT]"
ssh [PROD_HOST] "cd /opt/[PROJECT]/[SERVICE] && npm install --production"
ssh [PROD_HOST] "pm2 reload [SERVICE_NAME]"
```

2. Restore database backup:
```bash
ssh [PROD_HOST] "pg_restore -d [DB_NAME] --clean /var/backups/[PROJECT]/[BACKUP_FILE]"
```

3. Verify health check after rollback.

---

## Step 6: Post-Deploy

1. Tag the release:
```bash
git tag -a v[VERSION] -m "Release v[VERSION] — [sprint description]"
git push origin v[VERSION]
```

2. Update the sprint doc status to `CLOSED`.

3. Update MANIFEST.yaml if any new docs were added.

4. Notify the Human that deployment is complete.

---

## Quick Reference

| What | Command |
|:-----|:--------|
| Full deploy | `/deploy` |
| Rollback | Run Step 5 manually |
| Health check only | `curl -sf http://[HOST]:[PORT]/health` |
