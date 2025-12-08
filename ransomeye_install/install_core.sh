# Path and File Name : /home/ransomeye/rebuild/ransomeye_install/install_core.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main installation script for RansomEye Core Engine with idempotent operations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REBUILD_ROOT="$(dirname "$SCRIPT_DIR")"
CORE_DIR="${REBUILD_ROOT}/ransomeye_core"
INSTALL_DIR="${REBUILD_ROOT}/ransomeye_install"
SYSTEMD_DIR="${REBUILD_ROOT}/systemd"
LOG_DIR="${REBUILD_ROOT}/logs"
USER_NAME="ransomeye"
CORE_PORT=8080

echo "=========================================="
echo "RansomEye Core Engine Installation"
echo "=========================================="
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    exit 1
fi

# Run preflight checks
echo "[1/8] Running preflight checks..."
if [ -f "${INSTALL_DIR}/preflight_checks.sh" ]; then
    bash "${INSTALL_DIR}/preflight_checks.sh"
    if [ $? -ne 0 ]; then
        echo "ERROR: Preflight checks failed"
        exit 1
    fi
else
    echo "WARNING: preflight_checks.sh not found, skipping..."
fi

# Create ransomeye user if it doesn't exist
echo "[2/8] Creating system user '${USER_NAME}'..."
if ! id "${USER_NAME}" &>/dev/null; then
    useradd -r -s /bin/bash -d "${REBUILD_ROOT}" -m "${USER_NAME}" 2>/dev/null || true
    echo "User '${USER_NAME}' created"
else
    echo "User '${USER_NAME}' already exists"
fi

# Create necessary directories
echo "[3/8] Creating directory structure..."
mkdir -p "${CORE_DIR}/bin"
mkdir -p "${CORE_DIR}/config"
mkdir -p "${CORE_DIR}/scripts"
mkdir -p "${CORE_DIR}/api"
mkdir -p "${CORE_DIR}/logs"
mkdir -p "${SYSTEMD_DIR}"
mkdir -p "${LOG_DIR}"
mkdir -p "${REBUILD_ROOT}/data"
mkdir -p "${REBUILD_ROOT}/certs"

# Set ownership
chown -R "${USER_NAME}:${USER_NAME}" "${REBUILD_ROOT}"
chmod 750 "${REBUILD_ROOT}"

# Copy configuration files
echo "[4/8] Installing configuration files..."
if [ -f "${CORE_DIR}/config/sample.env" ]; then
    if [ ! -f "${CORE_DIR}/config/.env" ]; then
        cp "${CORE_DIR}/config/sample.env" "${CORE_DIR}/config/.env"
        chown "${USER_NAME}:${USER_NAME}" "${CORE_DIR}/config/.env"
        chmod 600 "${CORE_DIR}/config/.env"
        echo "Created .env from sample.env"
    else
        echo ".env already exists, skipping..."
    fi
else
    echo "WARNING: sample.env not found"
fi

# Generate TLS certificates if they don't exist
echo "[5/8] Generating TLS certificates..."
if [ ! -f "${REBUILD_ROOT}/certs/cert.pem" ] || [ ! -f "${REBUILD_ROOT}/certs/key.pem" ]; then
    if [ -f "${CORE_DIR}/scripts/generate_tls_selfsigned.py" ]; then
        sudo -u "${USER_NAME}" python3 "${CORE_DIR}/scripts/generate_tls_selfsigned.py" \
            --cert-path "${REBUILD_ROOT}/certs/cert.pem" \
            --key-path "${REBUILD_ROOT}/certs/key.pem"
        chmod 600 "${REBUILD_ROOT}/certs/cert.pem" "${REBUILD_ROOT}/certs/key.pem"
        echo "TLS certificates generated"
    else
        echo "WARNING: generate_tls_selfsigned.py not found"
    fi
else
    echo "TLS certificates already exist"
fi

# Install systemd service
echo "[6/8] Installing systemd service..."
if [ -f "${SYSTEMD_DIR}/ransomeye-core.service" ]; then
    cp "${SYSTEMD_DIR}/ransomeye-core.service" "/etc/systemd/system/"
    systemctl daemon-reload
    echo "Systemd service installed"
else
    echo "ERROR: ransomeye-core.service not found in ${SYSTEMD_DIR}"
    exit 1
fi

# Set permissions on scripts
echo "[7/8] Setting file permissions..."
find "${CORE_DIR}/bin" -type f -exec chmod 750 {} \;
find "${CORE_DIR}/scripts" -type f -exec chmod 750 {} \;
find "${CORE_DIR}/api" -type f -exec chmod 750 {} \;
chmod 700 "${REBUILD_ROOT}/certs"/*.pem 2>/dev/null || true

# Run database migrations
echo "[8/8] Running database migrations..."
if [ -f "${CORE_DIR}/bin/run_migrations.py" ]; then
    sudo -u "${USER_NAME}" python3 "${CORE_DIR}/bin/run_migrations.py"
    if [ $? -eq 0 ]; then
        echo "Database migrations completed successfully"
    else
        echo "ERROR: Database migrations failed"
        exit 1
    fi
else
    echo "WARNING: run_migrations.py not found"
fi

# Generate version manifest
echo ""
echo "Generating version manifest..."
if [ -f "${INSTALL_DIR}/tools/create_version_manifest.py" ]; then
    sudo -u "${USER_NAME}" python3 "${INSTALL_DIR}/tools/create_version_manifest.py" \
        --root "${REBUILD_ROOT}" \
        --output "${REBUILD_ROOT}/version_manifest.json"
    echo "Version manifest created: ${REBUILD_ROOT}/version_manifest.json"
fi

# Enable and start service
echo ""
echo "Enabling and starting RansomEye Core service..."
systemctl enable ransomeye-core.service
systemctl start ransomeye-core.service

# Wait for service to be ready
echo "Waiting for service to start..."
sleep 3

# Run post-install validation
echo ""
echo "Running post-install validation..."
if [ -f "${INSTALL_DIR}/install_validator.py" ]; then
    sudo -u "${USER_NAME}" python3 "${INSTALL_DIR}/install_validator.py" \
        --port "${CORE_PORT}" \
        --output "${LOG_DIR}/install_report.pdf"
    if [ $? -eq 0 ]; then
        echo "Installation validation completed"
    else
        echo "WARNING: Installation validation reported issues"
    fi
else
    echo "WARNING: install_validator.py not found"
fi

echo ""
echo "=========================================="
echo "Installation completed successfully!"
echo "=========================================="
echo "Service status:"
systemctl status ransomeye-core.service --no-pager -l || true
echo ""
echo "Logs location: ${LOG_DIR}"
echo "Configuration: ${CORE_DIR}/config/.env"
echo ""

