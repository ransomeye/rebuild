# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/tools/download_threat_data.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Downloads full historical threat intelligence data from all sources for Day-Zero hydration

#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REBUILD_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DATA_DIR="${REBUILD_ROOT}/ransomeye_threat_intel/data"
CURRENT_YEAR=$(date +%Y)

echo "=========================================="
echo "RansomEye Threat Data Downloader"
echo "Day-Zero Data Hydration"
echo "=========================================="
echo ""
echo "Download directory: ${DATA_DIR}"
echo ""

# Create data directory
mkdir -p "${DATA_DIR}"

# Function to download with retry
download_with_retry() {
    local url=$1
    local output=$2
    local max_retries=3
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        if wget -q --show-progress -O "${output}" "${url}" 2>&1; then
            # Verify file exists and has size > 0
            if [ -f "${output}" ] && [ -s "${output}" ]; then
                echo "  ✓ Downloaded: $(basename ${output})"
                return 0
            else
                echo "  ✗ File is empty or missing: ${output}"
            fi
        elif curl -s -L -o "${output}" "${url}" 2>&1; then
            if [ -f "${output}" ] && [ -s "${output}" ]; then
                echo "  ✓ Downloaded: $(basename ${output})"
                return 0
            else
                echo "  ✗ File is empty or missing: ${output}"
            fi
        else
            echo "  ✗ Download failed (attempt $((retry + 1))/${max_retries})"
        fi
        
        retry=$((retry + 1))
        sleep 2
    done
    
    echo "  ✗ Failed to download after ${max_retries} attempts: ${url}"
    return 1
}

# 1. NIST NVD - Full history from 2002 to current year
echo "[1/7] Downloading NIST NVD CVE data (2002-${CURRENT_YEAR})..."
NVD_COUNT=0
NVD_FAILED=0

for year in $(seq 2002 ${CURRENT_YEAR}); do
    url="https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-${year}.json.gz"
    output="${DATA_DIR}/nvdcve-2.0-${year}.json.gz"
    
    if download_with_retry "${url}" "${output}"; then
        NVD_COUNT=$((NVD_COUNT + 1))
    else
        NVD_FAILED=$((NVD_FAILED + 1))
    fi
done

echo "  NVD: ${NVD_COUNT} files downloaded, ${NVD_FAILED} failed"

# 2. CISA KEV
echo ""
echo "[2/7] Downloading CISA Known Exploited Vulnerabilities..."
url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
output="${DATA_DIR}/known_exploited_vulnerabilities.json"

if download_with_retry "${url}" "${output}"; then
    echo "  ✓ CISA KEV downloaded"
else
    echo "  ✗ CISA KEV download failed"
fi

# 3. MITRE ATT&CK
echo ""
echo "[3/7] Downloading MITRE ATT&CK..."
url="https://github.com/mitre-attack/attack-stix-data/raw/master/enterprise-attack/enterprise-attack.json"
output="${DATA_DIR}/enterprise-attack.json"

if download_with_retry "${url}" "${output}"; then
    echo "  ✓ MITRE ATT&CK downloaded"
else
    echo "  ✗ MITRE ATT&CK download failed"
fi

# 4. MITRE CAPEC
echo ""
echo "[4/7] Downloading MITRE CAPEC..."
url="https://capec.mitre.org/data/xml/capec_latest.xml"
output="${DATA_DIR}/capec_latest.xml"

if download_with_retry "${url}" "${output}"; then
    echo "  ✓ MITRE CAPEC downloaded"
else
    echo "  ✗ MITRE CAPEC download failed"
fi

# 5. MITRE CWE
echo ""
echo "[5/7] Downloading MITRE CWE..."
url="https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"
output="${DATA_DIR}/cwec_latest.xml.zip"

if download_with_retry "${url}" "${output}"; then
    echo "  ✓ MITRE CWE downloaded"
    # Optionally extract
    if command -v unzip >/dev/null 2>&1; then
        cd "${DATA_DIR}"
        unzip -q -o "${output}" 2>/dev/null || true
        echo "  ✓ CWE extracted"
    fi
else
    echo "  ✗ MITRE CWE download failed"
fi

# 6. MalwareBazaar
echo ""
echo "[6/7] Downloading MalwareBazaar full export..."
url="https://bazaar.abuse.ch/export/csv/full/"
output="${DATA_DIR}/full.csv.zip"

if download_with_retry "${url}" "${output}"; then
    echo "  ✓ MalwareBazaar downloaded"
else
    echo "  ✗ MalwareBazaar download failed"
fi

# 7. ThreatFox
echo ""
echo "[7/7] Downloading ThreatFox full export..."
url="https://threatfox.abuse.ch/export/json/"
output="${DATA_DIR}/threatfox_full.json.zip"

if download_with_retry "${url}" "${output}"; then
    echo "  ✓ ThreatFox downloaded"
else
    echo "  ✗ ThreatFox download failed"
fi

# Summary
echo ""
echo "=========================================="
echo "Download Summary"
echo "=========================================="
echo "Data directory: ${DATA_DIR}"
echo "Total files: $(find ${DATA_DIR} -type f | wc -l)"
echo "Total size: $(du -sh ${DATA_DIR} | cut -f1)"
echo ""
echo "✓ Day-Zero data download complete!"
echo ""

