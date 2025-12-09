# Path and File Name : /home/ransomeye/rebuild/ransomeye_release_engineering/docs/RELEASE_PROCESS.md
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Documentation for RansomEye release packaging process

# RansomEye Release Process

## Overview

Phase 25 implements the Final Release Packaging & Gate Enforcement system for RansomEye. This system ensures that all release artifacts are properly validated, packaged, signed, and verified before delivery.

## Architecture

The release engineering module is located at:
```
/home/ransomeye/rebuild/ransomeye_release_engineering/
├── builder/              # Packaging and signing scripts
├── manifests/            # Manifest generation
├── validation/           # Verification and smoke tests
├── artifacts/            # Output directory for release artifacts
└── docs/                 # Documentation
```

## Release Process Flow

### 1. Gate Enforcement

Before any packaging begins, the system runs acceptance gates from Phase 24:
- **mTLS Check:** Verifies SSL context setup in agents/probe
- **SHAP Check:** Ensures SHAP explainability files exist
- **Buffer Check:** Verifies buffer/persistence logic
- **Signing Check:** Validates signed update scripts

**Location:** `/home/ransomeye/rebuild/ransomeye_governance/gates/check_gates.py`

If any gate fails, the release process **aborts immediately**.

### 2. Core Packaging

The Core Engine bundle includes:
- All backend modules (AI Core, Alert Engine, DB Core, etc.)
- Installation scripts (`install.sh`, `uninstall.sh`)
- Systemd service files
- Unified requirements.txt
- Governance and validation modules

**Excludes:** Standalone agents (Linux Agent, Windows Agent, DPI Probe)

**Output:** `ransomeye-core-{version}.tar.gz`

### 3. Agent Packaging

Standalone agents are packaged separately:

- **Linux Agent:** `ransomeye-linux-agent-{version}.tar.gz`
- **Windows Agent:** `ransomeye-windows-agent-{version}.zip`
- **DPI Probe:** `ransomeye-dpi-probe-{version}.tar.gz`

Each agent archive includes:
- Agent source code
- Installation scripts
- Updater scripts
- Required dependencies

### 4. Artifact Signing

All archives are signed using RSA-4096:
- **Method 1:** GPG (preferred)
- **Method 2:** OpenSSL (fallback)

**Signature files:** `{archive}.sig`

**Key location:** Set via `RELEASE_SIGN_KEY_PATH` environment variable

### 5. Manifest Generation

Two manifest files are generated:

1. **release_manifest.json:**
   - Version information
   - Artifact list with SHA256 hashes
   - File sizes
   - Signature status

2. **SHA256SUMS:**
   - Standard SHA256 checksum file
   - Compatible with `sha256sum -c`

## Usage

### Building a Release

```bash
cd /home/ransomeye/rebuild

# Set version (optional, defaults to VERSION file)
export RELEASE_VERSION="1.0.0"

# Set signing key (optional)
export RELEASE_SIGN_KEY_PATH="/path/to/private.key"

# Run release build
python3 ransomeye_release_engineering/builder/build_release.py
```

### Options

```bash
# Skip gate checks (NOT RECOMMENDED)
python3 ransomeye_release_engineering/builder/build_release.py --skip-gates

# Override version
python3 ransomeye_release_engineering/builder/build_release.py --version 1.2.3

# Specify signing key
python3 ransomeye_release_engineering/builder/build_release.py --sign-key /path/to/key.pem
```

### Verifying Release Artifacts

```bash
# Verify all artifacts
python3 ransomeye_release_engineering/validation/verify_release.py

# With public key for signature verification
python3 ransomeye_release_engineering/validation/verify_release.py \
    --public-key /path/to/public.key
```

### Running Smoke Tests

```bash
# Test artifact structure
python3 ransomeye_release_engineering/validation/final_smoke_test.py
```

## Output Structure

After a successful build, the `artifacts/` directory contains:

```
artifacts/
├── ransomeye-core-1.0.0.tar.gz
├── ransomeye-core-1.0.0.tar.gz.sig
├── ransomeye-linux-agent-1.0.0.tar.gz
├── ransomeye-linux-agent-1.0.0.tar.gz.sig
├── ransomeye-windows-agent-1.0.0.zip
├── ransomeye-windows-agent-1.0.0.zip.sig
├── ransomeye-dpi-probe-1.0.0.tar.gz
├── ransomeye-dpi-probe-1.0.0.tar.gz.sig
├── release_manifest.json
└── SHA256SUMS
```

## Version Management

Version is read from:
1. `--version` command-line argument (highest priority)
2. `RELEASE_VERSION` environment variable
3. `/home/ransomeye/rebuild/VERSION` file
4. Default: `1.0.0`

## Security Considerations

1. **Gate Enforcement:** Never skip gates in production builds
2. **Signing:** Always sign artifacts before distribution
3. **Verification:** Always verify signatures and checksums before deployment
4. **Key Management:** Store signing keys securely, never commit to repository

## CI/CD Integration

See `.github/workflows/build_release_candidate.yml` for GitHub Actions integration.

## Troubleshooting

### Gate Check Fails

If gates fail, review the output from `check_gates.py`:
```bash
python3 ransomeye_governance/gates/check_gates.py
```

Fix the reported issues before retrying the release build.

### Signing Fails

If signing fails:
1. Verify `RELEASE_SIGN_KEY_PATH` points to a valid key file
2. Ensure GPG or OpenSSL is installed
3. Check key file permissions

### Archive Extraction Issues

If smoke tests fail:
1. Verify archive format (tar.gz vs zip)
2. Check file permissions
3. Ensure sufficient disk space

## Compliance

This release process ensures:
- ✅ All gates pass before packaging
- ✅ Core and Agents are strictly separated
- ✅ All artifacts are signed
- ✅ Manifests provide full provenance
- ✅ Structure verified via smoke tests

## Support

For issues or questions:
- **Email:** Gagan@RansomEye.Tech
- **Documentation:** See Phase 24 Governance documentation

