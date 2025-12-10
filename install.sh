#!/bin/bash
# Path: /home/ransomeye/rebuild/install.sh
# details: Unified Installer Entrypoint

if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root"
  exit 1
fi

echo "[-] Starting RansomEye Unified Installation..."
chmod +x ./ransomeye_install/install_core.sh
./ransomeye_install/install_core.sh

echo "[+] Installation Complete."
