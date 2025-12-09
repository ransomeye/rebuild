#!/bin/bash
# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/install.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Standalone installation script that creates user, copies files, and enables service

set -euo pipefail

INSTALL_DIR="/opt/ransomeye-agent"
CONFIG_DIR="/etc/ransomeye-agent"
BUFFER_DIR="/var/lib/ransomeye-agent"
SERVICE_USER="ransomeye"
SERVICE_GROUP="ransomeye"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[INSTALL]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root"
    exit 1
fi

log "Starting RansomEye Linux Agent installation..."

# Step 1: Create user and group
log "Step 1: Creating user and group..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$BUFFER_DIR" "$SERVICE_USER"
    log "User created: $SERVICE_USER"
else
    log "User already exists: $SERVICE_USER"
fi

# Step 2: Create directories
log "Step 2: Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR/certs"
mkdir -p "$CONFIG_DIR/keys"
mkdir -p "$BUFFER_DIR/buffer/pending"
mkdir -p "$BUFFER_DIR/buffer/archive"
mkdir -p "$BUFFER_DIR/backup"
mkdir -p "$INSTALL_DIR/models"
mkdir -p "$INSTALL_DIR/tools"

# Step 3: Copy files
log "Step 3: Copying files..."
cp -r "$SOURCE_DIR/engine" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/transport" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/models" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/security" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/cli" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/updater" "$INSTALL_DIR/"
cp -r "$SOURCE_DIR/tools" "$INSTALL_DIR/" 2>/dev/null || true

# Copy systemd service
cp "$SOURCE_DIR/systemd/ransomeye-agent.service" /etc/systemd/system/

# Step 4: Set permissions
log "Step 4: Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$BUFFER_DIR"
chmod +x "$INSTALL_DIR/engine/agent_main.py"
chmod +x "$INSTALL_DIR/updater/apply_update.sh"
chmod +x "$INSTALL_DIR/updater/verifier.sh"
chmod +x "$INSTALL_DIR/tools/self_test.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/cli/agent_ctl.py"
chmod +x "$INSTALL_DIR/cli/inspect_buffer.py"

# Step 5: Create symlinks for CLI tools
log "Step 5: Creating CLI symlinks..."
ln -sf "$INSTALL_DIR/cli/agent_ctl.py" /usr/local/bin/ransomeye-agent-ctl
ln -sf "$INSTALL_DIR/cli/inspect_buffer.py" /usr/local/bin/ransomeye-agent-inspect

# Step 6: Generate default model if not exists
log "Step 6: Checking model..."
if [ ! -f "$INSTALL_DIR/models/detector_model.pkl" ]; then
    warn "Model file not found, will use default model at runtime"
    warn "To train a model, run: python3 $INSTALL_DIR/models/train/train_detector.py"
fi

# Step 7: Create environment file template
log "Step 7: Creating environment file template..."
cat > "$CONFIG_DIR/agent.env" <<EOF
# RansomEye Linux Agent Configuration
# Edit this file and source it before starting the service

CORE_API_URL=https://localhost:8443
AGENT_CERT_PATH=$CONFIG_DIR/certs/agent.crt
AGENT_KEY_PATH=$CONFIG_DIR/certs/agent.key
CA_CERT_PATH=$CONFIG_DIR/certs/ca.crt
AGENT_UPDATE_KEY_PATH=$CONFIG_DIR/keys/update_key.pub
BUFFER_DIR=$BUFFER_DIR/buffer
MODEL_PATH=$INSTALL_DIR/models/detector_model.pkl
DETECTION_THRESHOLD=0.7
HEARTBEAT_INTERVAL=60
COLLECTION_INTERVAL=5.0
UPLOAD_BATCH_SIZE=10
MONITOR_DIRS=/tmp,/var/tmp,/home
AGENT_METRICS_PORT=9110
EOF

chown "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_DIR/agent.env"
chmod 600 "$CONFIG_DIR/agent.env"

log "Environment file template created: $CONFIG_DIR/agent.env"

# Step 8: Reload systemd and enable service
log "Step 8: Reloading systemd..."
systemctl daemon-reload

log "Step 9: Enabling service..."
systemctl enable ransomeye-agent.service

# Step 9: Instructions
log ""
log "Installation completed successfully!"
log ""
log "Next steps:"
log "  1. Configure certificates in $CONFIG_DIR/certs/"
log "  2. Configure update key in $CONFIG_DIR/keys/"
log "  3. Edit $CONFIG_DIR/agent.env with your settings"
log "  4. Start the service: systemctl start ransomeye-agent"
log "  5. Check status: ransomeye-agent-ctl status"
log ""
warn "IMPORTANT: The agent requires certificates and keys to function."
warn "Please configure them before starting the service."

exit 0

