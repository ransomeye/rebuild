# Phase 20: Global Validator - Validation Checklist

## ✅ Hard Constraints Verification

### 1. Directory Standards
- ✅ Root path: `/home/ransomeye/rebuild/ransomeye_global_validator/`
- ✅ All internal imports use relative paths (e.g., `from ..ml.validator_model import ValidatorModel`)
- ✅ All modules properly structured

### 2. Network Configuration
- ✅ Validator API: Port `8100` (VALIDATOR_API_PORT)
- ✅ Metrics: Port `9104` (VALIDATOR_METRICS_PORT)
- ✅ DB Connection: Uses `os.environ` with defaults (DB_USER=gagan, DB_PASS=gagan, DB_PORT=5432)

### 3. File Headers
- ✅ All Python files have mandatory header:
  ```python
  # Path and File Name : <absolute_path>
  # Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
  # Details of functionality of this file: <description>
  ```

### 4. Integrity & AI
- ✅ Trainable ML Model: RandomForest classifier in `ml/validator_model.py`
- ✅ SHAP Support: Integrated in `ml/shap_support.py` and called in `synthetic_runner.py`
- ✅ Signed PDF: RSA cryptographic signing in `validator/pdf_signer.py` using `VALIDATOR_SIGN_KEY_PATH`

### 5. Fail-Closed
- ✅ Validation failures raise exceptions (non-zero exit)
- ✅ Failures logged to signed audit ledger
- ✅ Specific error messages in exception details

## ✅ Directory Structure Verification

### A. Validator Engine (`validator/`)
1. ✅ `synthetic_runner.py` - Orchestrates validation runs
2. ✅ `scenario_manager.py` - Defines Happy Path with 3 steps + chain integrity
3. ✅ `injector.py` - HTTP client for ALERT_ENGINE_URL, KILLCHAIN_API_URL, FORENSIC_API_URL
4. ✅ `verifier.py` - DB/API verification with exponential backoff
5. ✅ `pdf_signer.py` - ReportLab PDF generation with RSA signing
6. ✅ `pdf_verifier.py` - PDF signature verification

### B. ML Validator (`ml/`)
1. ✅ `validator_model.py` - RandomForest classifier (api_latency, queue_depth, error_count → is_healthy)
2. ✅ `train_validator.py` - Training script with synthetic data generation
3. ✅ `incremental_trainer.py` - Autolearn loop for continuous training
4. ✅ `shap_support.py` - SHAP plots/values generation

### C. Chain of Custody (`chain/`)
1. ✅ `manifest_builder.py` - Creates run_manifest.json (Start Time, Scenarios, Results)
2. ✅ `manifest_signer.py` - Signs run manifest with RSA
3. ✅ `manifest_verifier.py` - Verifies manifest signatures and chain

### D. Storage & Tools
1. ✅ `storage/run_store.py` - Persists run artifacts (PDFs, logs) to disk
2. ✅ `storage/audit_ledger.py` - Signed append-only log of validation runs
3. ✅ `tools/create_test_keypair.py` - Generates ephemeral RSA keypairs
4. ✅ `tools/export_pdf_bundle.py` - Exports signed PDF + Proofs

### E. API & Metrics
1. ✅ `api/validator_api.py` - FastAPI on port 8100
   - ✅ `POST /runs` - Trigger validation
   - ✅ `GET /runs/{id}/report` - Download PDF
   - ✅ Additional endpoints: GET /runs/{id}, GET /runs, GET /runs/{id}/manifest, GET /runs/{id}/verify
2. ✅ `metrics/exporter.py` - Prometheus metrics:
   - ✅ `validator_runs_total`
   - ✅ `validator_success_rate`
   - ✅ Additional metrics: duration, latency, ML health score

## ✅ Implementation Requirements

### ReportLab PDF
- ✅ Professional-looking PDF with tables
- ✅ Pass/Fail status for each step
- ✅ Summary section with metrics
- ✅ Footer with branding: "© RansomEye.Tech | Support: Gagan@RansomEye.Tech"

### Exponential Backoff
- ✅ Implemented in `verifier.py`:
  - `verify_alert_in_db()` - Starts at 1s, doubles to max 10s
  - `verify_incident_created()` - Starts at 1s, doubles to max 10s
  - `verify_evidence_logged()` - Starts at 2s, doubles to max 15s

### Fail-Loud Behavior
- ✅ Alert API failures raise exceptions immediately
- ✅ Specific error messages in exception details
- ✅ All exceptions logged with full context

### Synthetic Data Generation
- ✅ No test data committed
- ✅ All data generated at runtime in `scenario_manager.py`:
  - Random IP addresses
  - Random file hashes (SHA256)
  - Random file paths
  - Random encryption extensions
  - Random process names

### Happy Path Scenario Steps
1. ✅ Step 1: Inject Synthetic Ransomware Alert
   - Calls `injector.inject_alert()`
   - Stores alert_id in scenario data

2. ✅ Step 2: Poll KillChain for Incident Creation
   - Calls `injector.build_timeline()` to trigger KillChain
   - Polls `verifier.verify_incident_created()` with exponential backoff
   - Verifies incident exists in timeline_records table

3. ✅ Step 3: Poll Forensic DB for Artifact Logging
   - Calls `verifier.verify_evidence_logged()` with exponential backoff
   - Verifies SHA256 hash matches injected value
   - Checks evidence_ledger table

4. ✅ Step 4: Verify Chain Integrity
   - Calls `verifier.verify_chain_integrity()`
   - Verifies alert_id → incident_id → evidence_id relationships

## ✅ Additional Features Implemented

- ✅ Main entry point: `main.py` for running the API server
- ✅ systemd service file: `systemd/ransomeye-global-validator.service`
- ✅ README.md with comprehensive documentation
- ✅ ML health scoring integrated into validation flow
- ✅ SHAP explanations generated for each run
- ✅ Signed manifests for chain of custody
- ✅ Audit ledger with cryptographic signatures
- ✅ Metrics integration for Prometheus monitoring

## ✅ Code Quality

- ✅ No placeholders - all logic is implemented
- ✅ Proper error handling throughout
- ✅ Comprehensive logging
- ✅ Type hints where appropriate
- ✅ Docstrings for all classes and methods
- ✅ No linter errors

## Summary

**Phase 20: Global Validator is 100% complete** with all requirements met:
- ✅ All 28 Python files created with complete implementation
- ✅ All hard constraints satisfied
- ✅ All directory structure requirements met
- ✅ All implementation instructions followed
- ✅ Additional production-ready features included

The validator is ready for deployment and can be used to validate the entire RansomEye platform end-to-end.

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

