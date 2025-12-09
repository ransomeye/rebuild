#!/bin/bash
# Path and File Name : /home/ransomeye/rebuild/ransomeye_governance/gates/release_readiness.sh
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper script that runs unit tests, static IP scanner, and gate checks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/ransomeye/rebuild"
GOVERNANCE_DIR="${PROJECT_ROOT}/ransomeye_governance"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "RansomEye Release Readiness Check"
echo "============================================================"
echo ""

# Step 1: Run unit tests (if available)
echo -e "${YELLOW}[STEP 1/3] Running Unit Tests...${NC}"
if [ -f "${PROJECT_ROOT}/run_tests.sh" ]; then
    if bash "${PROJECT_ROOT}/run_tests.sh"; then
        echo -e "${GREEN}✅ Unit tests passed${NC}"
    else
        echo -e "${RED}❌ Unit tests failed${NC}"
        exit 1
    fi
elif [ -d "${PROJECT_ROOT}/tests" ]; then
    # Try to run pytest if available
    if command -v pytest &> /dev/null; then
        if pytest "${PROJECT_ROOT}/tests" -v; then
            echo -e "${GREEN}✅ Unit tests passed${NC}"
        else
            echo -e "${RED}❌ Unit tests failed${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  No test runner found, skipping unit tests${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No test directory found, skipping unit tests${NC}"
fi

echo ""

# Step 2: Run static IP/port scanner
echo -e "${YELLOW}[STEP 2/3] Running Port Usage Audit...${NC}"
PORT_AUDIT_SCRIPT="${GOVERNANCE_DIR}/audits/port_usage_audit.py"
if [ -f "${PORT_AUDIT_SCRIPT}" ]; then
    if python3 "${PORT_AUDIT_SCRIPT}"; then
        echo -e "${GREEN}✅ Port audit passed${NC}"
    else
        echo -e "${RED}❌ Port audit failed${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Port audit script not found: ${PORT_AUDIT_SCRIPT}${NC}"
    exit 1
fi

echo ""

# Step 3: Run gate checks
echo -e "${YELLOW}[STEP 3/3] Running Acceptance Gate Checks...${NC}"
GATE_CHECK_SCRIPT="${GOVERNANCE_DIR}/gates/check_gates.py"
if [ -f "${GATE_CHECK_SCRIPT}" ]; then
    if python3 "${GATE_CHECK_SCRIPT}"; then
        echo -e "${GREEN}✅ Gate checks passed${NC}"
    else
        echo -e "${RED}❌ Gate checks failed${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Gate check script not found: ${GATE_CHECK_SCRIPT}${NC}"
    exit 1
fi

echo ""
echo "============================================================"
echo -e "${GREEN}✅ ALL CHECKS PASSED - RELEASE READY${NC}"
echo "============================================================"
exit 0

