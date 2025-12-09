#!/bin/bash
# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/updater/apply_update.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Atomic update script with rollback capability

set -euo pipefail

UPDATE_BUNDLE="${1:-}"
BACKUP_DIR="/var/lib/ransomeye-agent/backup"
INSTALL_DIR="/opt/ransomeye-agent"
SERVICE_NAME="ransomeye-agent"
SELF_TEST_SCRIPT="${INSTALL_DIR}/tools/self_test.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[UPDATE]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

if [ -z "$UPDATE_BUNDLE" ]; then
    error "Usage: $0 <update_bundle.tar.gz>"
    exit 1
fi

if [ ! -f "$UPDATE_BUNDLE" ]; then
    error "Update bundle not found: $UPDATE_BUNDLE"
    exit 1
fi

# Step 1: Verify signature
log "Step 1: Verifying update bundle signature..."
if ! "${INSTALL_DIR}/updater/verifier.sh" "$UPDATE_BUNDLE"; then
    error "Signature verification failed"
    exit 1
fi

# Step 2: Stop service
log "Step 2: Stopping service..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl stop "$SERVICE_NAME"
    log "Service stopped"
else
    warn "Service was not running"
fi

# Step 3: Create backup
log "Step 3: Creating backup..."
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CURRENT_BACKUP="${BACKUP_DIR}/${BACKUP_TIMESTAMP}"
mkdir -p "$CURRENT_BACKUP"

if [ -d "$INSTALL_DIR" ]; then
    cp -r "$INSTALL_DIR"/* "$CURRENT_BACKUP/" 2>/dev/null || true
    log "Backup created: $CURRENT_BACKUP"
else
    warn "Install directory does not exist, skipping backup"
fi

# Step 4: Extract new binary
log "Step 4: Extracting update bundle..."
TEMP_EXTRACT=$(mktemp -d)
trap "rm -rf $TEMP_EXTRACT" EXIT

tar -xzf "$UPDATE_BUNDLE" -C "$TEMP_EXTRACT"

# Verify bundle structure
if [ ! -d "$TEMP_EXTRACT/ransomeye-agent" ]; then
    error "Invalid bundle structure"
    exit 1
fi

# Step 5: Install new files
log "Step 5: Installing new files..."
mkdir -p "$INSTALL_DIR"
cp -r "$TEMP_EXTRACT/ransomeye-agent"/* "$INSTALL_DIR/"

# Set permissions
chown -R ransomeye:ransomeye "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/engine/agent_main.py"
chmod +x "$INSTALL_DIR/updater/apply_update.sh"
chmod +x "$INSTALL_DIR/updater/verifier.sh"

log "Files installed"

# Step 6: Start service
log "Step 6: Starting service..."
if systemctl start "$SERVICE_NAME"; then
    log "Service started"
    sleep 2  # Give service time to initialize
else
    error "Failed to start service"
    # Rollback will happen below
fi

# Step 7: Run self-test
log "Step 7: Running self-test..."
if [ -f "$SELF_TEST_SCRIPT" ] && [ -x "$SELF_TEST_SCRIPT" ]; then
    if "$SELF_TEST_SCRIPT"; then
        log "Self-test passed"
    else
        error "Self-test failed"
        # Rollback
    fi
else
    warn "Self-test script not found, skipping"
    # Check if service is running as alternative
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        error "Service is not running after update"
        # Rollback
    fi
fi

# Check if we need to rollback
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    error "Service failed after update, initiating rollback..."
    
    # Stop service if running
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    # Restore from backup
    if [ -d "$CURRENT_BACKUP" ]; then
        log "Restoring from backup: $CURRENT_BACKUP"
        rm -rf "$INSTALL_DIR"/*
        cp -r "$CURRENT_BACKUP"/* "$INSTALL_DIR/"
        chown -R ransomeye:ransomeye "$INSTALL_DIR"
        
        # Start service
        if systemctl start "$SERVICE_NAME"; then
            log "Rollback successful, service restarted"
        else
            error "Rollback failed, manual intervention required"
            exit 1
        fi
    else
        error "Backup not found, cannot rollback"
        exit 1
    fi
    
    exit 1
fi

log "Update completed successfully"
log "Backup preserved at: $CURRENT_BACKUP"
log "To remove old backups, run: rm -rf ${BACKUP_DIR}/*"

exit 0

