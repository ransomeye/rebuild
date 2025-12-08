# Path and File Name : /home/ransomeye/rebuild/ransomeye_install/preflight_checks.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Pre-installation validation checks for OS, ports, and database connectivity

set -e

CORE_PORT=8080
DB_PORT=5432
DB_HOST="${DB_HOST:-localhost}"

echo "Running preflight checks..."
echo ""

# Check OS
echo "[1/4] Checking operating system..."
if [ "$(uname)" != "Linux" ]; then
    echo "ERROR: This installer is designed for Linux systems only"
    exit 1
fi
OS_RELEASE=$(cat /etc/os-release 2>/dev/null | grep "^ID=" | cut -d'=' -f2 | tr -d '"' || echo "unknown")
echo "✓ OS detected: ${OS_RELEASE}"

# Check if port 8080 is available
echo "[2/4] Checking if port ${CORE_PORT} is available..."
if command -v netstat >/dev/null 2>&1; then
    if netstat -tuln | grep -q ":${CORE_PORT} "; then
        echo "ERROR: Port ${CORE_PORT} is already in use"
        echo "Please stop the service using this port or change CORE_PORT in configuration"
        exit 1
    fi
elif command -v ss >/dev/null 2>&1; then
    if ss -tuln | grep -q ":${CORE_PORT} "; then
        echo "ERROR: Port ${CORE_PORT} is already in use"
        echo "Please stop the service using this port or change CORE_PORT in configuration"
        exit 1
    fi
else
    echo "WARNING: Cannot check port availability (netstat/ss not found)"
fi
echo "✓ Port ${CORE_PORT} is available"

# Check PostgreSQL connectivity
echo "[3/4] Checking PostgreSQL connectivity..."
if command -v pg_isready >/dev/null 2>&1; then
    if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" >/dev/null 2>&1; then
        echo "✓ PostgreSQL is reachable at ${DB_HOST}:${DB_PORT}"
    else
        echo "ERROR: PostgreSQL is not reachable at ${DB_HOST}:${DB_PORT}"
        echo "Please ensure PostgreSQL is running and accessible"
        exit 1
    fi
else
    # Fallback to Python check
    if command -v python3 >/dev/null 2>&1; then
        python3 <<EOF
import sys
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex(('${DB_HOST}', ${DB_PORT}))
    sock.close()
    if result != 0:
        print("ERROR: PostgreSQL is not reachable at ${DB_HOST}:${DB_PORT}")
        sys.exit(1)
    print("✓ PostgreSQL is reachable at ${DB_HOST}:${DB_PORT}")
except Exception as e:
    print(f"ERROR: Cannot check PostgreSQL connectivity: {e}")
    sys.exit(1)
EOF
        if [ $? -ne 0 ]; then
            exit 1
        fi
    else
        echo "WARNING: Cannot check PostgreSQL connectivity (pg_isready and python3 not found)"
    fi
fi

# Check required Python packages
echo "[4/4] Checking Python dependencies..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is not installed"
    exit 1
fi

REQUIRED_PACKAGES=("fastapi" "uvicorn" "sqlalchemy" "psycopg2" "cryptography" "reportlab")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import ${package}" 2>/dev/null; then
        MISSING_PACKAGES+=("${package}")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo "ERROR: Missing required Python packages: ${MISSING_PACKAGES[*]}"
    echo "Please install missing packages before running the installer"
    exit 1
fi
echo "✓ All required Python packages are installed"

echo ""
echo "All preflight checks passed!"
echo ""

