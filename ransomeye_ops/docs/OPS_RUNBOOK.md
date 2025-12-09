# RansomEye Operations Runbook

## Overview

This runbook provides step-by-step procedures for common operational tasks, disaster recovery, and troubleshooting in the RansomEye platform.

---

## Table of Contents

1. [Backup and Restore](#backup-and-restore)
2. [Key Rotation](#key-rotation)
3. [Database Maintenance](#database-maintenance)
4. [Log Management](#log-management)
5. [Health Monitoring](#health-monitoring)
6. [Disaster Recovery](#disaster-recovery)
7. [Performance Tuning](#performance-tuning)

---

## Backup and Restore

### Creating a Backup

```bash
cd /home/ransomeye/rebuild
python3 ransomeye_ops/disaster_recovery/backup_manager.py
```

**Options:**
- `--no-artifacts`: Skip forensic artifacts backup (faster, smaller)
- `--output-dir <path>`: Specify custom backup directory

**Backup Location:** `/home/ransomeye/rebuild/backups/`

**Backup Format:** Encrypted tarball (`.tar.gz.enc`) with signed manifest

### Verifying a Backup

```bash
python3 ransomeye_ops/disaster_recovery/verify_backup.py <backup_file>
```

### Restoring from Backup

**WARNING:** This will stop services and restore data. Ensure you have a current backup before proceeding.

```bash
python3 ransomeye_ops/disaster_recovery/restore_manager.py <backup_file>
```

**Options:**
- `--no-verify`: Skip backup verification (not recommended)

**Process:**
1. Decrypts backup
2. Stops all RansomEye services
3. Restores database
4. Restores configuration files
5. Restores artifacts (if included)
6. Starts services

---

## Key Rotation

### Rotate Signing Keys

```bash
python3 ransomeye_ops/key_management/rotate_signing_keys.py
```

**Process:**
1. Generates new key pair
2. Creates update bundle signed with old key (for agents)
3. Backs up old key
4. Activates new key

**Rollback:**
```bash
python3 ransomeye_ops/key_management/rotate_signing_keys.py --rollback
```

### Rotate Database Credentials

```bash
python3 ransomeye_ops/key_management/rotate_db_creds.py
```

**Options:**
- `--password <password>`: Use specific password (otherwise generates random)

**Process:**
1. Updates PostgreSQL user password
2. Updates all `.env` files
3. Restarts services

**WARNING:** Save the new password securely!

### Renew Certificates

```bash
python3 ransomeye_ops/key_management/cert_renewer.py
```

**Options:**
- `--force`: Force renewal even if not expiring

Certificates are automatically renewed 30 days before expiry.

---

## Database Maintenance

### Run VACUUM ANALYZE

```bash
python3 ransomeye_ops/maintenance/db_vacuum_scheduler.py --analyze
```

**For specific table:**
```bash
python3 ransomeye_ops/maintenance/db_vacuum_scheduler.py --analyze --table <table_name>
```

### Run VACUUM FULL (Maintenance Window Required)

**WARNING:** VACUUM FULL locks tables. Schedule during maintenance window.

```bash
python3 ransomeye_ops/maintenance/db_vacuum_scheduler.py --full --force
```

### View Table Statistics

```bash
python3 ransomeye_ops/maintenance/db_vacuum_scheduler.py --stats
```

---

## Log Management

### Archive Old Logs

```bash
python3 ransomeye_ops/maintenance/log_archiver.py
```

**Options:**
- `--dry-run`: Show what would be archived without doing it
- `--retention-days <N>`: Override retention period (default: 30 days)
- `--cleanup-archives <N>`: Remove archives older than N days

**Process:**
1. Compresses logs older than retention period
2. Verifies checksum before deletion
3. Moves compressed logs to `logs/archive/`

### Clean Temporary Files

```bash
python3 ransomeye_ops/maintenance/disk_cleaner.py
```

**Options:**
- `--dry-run`: Show what would be cleaned

**Cleans:**
- Temporary files older than 7 days
- Orphaned chunks in buffer directories
- Empty directories

---

## Health Monitoring

### Deep Health Check

```bash
python3 ransomeye_ops/monitoring/deep_health_check.py
```

**Options:**
- `--json`: Output results as JSON

**Checks:**
- Disk I/O and usage
- Database connection pool
- Database query latency
- System load and memory

### Forward Alerts

```bash
python3 ransomeye_ops/monitoring/alert_forwarder.py \
  --type "disk_usage_high" \
  --severity "warning" \
  --message "Disk usage at 85%"
```

**Severity levels:** `critical`, `error`, `warning`, `info`, `debug`

---

## Disaster Recovery

### Disaster Recovery Drill

**WARNING:** This simulates data loss. Use in test environment first.

```bash
bash ransomeye_ops/disaster_recovery/disaster_drill.sh
```

**Process:**
1. Creates test backup
2. Verifies backup
3. Simulates data loss
4. Restores from backup
5. Verifies restore

**Cleanup:**
```bash
rm -rf /home/ransomeye/rebuild/drill_test
```

### Recovery Procedures

#### Complete System Failure

1. **Stop all services:**
   ```bash
   systemctl stop ransomeye-*.service
   ```

2. **Restore from latest backup:**
   ```bash
   python3 ransomeye_ops/disaster_recovery/restore_manager.py <backup_file>
   ```

3. **Verify services:**
   ```bash
   systemctl status ransomeye-core.service
   python3 ransomeye_ops/monitoring/deep_health_check.py
   ```

#### Database Corruption

1. **Stop database-dependent services:**
   ```bash
   systemctl stop ransomeye-core.service
   systemctl stop ransomeye-ai-core.service
   ```

2. **Restore database only:**
   ```bash
   # Extract backup
   # Restore database.dump using pg_restore
   ```

3. **Restart services**

#### Configuration Loss

1. **Extract config from backup:**
   ```bash
   # Decrypt backup
   # Extract config.tar.gz
   ```

2. **Restore config files:**
   ```bash
   tar -xzf config.tar.gz -C /home/ransomeye/rebuild/
   ```

3. **Restart services**

---

## Performance Tuning

### Tune Worker Counts

```bash
python3 ransomeye_ops/tuning/tune_workers.py
```

**Generate configs:**
```bash
python3 ransomeye_ops/tuning/tune_workers.py \
  --gunicorn-config /path/to/gunicorn.conf \
  --celery-config /path/to/celery.conf
```

### Tune PostgreSQL

```bash
python3 ransomeye_ops/tuning/postgres_tuner.py
```

**Generate config:**
```bash
python3 ransomeye_ops/tuning/postgres_tuner.py \
  --output /etc/postgresql/14/main/postgresql.conf.tuned
```

**WARNING:** Review and test before applying to production!

---

## Emergency Contacts

- **Support Email:** Gagan@RansomEye.Tech
- **Project:** RansomEye.Tech

---

## Quick Reference

| Task | Command |
|------|---------|
| Create backup | `python3 ransomeye_ops/disaster_recovery/backup_manager.py` |
| Restore backup | `python3 ransomeye_ops/disaster_recovery/restore_manager.py <backup>` |
| Health check | `python3 ransomeye_ops/monitoring/deep_health_check.py` |
| Archive logs | `python3 ransomeye_ops/maintenance/log_archiver.py` |
| Clean disk | `python3 ransomeye_ops/maintenance/disk_cleaner.py` |
| Rotate keys | `python3 ransomeye_ops/key_management/rotate_signing_keys.py` |
| Rotate DB creds | `python3 ransomeye_ops/key_management/rotate_db_creds.py` |
| Vacuum DB | `python3 ransomeye_ops/maintenance/db_vacuum_scheduler.py --analyze` |

---

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

