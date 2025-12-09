# RansomEye Delivery Assurance - Handover Process

## Overview

The Delivery Assurance framework provides comprehensive auditing and verification of the RansomEye platform before handover to production. This document describes the handover process and audit procedures.

## Purpose

The Delivery Assurance system verifies:

1. **Architectural Compliance**: Core modules are properly separated from standalone agents
2. **Code Quality**: All source files contain required headers and follow standards
3. **Security Hygiene**: No hardcoded secrets, IPs, or sample data in production code
4. **Installation Integrity**: Installers correctly separate core and standalone components
5. **Deliverable Completeness**: All required modules, tests, and documentation exist

## Prerequisites

- Python 3.8+
- Required packages (install via `pip install -r requirements.txt`):
  - `reportlab` (PDF generation)
  - `cryptography` (signing)
  - Standard library: `json`, `pathlib`, `re`, `os`

## Running the Audit

### Full Audit

Run the complete audit pipeline:

```bash
cd /home/ransomeye/rebuild
python3 ransomeye_delivery_assurance/tools/run_final_audit.py
```

### Specific Category

Run a single audit category:

```bash
# Structure audit only
python3 ransomeye_delivery_assurance/tools/run_final_audit.py --category structure

# Content audit only
python3 ransomeye_delivery_assurance/tools/run_final_audit.py --category content

# Installer audit only
python3 ransomeye_delivery_assurance/tools/run_final_audit.py --category installer

# Security scan only
python3 ransomeye_delivery_assurance/tools/run_final_audit.py --category security
```

### Options

- `--root <path>`: Specify project root (default: `/home/ransomeye/rebuild`)
- `--output <path>`: Specify output directory (default: `<root>/logs/delivery_assurance`)
- `--no-sign`: Skip PDF signing
- `--category <name>`: Run specific category (structure, content, installer, security, all)

## Audit Categories

### 1. Structure Audit

Verifies:
- All core modules (Phases 1-20) exist
- All standalone modules (Phases 21-23) exist
- Required directories (`systemd/`, `logs/`) exist
- Module separation is maintained
- Each module has `tests/` directory
- Each module has `README.md` or `docs/README.md`

**Manifests:**
- `definitions/core_manifest.json`: Core module definitions
- `definitions/standalone_manifest.json`: Standalone module definitions

### 2. Content Audit

Verifies:
- All `.py` and `.sh` files contain required header in first 5 lines:
  ```
  # Path and File Name : <absolute_path>
  # Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
  # Details of functionality of this file: <description>
  ```

**Exclusions:**
- Test files (`tests/test_*.py`)
- Documentation files (`docs/*.md`)
- Cache directories (`__pycache__`, `.pyc`, etc.)

### 3. Installer Audit

Verifies:
- Core installer (`ransomeye_install/install_core.sh`) does NOT reference:
  - `linux_agent`
  - `windows_agent`
  - `dpi_probe`
- Standalone modules have their own install scripts:
  - `ransomeye_linux_agent/install.sh`
  - `ransomeye_windows_agent/installer/build_installer.ps1`
  - `ransomeye_dpi_probe/admin/install_probe.sh`

### 4. Security Scan

Scans for:
- **Forbidden filenames**: `sample_data.csv`, `test.pcap`, `dummy*.pkl`, etc.
- **Hardcoded IPs**: Private IPs (192.168.x.x, 10.x.x.x, 172.x.x.x) in source code
- **Hardcoded credentials**: Passwords, API keys, tokens, secrets in code

**Allowed:**
- `127.0.0.1` (localhost)
- `0.0.0.0` (bind all)
- Environment variable references (`os.environ`, `${VAR}`)

## Output Files

After running the audit, the following files are generated in the output directory:

1. **`final_handover_report.pdf`**: Comprehensive PDF report with:
   - Executive summary
   - Detailed results by category
   - Error and warning listings
   - Footer: "© RansomEye.Tech | Support: Gagan@RansomEye.Tech"

2. **`final_handover_report.pdf.sig`**: Cryptographic signature file containing:
   - File hash (SHA-256)
   - RSA-PSS signature
   - Algorithm details

3. **`audit_results.json`**: Machine-readable audit results in JSON format

## Signing

The audit report is cryptographically signed using RSA-4096 with PSS padding and SHA-256 hashing.

**Key Location:**
- Default: `/home/ransomeye/rebuild/certs/audit_signing_key.pem`
- Override via `AUDIT_SIGN_KEY_PATH` environment variable

If the key doesn't exist, a new key pair is automatically generated.

**Verification:**
```python
from reporting.signer import ReportSigner

signer = ReportSigner()
is_valid = signer.verify_signature(
    pdf_path,
    signature_b64,
    expected_hash_b64
)
```

## Exit Codes

- `0`: All audits passed
- `1`: One or more audits failed

## CI Integration

The audit can be integrated into CI/CD pipelines. See:
- `ci/.github/workflows/final_audit_check.yml`

## Troubleshooting

### Common Issues

1. **Missing modules**: Ensure all core and standalone modules are present
2. **Header violations**: Run content audit to identify files missing headers
3. **Installer violations**: Check that core installer doesn't reference standalone modules
4. **Security violations**: Review hardcoded IPs/credentials and move to environment variables

### Debug Mode

For detailed output, run individual auditors directly:

```bash
# Structure auditor
python3 ransomeye_delivery_assurance/auditors/structure_auditor.py

# Content auditor
python3 ransomeye_delivery_assurance/auditors/content_auditor.py

# Installer auditor
python3 ransomeye_delivery_assurance/auditors/installer_auditor.py

# Security scanner
python3 ransomeye_delivery_assurance/tools/scan_for_forbidden.py
```

## Handover Checklist

Before handover, ensure:

- [ ] Full audit passes with zero errors
- [ ] All warnings are reviewed and resolved (or documented)
- [ ] PDF report is generated and signed
- [ ] Signature file is verified
- [ ] All required modules are present and functional
- [ ] Installation scripts are tested
- [ ] Documentation is complete

## Support

For issues or questions:
- **Email**: Gagan@RansomEye.Tech
- **Project**: RansomEye.Tech

---

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

