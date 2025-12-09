# RansomEye Operations & Maintenance Suite (Phase 27)

## Overview

The Operations & Maintenance suite provides comprehensive tools for day-2 operations, disaster recovery, key management, maintenance, monitoring, and performance tuning of the RansomEye platform.

## Features

- **Disaster Recovery**: Encrypted backups, restore procedures, and verification
- **Key Management**: Rotation of signing keys, database credentials, and certificates
- **Maintenance**: Log archiving, disk cleanup, and database vacuum scheduling
- **Monitoring**: Deep health checks and alert forwarding to Syslog/SIEM
- **Performance Tuning**: Auto-calculation of worker counts and PostgreSQL optimization

## Directory Structure

```
ransomeye_ops/
├── disaster_recovery/      # Backup, restore, and DR procedures
│   ├── backup_manager.py
│   ├── restore_manager.py
│   ├── verify_backup.py
│   └── disaster_drill.sh
├── key_management/         # Key and credential rotation
│   ├── rotate_signing_keys.py
│   ├── rotate_db_creds.py
│   └── cert_renewer.py
├── maintenance/            # Log archiving and cleanup
│   ├── log_archiver.py
│   ├── disk_cleaner.py
│   └── db_vacuum_scheduler.py
├── monitoring/             # Health checks and alerting
│   ├── deep_health_check.py
│   └── alert_forwarder.py
├── tuning/                # Performance optimization
│   ├── tune_workers.py
│   └── postgres_tuner.py
└── docs/                  # Documentation
    └── OPS_RUNBOOK.md
```

## Quick Start

### Create Backup
```bash
python3 ransomeye_ops/disaster_recovery/backup_manager.py
```

### Health Check
```bash
python3 ransomeye_ops/monitoring/deep_health_check.py
```

### Archive Logs
```bash
python3 ransomeye_ops/maintenance/log_archiver.py
```

## Requirements

- Python 3.8+
- PostgreSQL client tools (`pg_dump`, `pg_restore`, `psql`)
- `psutil` (system monitoring)
- `sqlalchemy` (database connections)
- `cryptography` (encryption and signing)

## Environment Variables

- `REBUILD_ROOT`: Project root directory (default: `/home/ransomeye/rebuild`)
- `OPS_BACKUP_PUBKEY_PATH`: Public key for backup encryption
- `OPS_BACKUP_PASSPHRASE`: Passphrase for symmetric encryption (alternative)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`: Database credentials
- `LOG_RETENTION_DAYS`: Log retention period (default: 30)
- `SYSLOG_HOST`, `SYSLOG_PORT`: Syslog server configuration

## Documentation

See [docs/OPS_RUNBOOK.md](docs/OPS_RUNBOOK.md) for detailed operational procedures.

## Support

- **Email**: Gagan@RansomEye.Tech
- **Project**: RansomEye.Tech

---

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

