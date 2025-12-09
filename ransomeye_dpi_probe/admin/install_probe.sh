#!/bin/bash
# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/admin/install_probe.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Installation script that creates ransomeye-probe user and grants CAP_NET_RAW/CAP_NET_ADMIN capabilities

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing RansomEye DPI Probe...${NC}"

# Configuration
PROBE_USER="ransomeye-probe"
PROBE_GROUP="ransomeye-probe"
PROBE_HOME="/var/lib/ransomeye-probe"
PROBE_ETC="/etc/ransomeye-probe"
PROBE_LOG="/var/log/ransomeye-probe"
PROJECT_ROOT="/home/ransomeye/rebuild"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

# Create user and group
if ! id "$PROBE_USER" &>/dev/null; then
    echo -e "${GREEN}Creating user and group: $PROBE_USER${NC}"
    useradd --system --no-create-home --shell /bin/false --home-dir "$PROBE_HOME" "$PROBE_USER" || true
else
    echo -e "${YELLOW}User $PROBE_USER already exists${NC}"
fi

# Create directories
echo -e "${GREEN}Creating directories...${NC}"
mkdir -p "$PROBE_HOME"/{buffer/pending,buffer/inflight,buffer/archived,receipts,models,feedback}
mkdir -p "$PROBE_ETC"/certs
mkdir -p "$PROBE_LOG"
mkdir -p "$PROJECT_ROOT/models"

# Set permissions
echo -e "${GREEN}Setting permissions...${NC}"
chown -R "$PROBE_USER:$PROBE_GROUP" "$PROBE_HOME"
chown -R "$PROBE_USER:$PROBE_GROUP" "$PROBE_LOG"
chmod 755 "$PROBE_HOME"
chmod 755 "$PROBE_LOG"
chmod 700 "$PROBE_ETC"/certs

# Grant capabilities
echo -e "${GREEN}Granting network capabilities...${NC}"
PYTHON_BIN=$(which python3)
if [ -z "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(which python)
fi

if [ -n "$PYTHON_BIN" ]; then
    setcap cap_net_raw,cap_net_admin=eip "$PYTHON_BIN"
    echo -e "${GREEN}Granted CAP_NET_RAW and CAP_NET_ADMIN to $PYTHON_BIN${NC}"
else
    echo -e "${YELLOW}Could not find Python binary for capabilities${NC}"
fi

# Create systemd service file
echo -e "${GREEN}Creating systemd service...${NC}"
cat > /etc/systemd/system/ransomeye-probe.service <<EOF
[Unit]
Description=RansomEye DPI Probe
After=network.target

[Service]
Type=simple
User=$PROBE_USER
Group=$PROBE_GROUP
WorkingDirectory=$PROJECT_ROOT
Environment="PYTHONPATH=$PROJECT_ROOT"
Environment="BUFFER_DIR=$PROBE_HOME/buffer"
Environment="MODEL_DIR=$PROJECT_ROOT/models"
Environment="RECEIPT_STORE_DIR=$PROBE_HOME/receipts"
Environment="LOG_DIR=$PROBE_LOG"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

ExecStart=$PYTHON_BIN -m ransomeye_dpi_probe.main

[Install]
WantedBy=multi-user.target
EOF

# Create admin API service
cat > /etc/systemd/system/ransomeye-probe-admin.service <<EOF
[Unit]
Description=RansomEye DPI Probe Admin API
After=network.target

[Service]
Type=simple
User=$PROBE_USER
Group=$PROBE_GROUP
WorkingDirectory=$PROJECT_ROOT
Environment="PYTHONPATH=$PROJECT_ROOT"
Environment="PROBE_ADMIN_PORT=9080"
Environment="PROBE_ADMIN_HOST=127.0.0.1"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

ExecStart=$PYTHON_BIN -m ransomeye_dpi_probe.api.probe_admin_api

[Install]
WantedBy=multi-user.target
EOF

# Create metrics exporter service
cat > /etc/systemd/system/ransomeye-probe-metrics.service <<EOF
[Unit]
Description=RansomEye DPI Probe Metrics Exporter
After=network.target

[Service]
Type=simple
User=$PROBE_USER
Group=$PROBE_GROUP
WorkingDirectory=$PROJECT_ROOT
Environment="PYTHONPATH=$PROJECT_ROOT"
Environment="PROBE_METRICS_PORT=9092"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

ExecStart=$PYTHON_BIN -m ransomeye_dpi_probe.metrics.exporter

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Configure certificates in $PROBE_ETC/certs/"
echo "2. Set environment variables in /etc/systemd/system/ransomeye-probe.service"
echo "3. Start services:"
echo "   systemctl enable ransomeye-probe"
echo "   systemctl enable ransomeye-probe-admin"
echo "   systemctl enable ransomeye-probe-metrics"
echo "   systemctl start ransomeye-probe"
echo "   systemctl start ransomeye-probe-admin"
echo "   systemctl start ransomeye-probe-metrics"

