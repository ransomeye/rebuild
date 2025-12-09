#!/bin/bash
# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/updater/verifier.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: GPG/OpenSSL signature verifier for update bundles

set -euo pipefail

BUNDLE="${1:-}"
SIGNATURE_FILE="${BUNDLE}.sig"
PUBLIC_KEY_PATH="${AGENT_UPDATE_KEY_PATH:-/etc/ransomeye-agent/keys/update_key.pub}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[VERIFY]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

if [ -z "$BUNDLE" ]; then
    error "Usage: $0 <bundle.tar.gz>"
    exit 1
fi

if [ ! -f "$BUNDLE" ]; then
    error "Bundle not found: $BUNDLE"
    exit 1
fi

# Check if signature file exists
if [ ! -f "$SIGNATURE_FILE" ]; then
    error "Signature file not found: $SIGNATURE_FILE"
    exit 1
fi

# Check if public key exists
if [ ! -f "$PUBLIC_KEY_PATH" ]; then
    error "Public key not found: $PUBLIC_KEY_PATH"
    exit 1
fi

# Verify signature using OpenSSL
log "Verifying signature..."

# Extract signature (assuming it's base64 encoded)
SIGNATURE_TEMP=$(mktemp)
trap "rm -f $SIGNATURE_TEMP" EXIT

# Decode signature if needed
if grep -q "BEGIN" "$SIGNATURE_FILE"; then
    # PEM format
    openssl dgst -sha256 -verify "$PUBLIC_KEY_PATH" -signature "$SIGNATURE_FILE" "$BUNDLE" > /dev/null 2>&1
else
    # Binary signature, decode base64 if needed
    base64 -d "$SIGNATURE_FILE" > "$SIGNATURE_TEMP" 2>/dev/null || cp "$SIGNATURE_FILE" "$SIGNATURE_TEMP"
    openssl dgst -sha256 -verify "$PUBLIC_KEY_PATH" -signature "$SIGNATURE_TEMP" "$BUNDLE" > /dev/null 2>&1
fi

if [ $? -eq 0 ]; then
    log "Signature verification successful"
    exit 0
else
    error "Signature verification failed"
    exit 1
fi

