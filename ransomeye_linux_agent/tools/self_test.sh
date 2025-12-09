#!/bin/bash
# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/tools/self_test.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Self-test script to verify agent functionality after update

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[TEST]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

INSTALL_DIR="/opt/ransomeye-agent"
SERVICE_NAME="ransomeye-agent"

# Test 1: Check if service is running
log "Test 1: Checking service status..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log "Service is running"
else
    error "Service is not running"
    exit 1
fi

# Test 2: Check if Python modules can be imported
log "Test 2: Checking Python imports..."
if python3 -c "import sys; sys.path.insert(0, '$INSTALL_DIR'); from engine.agent_main import AgentMain" 2>/dev/null; then
    log "Python imports successful"
else
    error "Python import failed"
    exit 1
fi

# Test 3: Check if buffer directory is writable
log "Test 3: Checking buffer directory..."
BUFFER_DIR="${BUFFER_DIR:-/var/lib/ransomeye-agent/buffer}"
if [ -d "$BUFFER_DIR" ] && [ -w "$BUFFER_DIR" ]; then
    log "Buffer directory is writable"
else
    error "Buffer directory is not writable"
    exit 1
fi

# Test 4: Check if model file exists (warning if not)
log "Test 4: Checking model file..."
MODEL_PATH="${MODEL_PATH:-$INSTALL_DIR/models/detector_model.pkl}"
if [ -f "$MODEL_PATH" ]; then
    log "Model file exists"
else
    warn "Model file not found (will use default)"
fi

# Test 5: Check agent CLI
log "Test 5: Checking agent CLI..."
if [ -f "$INSTALL_DIR/cli/agent_ctl.py" ] && [ -x "$INSTALL_DIR/cli/agent_ctl.py" ]; then
    if python3 "$INSTALL_DIR/cli/agent_ctl.py" status > /dev/null 2>&1; then
        log "Agent CLI is functional"
    else
        warn "Agent CLI test failed (non-critical)"
    fi
else
    warn "Agent CLI not found"
fi

log "All critical tests passed"
exit 0

