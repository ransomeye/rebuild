# Path and File Name : /home/ransomeye/rebuild/ransomeye_governance/docs/GOVERNANCE.md
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Comprehensive guide on using governance tools and processes for adding new features

# RansomEye Project Governance Guide

**Version:** 1.0.0  
**Last Updated:** 2024-12-19  
**Project Root:** `/home/ransomeye/rebuild/`

---

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Roadmap & Tracking](#roadmap--tracking)
4. [Acceptance Gates](#acceptance-gates)
5. [Security Audits](#security-audits)
6. [Adding New Features](#adding-new-features)
7. [Release Process](#release-process)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The RansomEye Project Governance layer provides automated tools and processes to ensure:
- **Consistency:** All modules follow the same standards
- **Security:** Hardcoded values, missing controls, and policy violations are detected automatically
- **Quality:** Acceptance gates verify critical requirements before release
- **Traceability:** Roadmap and deliverables are tracked and documented

---

## Directory Structure

```
ransomeye_governance/
├── roadmap/                    # Planning and tracking
│   ├── implementation_plan.md      # 12-week schedule with priorities
│   ├── deliverable_matrix.csv       # Phase-to-artifact mapping
│   └── priority_tracker.json        # Machine-readable P0 status
├── gates/                     # Acceptance gate verification
│   ├── check_gates.py              # Automated gate checker
│   ├── verification_policies.yaml   # Gate configuration
│   └── release_readiness.sh         # Full release check wrapper
├── audits/                    # Security and compliance audits
│   ├── port_usage_audit.py         # Hardcoded port scanner
│   └── security_control_matrix.md   # Feature-to-control mapping
└── docs/                      # Documentation
    └── GOVERNANCE.md               # This file
```

---

## Roadmap & Tracking

### Implementation Plan

**File:** `roadmap/implementation_plan.md`

The implementation plan provides a 12-week schedule with P0 (Critical), P1 (High), and P2 (Normal) priorities. Each phase includes:
- Target completion week
- Required deliverables
- Acceptance criteria
- File paths

**Usage:**
- Review weekly to track progress
- Update status as phases complete
- Reference for sprint planning

### Deliverable Matrix

**File:** `roadmap/deliverable_matrix.csv`

CSV format with columns:
- `Phase`: Phase number (1-24)
- `Component`: Component name
- `Artifact_Path`: Absolute file path
- `Priority`: P0, P1, or P2
- `Status`: COMPLETE, IN_PROGRESS, or PLANNED

**Usage:**
```bash
# View matrix
cat ransomeye_governance/roadmap/deliverable_matrix.csv

# Filter by priority
grep "P0" ransomeye_governance/roadmap/deliverable_matrix.csv
```

### Priority Tracker

**File:** `roadmap/priority_tracker.json`

Machine-readable JSON with:
- P0 critical items and their gates
- P1 high-priority items
- P2 normal items

**Usage:**
```python
import json
with open('ransomeye_governance/roadmap/priority_tracker.json') as f:
    tracker = json.load(f)
    print(tracker['p0_critical'])
```

---

## Acceptance Gates

### Gate Checker

**File:** `gates/check_gates.py`

Automated verification of:
1. **mTLS Implementation:** Verifies SSL context setup in agent/probe transport files
2. **SHAP Explainability:** Ensures SHAP files exist in all ML modules
3. **Buffer/Persistence:** Verifies buffer logic in agents and probe
4. **Signed Updates:** Checks for signed update scripts

**Usage:**
```bash
cd /home/ransomeye/rebuild
python3 ransomeye_governance/gates/check_gates.py
```

**Output:**
- ✅ PASS: Gate passed
- ❌ FAIL: Gate failed (with specific error)
- ⚠️  WARNING: Gate passed but with warnings

**Exit Code:**
- `0`: All gates passed
- `1`: One or more gates failed

### Verification Policies

**File:** `gates/verification_policies.yaml`

Configuration file defining:
- Required file patterns per module
- Regex patterns for verification
- Minimum pattern matches required
- Whitelisted files

**Modifying Policies:**
1. Edit `verification_policies.yaml`
2. Run `check_gates.py` to verify changes
3. Update this documentation if new policies are added

### Release Readiness

**File:** `gates/release_readiness.sh`

Wrapper script that runs:
1. Unit tests (if available)
2. Port usage audit
3. Gate checks

**Usage:**
```bash
cd /home/ransomeye/rebuild
bash ransomeye_governance/gates/release_readiness.sh
```

**Exit Code:**
- `0`: All checks passed (release ready)
- `1`: One or more checks failed

---

## Security Audits

### Port Usage Audit

**File:** `audits/port_usage_audit.py`

Scans the entire codebase for hardcoded ports using regex patterns. Fails if restricted ports (8080, 5432, 3000, etc.) are found outside of:
- Whitelisted configuration files
- Allowed contexts (environment variables, config.get, etc.)

**Restricted Ports:**
- 8080, 5432, 3000, 3306, 6379, 8443, 9090-9094

**Usage:**
```bash
cd /home/ransomeye/rebuild
python3 ransomeye_governance/audits/port_usage_audit.py
```

**Output:**
- Lists all violations with file, line number, and context
- Provides summary of scanned files

**Fixing Violations:**
1. Replace hardcoded ports with environment variables:
   ```python
   # ❌ BAD
   port = 8080
   
   # ✅ GOOD
   port = int(os.environ.get('CORE_API_PORT', '8080'))
   ```
2. If port must be in code, add to whitelist in `verification_policies.yaml`

### Security Control Matrix

**File:** `audits/security_control_matrix.md`

Maps RansomEye features to NIST/ISO 27001 security controls:
- Access Control (AC)
- Audit and Accountability (AU)
- Configuration Management (CM)
- Identification and Authentication (IA)
- Incident Response (IR)
- System and Communications Protection (SC)
- System and Information Integrity (SI)
- Risk Assessment (RA)
- Security Assessment and Authorization (CA)
- Planning (PL)

**Usage:**
- Reference for compliance audits
- Feature-to-control mapping for new features
- Validation checklist for security requirements

---

## Adding New Features

### Step 1: Update Roadmap

1. **Add to Implementation Plan:**
   - Edit `roadmap/implementation_plan.md`
   - Assign priority (P0/P1/P2)
   - Set target completion week
   - Define acceptance criteria

2. **Add to Deliverable Matrix:**
   - Edit `roadmap/deliverable_matrix.csv`
   - Add row with Phase, Component, Artifact_Path, Priority, Status

3. **Update Priority Tracker:**
   - Edit `roadmap/priority_tracker.json`
   - Add entry to appropriate priority section
   - Define required gates

### Step 2: Implement Feature

Follow RansomEye standards:
- ✅ No hardcoded IPs, ports, or credentials
- ✅ Use environment variables via `os.environ.get()`
- ✅ Include file header in all Python/script files
- ✅ Add SHAP explainability if ML/AI feature
- ✅ Implement mTLS if network communication
- ✅ Add buffer/persistence if agent/probe feature
- ✅ Sign updates if agent feature

### Step 3: Update Gate Policies (if needed)

If new feature requires new gate checks:

1. **Edit `gates/verification_policies.yaml`:**
   - Add new requirement section
   - Define file patterns and regex

2. **Update `gates/check_gates.py`:**
   - Add new check method
   - Integrate into `run_all_checks()`

3. **Test:**
   ```bash
   python3 ransomeye_governance/gates/check_gates.py
   ```

### Step 4: Update Security Control Matrix

1. **Edit `audits/security_control_matrix.md`:**
   - Map feature to relevant security controls
   - Document implementation path
   - Add to feature-to-control mapping section

### Step 5: Run Validation

```bash
# Full release readiness check
bash ransomeye_governance/gates/release_readiness.sh

# Individual checks
python3 ransomeye_governance/gates/check_gates.py
python3 ransomeye_governance/audits/port_usage_audit.py
```

---

## Release Process

### Pre-Release Checklist

1. **All P0 Phases Complete:**
   ```bash
   python3 -c "import json; t=json.load(open('ransomeye_governance/roadmap/priority_tracker.json')); print('P0 Complete:', all(v['status']=='complete' for v in t['p0_critical'].values()))"
   ```

2. **Run Release Readiness:**
   ```bash
   bash ransomeye_governance/gates/release_readiness.sh
   ```

3. **Verify Exports:**
   - All user-facing modules export PDF, HTML, CSV
   - Footer includes: "© RansomEye.Tech | Support: Gagan@RansomEye.Tech"

4. **Verify Offline Operation:**
   - Test all modules without internet connectivity
   - Verify IOC feeds are cached locally

5. **Verify Systemd Services:**
   - All master-core services in `systemd/` directory
   - All services have `Restart=always`

### Release Steps

1. **Update Status:**
   - Mark Phase 24 as COMPLETE in `deliverable_matrix.csv`
   - Update `priority_tracker.json` status

2. **Generate Validation Report:**
   - Run Phase 20 Global Validator
   - Verify `validation_summary.pdf` generated

3. **Final Gate Check:**
   ```bash
   bash ransomeye_governance/gates/release_readiness.sh
   ```

4. **Tag Release:**
   ```bash
   git tag -a v1.0.0 -m "RansomEye Phase 24 Complete"
   ```

---

## Troubleshooting

### Gate Check Failures

**mTLS Check Fails:**
- Verify `AGENT_CERT_PATH` or `PROBE_CERT_PATH` is used in transport files
- Check for SSL context setup (cert, key, verify=True)
- Ensure file exists at expected path

**SHAP Check Fails:**
- Verify SHAP file exists: `find . -name "*shap*.py" -path "*/ransomeye_*/"`
- Check file is in correct module directory
- Ensure file has actual implementation (not placeholder)

**Buffer Check Fails:**
- Verify `persistence.py` exists in agent/probe `engine/` directory
- Check for `BUFFER_DIR` environment variable usage
- Ensure buffer logic implements atomic writes

**Signing Check Fails:**
- Verify `apply_update.sh` (Linux) or `apply_update.ps1` (Windows) exists
- Check for signature verification code (gpg, openssl, Get-AuthenticodeSignature)
- Ensure file is not empty or placeholder

### Port Audit Failures

**False Positives:**
- Add file to whitelist in `verification_policies.yaml`
- Check if port is in allowed context (environment variable, config.get)
- Verify port is not part of version number

**True Violations:**
- Replace hardcoded port with environment variable
- Use `os.environ.get('PORT_NAME', 'default')` pattern
- Update configuration files instead of code

### Release Readiness Failures

**Unit Tests Fail:**
- Fix failing tests
- Ensure test directory exists: `tests/`
- Verify pytest is installed: `pip install pytest`

**Port Audit Fails:**
- Fix hardcoded ports (see Port Audit Failures above)
- Re-run: `python3 ransomeye_governance/audits/port_usage_audit.py`

**Gate Checks Fail:**
- Fix individual gate failures (see Gate Check Failures above)
- Re-run: `python3 ransomeye_governance/gates/check_gates.py`

---

## Best Practices

1. **Run Gates Before Committing:**
   ```bash
   python3 ransomeye_governance/gates/check_gates.py
   ```

2. **Check Ports Regularly:**
   ```bash
   python3 ransomeye_governance/audits/port_usage_audit.py
   ```

3. **Update Roadmap Weekly:**
   - Review `implementation_plan.md`
   - Update `deliverable_matrix.csv` status
   - Refresh `priority_tracker.json`

4. **Document New Features:**
   - Update security control matrix
   - Add to deliverable matrix
   - Update implementation plan if needed

5. **Use Release Readiness for CI/CD:**
   ```bash
   # In CI pipeline
   bash ransomeye_governance/gates/release_readiness.sh || exit 1
   ```

---

## Support

**Questions or Issues:**
- Review this documentation
- Check `verification_policies.yaml` for configuration
- Review gate check output for specific errors
- Contact: Gagan@RansomEye.Tech

**Contributing:**
- Follow RansomEye standards (no hardcoded values, file headers, etc.)
- Run gate checks before submitting
- Update documentation for new features

---

**Last Updated:** 2024-12-19  
**Version:** 1.0.0

