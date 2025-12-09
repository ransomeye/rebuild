#!/bin/bash
# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/admin/uninstall_probe.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Uninstallation script for DPI Probe

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Uninstalling RansomEye DPI Probe...${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

# Stop services
echo -e "${GREEN}Stopping services...${NC}"
systemctl stop ransomeye-probe.service 2>/dev/null || true
systemctl stop ransomeye-probe-admin.service 2>/dev/null || true
systemctl stop ransomeye-probe-metrics.service 2>/dev/null || true

# Disable services
systemctl disable ransomeye-probe.service 2>/dev/null || true
systemctl disable ransomeye-probe-admin.service 2>/dev/null || true
systemctl disable ransomeye-probe-metrics.service 2>/dev/null || true

# Remove systemd files
echo -e "${GREEN}Removing systemd services...${NC}"
rm -f /etc/systemd/system/ransomeye-probe.service
rm -f /etc/systemd/system/ransomeye-probe-admin.service
rm -f /etc/systemd/system/ransomeye-probe-metrics.service
systemctl daemon-reload

# Remove capabilities (optional - leave Python as is)
echo -e "${YELLOW}Note: Network capabilities on Python remain. Remove manually if needed.${NC}"

# Optionally remove user and directories
read -p "Remove user and data directories? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Removing user and directories...${NC}"
    userdel ransomeye-probe 2>/dev/null || true
    rm -rf /var/lib/ransomeye-probe
    rm -rf /etc/ransomeye-probe
    rm -rf /var/log/ransomeye-probe
fi

echo -e "${GREEN}Uninstallation complete!${NC}"

