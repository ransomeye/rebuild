# Path and File Name : /home/ransomeye/rebuild/ransomeye_install/uninstall_core.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Reversible uninstallation script for RansomEye Core Engine with log export

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REBUILD_ROOT="$(dirname "$SCRIPT_DIR")"
CORE_DIR="${REBUILD_ROOT}/ransomeye_core"
LOG_DIR="${REBUILD_ROOT}/logs"
DATA_DIR="${REBUILD_ROOT}/data"
SNAPSHOT_DIR="${REBUILD_ROOT}/uninstall_snapshots"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
CURRENT_SNAPSHOT="${SNAPSHOT_DIR}/snapshot_${TIMESTAMP}"

echo "=========================================="
echo "RansomEye Core Engine Uninstallation"
echo "=========================================="
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    exit 1
fi

# Prompt for data retention
echo "Do you want to keep data and logs? (y/n)"
read -r KEEP_DATA
KEEP_DATA=${KEEP_DATA:-n}

# Stop and disable service
echo "[1/5] Stopping RansomEye Core service..."
if systemctl is-active --quiet ransomeye-core.service; then
    systemctl stop ransomeye-core.service
    echo "Service stopped"
else
    echo "Service was not running"
fi

if systemctl is-enabled --quiet ransomeye-core.service; then
    systemctl disable ransomeye-core.service
    echo "Service disabled"
fi

# Export logs to snapshot
echo "[2/5] Exporting logs to snapshot..."
mkdir -p "${CURRENT_SNAPSHOT}"

# Copy logs
if [ -d "${LOG_DIR}" ]; then
    cp -r "${LOG_DIR}" "${CURRENT_SNAPSHOT}/logs" 2>/dev/null || true
    echo "Logs exported to ${CURRENT_SNAPSHOT}/logs"
fi

# Export journal logs
journalctl -u ransomeye-core.service --no-pager > "${CURRENT_SNAPSHOT}/journal.log" 2>/dev/null || true
echo "Journal logs exported to ${CURRENT_SNAPSHOT}/journal.log"

# Export configuration
if [ -f "${CORE_DIR}/config/.env" ]; then
    cp "${CORE_DIR}/config/.env" "${CURRENT_SNAPSHOT}/config.env" 2>/dev/null || true
    echo "Configuration exported to ${CURRENT_SNAPSHOT}/config.env"
fi

# Export version manifest if exists
if [ -f "${REBUILD_ROOT}/version_manifest.json" ]; then
    cp "${REBUILD_ROOT}/version_manifest.json" "${CURRENT_SNAPSHOT}/" 2>/dev/null || true
    echo "Version manifest exported"
fi

# Create snapshot summary
cat > "${CURRENT_SNAPSHOT}/snapshot_info.txt" <<EOF
RansomEye Uninstall Snapshot
Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Snapshot Directory: ${CURRENT_SNAPSHOT}
Data Retention: ${KEEP_DATA}
EOF

echo "Snapshot created: ${CURRENT_SNAPSHOT}"

# Remove systemd service
echo "[3/5] Removing systemd service..."
if [ -f "/etc/systemd/system/ransomeye-core.service" ]; then
    rm -f "/etc/systemd/system/ransomeye-core.service"
    systemctl daemon-reload
    echo "Systemd service removed"
else
    echo "Systemd service file not found"
fi

# Remove files
echo "[4/5] Removing installation files..."
if [ "${KEEP_DATA}" = "n" ] || [ "${KEEP_DATA}" = "N" ]; then
    # Remove everything except snapshots
    if [ -d "${CORE_DIR}" ]; then
        rm -rf "${CORE_DIR}"
        echo "Core directory removed"
    fi
    if [ -d "${LOG_DIR}" ]; then
        rm -rf "${LOG_DIR}"
        echo "Log directory removed"
    fi
    if [ -d "${DATA_DIR}" ]; then
        rm -rf "${DATA_DIR}"
        echo "Data directory removed"
    fi
    if [ -f "${REBUILD_ROOT}/version_manifest.json" ]; then
        rm -f "${REBUILD_ROOT}/version_manifest.json"
    fi
    echo "All files removed (data not retained)"
else
    # Keep data directories
    echo "Keeping data and logs as requested"
    if [ -d "${CORE_DIR}" ]; then
        # Remove only code, keep config and data
        rm -rf "${CORE_DIR}/bin" "${CORE_DIR}/api" "${CORE_DIR}/scripts" 2>/dev/null || true
        echo "Core code removed (config and data retained)"
    fi
fi

# Remove user (optional, commented out by default)
echo "[5/5] User cleanup..."
echo "NOTE: User 'ransomeye' will NOT be removed automatically."
echo "To remove the user manually, run: userdel ransomeye"
echo ""

echo "=========================================="
echo "Uninstallation completed!"
echo "=========================================="
echo "Snapshot location: ${CURRENT_SNAPSHOT}"
echo ""

