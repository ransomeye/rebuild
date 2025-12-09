#!/bin/bash
# Path and File Name : /home/ransomeye/rebuild/ransomeye_ui/grafana/install_grafana.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Grafana installation script that downloads and extracts Grafana binary

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GRAFANA_DIR="$SCRIPT_DIR"
BIN_DIR="$GRAFANA_DIR/bin"
VERSION="10.2.2"

echo "=========================================="
echo "RansomEye Grafana Installation"
echo "=========================================="
echo ""

# Detect architecture
ARCH=$(uname -m)
OS=$(uname -s | tr '[:upper:]' '[:lower:]')

case "$ARCH" in
  x86_64)
    GRAFANA_ARCH="amd64"
    ;;
  aarch64|arm64)
    GRAFANA_ARCH="arm64"
    ;;
  *)
    echo "Error: Unsupported architecture: $ARCH"
    exit 1
    ;;
esac

echo "Detected architecture: $ARCH ($GRAFANA_ARCH)"
echo "OS: $OS"
echo "Grafana version: $VERSION"
echo ""

# Create bin directory
mkdir -p "$BIN_DIR"

# Check if Grafana is already installed
if [ -f "$BIN_DIR/grafana-server" ] && [ -f "$BIN_DIR/grafana-cli" ]; then
  echo "Grafana appears to be already installed in $BIN_DIR"
  read -p "Do you want to reinstall? (y/N): " REINSTALL
  if [ "$REINSTALL" != "y" ] && [ "$REINSTALL" != "Y" ]; then
    echo "Installation cancelled"
    exit 0
  fi
  rm -rf "$BIN_DIR"/*
fi

# Download URL
GRAFANA_URL="https://dl.grafana.com/oss/release/grafana-${VERSION}.${OS}-${GRAFANA_ARCH}.tar.gz"
TEMP_DIR=$(mktemp -d)
TAR_FILE="$TEMP_DIR/grafana.tar.gz"

echo "Downloading Grafana from: $GRAFANA_URL"
echo ""

# Download Grafana
if command -v curl &> /dev/null; then
  curl -L -o "$TAR_FILE" "$GRAFANA_URL"
elif command -v wget &> /dev/null; then
  wget -O "$TAR_FILE" "$GRAFANA_URL"
else
  echo "Error: Neither curl nor wget is available"
  exit 1
fi

if [ ! -f "$TAR_FILE" ] || [ ! -s "$TAR_FILE" ]; then
  echo "Error: Failed to download Grafana"
  exit 1
fi

echo "Extracting Grafana..."
tar -xzf "$TAR_FILE" -C "$TEMP_DIR"

# Find the grafana directory in the extracted files
GRAFANA_EXTRACTED=$(find "$TEMP_DIR" -type d -name "grafana-*" | head -n 1)

if [ -z "$GRAFANA_EXTRACTED" ]; then
  echo "Error: Could not find Grafana directory in extracted files"
  exit 1
fi

echo "Copying Grafana binaries..."
cp -r "$GRAFANA_EXTRACTED/bin"/* "$BIN_DIR/"
cp -r "$GRAFANA_EXTRACTED/public" "$GRAFANA_DIR/" 2>/dev/null || true
cp -r "$GRAFANA_EXTRACTED/conf" "$GRAFANA_DIR/" 2>/dev/null || true

# Make binaries executable
chmod +x "$BIN_DIR"/*

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "=========================================="
echo "Grafana installation completed!"
echo "=========================================="
echo "Binaries installed to: $BIN_DIR"
echo ""
echo "Next steps:"
echo "1. Configure Grafana: Edit $GRAFANA_DIR/config/custom.ini"
echo "2. Set up provisioning: Configure $GRAFANA_DIR/provisioning/"
echo "3. Start Grafana service: systemctl start ransomeye-grafana"
echo ""

