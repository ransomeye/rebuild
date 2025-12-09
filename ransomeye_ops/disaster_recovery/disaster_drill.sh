# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/disaster_recovery/disaster_drill.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Simulates data loss scenario and tests restore procedure for training

#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REBUILD_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DRILL_DIR="${REBUILD_ROOT}/drill_test"
BACKUP_DIR="${REBUILD_ROOT}/backups"

echo "=========================================="
echo "RansomEye Disaster Recovery Drill"
echo "=========================================="
echo ""
echo "This script simulates a data loss scenario and tests the restore procedure."
echo "WARNING: This will create test data and may affect the system."
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Drill cancelled."
    exit 0
fi

# Step 1: Create a test backup
echo ""
echo "[Step 1/5] Creating test backup..."
python3 "${SCRIPT_DIR}/backup_manager.py" --no-artifacts --output-dir "${DRILL_DIR}/backups"
if [ $? -ne 0 ]; then
    echo "ERROR: Backup creation failed"
    exit 1
fi

BACKUP_FILE=$(ls -t "${DRILL_DIR}/backups"/*.tar.gz.enc | head -1)
if [ -z "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found"
    exit 1
fi

echo "✓ Backup created: ${BACKUP_FILE}"

# Step 2: Verify backup
echo ""
echo "[Step 2/5] Verifying backup..."
python3 "${SCRIPT_DIR}/verify_backup.py" "${BACKUP_FILE}"
if [ $? -ne 0 ]; then
    echo "ERROR: Backup verification failed"
    exit 1
fi

echo "✓ Backup verified"

# Step 3: Simulate data loss
echo ""
echo "[Step 3/5] Simulating data loss..."
echo "  - Stopping services..."
systemctl stop ransomeye-core.service 2>/dev/null || true
systemctl stop ransomeye-db-core.service 2>/dev/null || true

echo "  - Backing up current state (for rollback)..."
ROLLBACK_DIR="${DRILL_DIR}/rollback_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${ROLLBACK_DIR}"

# Backup current DB
if [ -d "${REBUILD_ROOT}/ransomeye_db_core" ]; then
    cp -r "${REBUILD_ROOT}/ransomeye_db_core" "${ROLLBACK_DIR}/" 2>/dev/null || true
fi

# Backup current configs
if [ -d "${REBUILD_ROOT}/ransomeye_core/config" ]; then
    cp -r "${REBUILD_ROOT}/ransomeye_core/config" "${ROLLBACK_DIR}/" 2>/dev/null || true
fi

echo "  - Simulating data corruption..."
# Create a test file to simulate loss
echo "DATA LOST" > "${REBUILD_ROOT}/.drill_marker"

echo "✓ Data loss simulated"

# Step 4: Restore from backup
echo ""
echo "[Step 4/5] Restoring from backup..."
python3 "${SCRIPT_DIR}/restore_manager.py" "${BACKUP_FILE}" --no-verify
if [ $? -ne 0 ]; then
    echo "ERROR: Restore failed"
    echo "Rollback data available at: ${ROLLBACK_DIR}"
    exit 1
fi

echo "✓ Restore completed"

# Step 5: Verify restore
echo ""
echo "[Step 5/5] Verifying restore..."
sleep 2

# Check if services are running
if systemctl is-active --quiet ransomeye-core.service; then
    echo "  ✓ Core service is running"
else
    echo "  ✗ Core service is not running"
fi

# Check if marker file is gone (indicating restore worked)
if [ ! -f "${REBUILD_ROOT}/.drill_marker" ]; then
    echo "  ✓ System appears restored"
else
    echo "  ✗ System may not be fully restored"
fi

echo ""
echo "=========================================="
echo "Disaster Recovery Drill Complete"
echo "=========================================="
echo ""
echo "Rollback data: ${ROLLBACK_DIR}"
echo "Test backup: ${BACKUP_FILE}"
echo ""
echo "To clean up test data:"
echo "  rm -rf ${DRILL_DIR}"
echo ""

