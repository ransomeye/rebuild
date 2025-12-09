# RansomEye Delivery Assurance (Phase 26)

## Overview

The Delivery Assurance framework provides comprehensive auditing and verification of the RansomEye platform before handover to production. This phase implements the final audit system that verifies architectural compliance, code quality, security hygiene, and deliverable completeness.

## Features

- **Structure Audit**: Verifies module existence, separation, and required directories
- **Content Audit**: Validates file headers in all source files
- **Installer Audit**: Ensures proper separation between core and standalone installers
- **Security Scan**: Detects hardcoded secrets, IPs, and sample data
- **PDF Reporting**: Generates comprehensive handover reports
- **Cryptographic Signing**: Signs reports with RSA-4096 signatures

## Quick Start

```bash
# Run full audit
cd /home/ransomeye/rebuild
python3 ransomeye_delivery_assurance/tools/run_final_audit.py

# Run specific category
python3 ransomeye_delivery_assurance/tools/run_final_audit.py --category structure
```

## Directory Structure

```
ransomeye_delivery_assurance/
├── definitions/          # Module manifests
│   ├── core_manifest.json
│   └── standalone_manifest.json
├── auditors/            # Audit engines
│   ├── structure_auditor.py
│   ├── content_auditor.py
│   └── installer_auditor.py
├── reporting/           # Report generation
│   ├── report_generator.py
│   └── signer.py
├── tools/               # CLI tools
│   ├── run_final_audit.py
│   └── scan_for_forbidden.py
├── docs/                # Documentation
│   └── HANDOVER_PROCESS.md
└── ci/                  # CI workflows
    └── .github/workflows/final_audit_check.yml
```

## Components

### Auditors

1. **StructureAuditor**: Verifies directory structure and module organization
2. **ContentAuditor**: Validates file headers in source files
3. **InstallerAuditor**: Checks installer script separation
4. **ForbiddenPatternScanner**: Scans for security violations

### Reporting

1. **ReportGenerator**: Creates PDF handover reports using reportlab
2. **ReportSigner**: Signs PDFs with RSA-4096 cryptographic signatures

### Tools

1. **run_final_audit.py**: Main orchestrator that runs all audits and generates reports
2. **scan_for_forbidden.py**: Standalone security scanner

## Usage

See [HANDOVER_PROCESS.md](docs/HANDOVER_PROCESS.md) for detailed usage instructions.

## Requirements

- Python 3.8+
- `reportlab` (PDF generation)
- `cryptography` (signing)

## Output

- `final_handover_report.pdf`: Comprehensive audit report
- `final_handover_report.pdf.sig`: Cryptographic signature
- `audit_results.json`: Machine-readable results

## CI Integration

The audit is integrated into GitHub Actions. See `ci/.github/workflows/final_audit_check.yml`.

## Support

- **Email**: Gagan@RansomEye.Tech
- **Project**: RansomEye.Tech

---

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

