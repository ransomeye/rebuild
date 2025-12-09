# RansomEye Global Validator (Phase 20)

## Overview

The Global Validator is the final gate for RansomEye, providing comprehensive validation of the entire platform through synthetic test scenarios, ML-based health scoring, and signed audit reports.

## Features

- **Synthetic Test Runner**: Injects synthetic ransomware alerts and validates the complete chain
- **ML Health Scoring**: RandomForest classifier with SHAP explainability
- **Signed PDF Reports**: Cryptographically signed validation reports using ReportLab
- **Chain of Custody**: Signed manifests and audit ledger for compliance
- **REST API**: FastAPI endpoints for triggering and managing validation runs
- **Prometheus Metrics**: Real-time metrics for monitoring validation performance

## Architecture

```
ransomeye_global_validator/
├── validator/          # Core validation engine
│   ├── synthetic_runner.py    # Orchestrates validation runs
│   ├── scenario_manager.py    # Manages test scenarios
│   ├── injector.py            # HTTP client for API injection
│   ├── verifier.py            # Database/API verification with backoff
│   ├── pdf_signer.py          # PDF generation and signing
│   └── pdf_verifier.py        # PDF signature verification
├── ml/                 # Machine Learning components
│   ├── validator_model.py     # Trainable RandomForest classifier
│   ├── train_validator.py     # Training script
│   ├── incremental_trainer.py # Autolearn loop
│   └── shap_support.py        # SHAP explainability
├── chain/              # Chain of custody
│   ├── manifest_builder.py    # Run manifest creation
│   ├── manifest_signer.py     # Manifest signing
│   └── manifest_verifier.py   # Manifest verification
├── storage/            # Persistence
│   ├── run_store.py          # Run artifact storage
│   └── audit_ledger.py       # Signed audit log
├── api/                # REST API
│   └── validator_api.py       # FastAPI application
├── metrics/             # Prometheus metrics
│   └── exporter.py            # Metrics exporter
└── tools/              # Utility scripts
    ├── create_test_keypair.py # Key generation
    └── export_pdf_bundle.py    # Bundle export
```

## Environment Variables

### Required
- `DB_HOST`: PostgreSQL host (default: localhost)
- `DB_PORT`: PostgreSQL port (default: 5432)
- `DB_NAME`: Database name (default: ransomeye)
- `DB_USER`: Database user (default: gagan)
- `DB_PASS`: Database password (default: gagan)

### API Configuration
- `VALIDATOR_API_PORT`: API port (default: 8100)
- `VALIDATOR_METRICS_PORT`: Metrics port (default: 9104)
- `VALIDATOR_API_HOST`: API host (default: 0.0.0.0)

### Service URLs
- `ALERT_ENGINE_URL`: Alert Engine API URL (default: http://localhost:8004)
- `KILLCHAIN_API_URL`: KillChain API URL (default: http://localhost:8005)
- `FORENSIC_API_URL`: Forensic API URL (default: http://localhost:8006)

### Security
- `VALIDATOR_SIGN_KEY_PATH`: Path to RSA private key for signing (default: keys/sign_key.pem)
- `VALIDATOR_PUBLIC_KEY_PATH`: Path to RSA public key for verification (default: keys/sign_key.pub)

### Storage
- `VALIDATOR_RUN_STORE_PATH`: Path to run storage directory
- `VALIDATOR_AUDIT_LEDGER_PATH`: Path to audit ledger file
- `VALIDATOR_MODEL_PATH`: Path to trained ML model
- `SHAP_OUTPUT_DIR`: Directory for SHAP outputs

## Usage

### Start the API Server

```bash
python3 /home/ransomeye/rebuild/ransomeye_global_validator/main.py
```

Or via systemd:

```bash
sudo systemctl start ransomeye-global-validator
```

### Trigger a Validation Run

```bash
curl -X POST http://localhost:8100/runs \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_type": "happy_path",
    "scenario_config": {}
  }'
```

### Download Validation Report

```bash
curl http://localhost:8100/runs/{run_id}/report -o report.pdf
```

### Generate Keypair

```bash
python3 /home/ransomeye/rebuild/ransomeye_global_validator/tools/create_test_keypair.py
```

### Train ML Model

```bash
python3 /home/ransomeye/rebuild/ransomeye_global_validator/ml/train_validator.py
```

## Validation Scenarios

### Happy Path
Validates the complete chain: Alert → KillChain → Forensic → DB
- Step 1: Inject synthetic ransomware alert
- Step 2: Verify incident creation in KillChain
- Step 3: Verify evidence logging in Forensic DB
- Step 4: Verify chain integrity

### Stress Test
Validates system performance under load with multiple concurrent alerts.

## API Endpoints

- `GET /`: Service information
- `GET /health`: Health check
- `POST /runs`: Trigger validation run
- `GET /runs/{run_id}`: Get run data
- `GET /runs/{run_id}/report`: Download PDF report
- `GET /runs/{run_id}/manifest`: Get signed manifest
- `GET /runs/{run_id}/verify`: Verify chain of custody
- `GET /runs`: List all runs

## Metrics

Prometheus metrics available at `http://localhost:9104/metrics`:

- `validator_runs_total`: Total validation runs
- `validator_success_rate`: Success rate gauge
- `validator_run_duration_seconds`: Run duration histogram
- `validator_api_latency_seconds`: API latency histogram
- `validator_ml_health_score`: ML health score gauge

## Fail-Closed Behavior

If validation fails, the validator:
1. Logs the failure to the signed audit ledger
2. Exits with non-zero status code
3. Generates a failure report with specific error details

## Dependencies

- FastAPI
- SQLAlchemy
- ReportLab
- PyCryptodome
- scikit-learn
- SHAP (optional, for explainability)
- prometheus-client
- aiohttp

## Notes

- All synthetic data is generated at runtime (no test data committed)
- PDFs are cryptographically signed using RSA
- Manifests provide chain of custody tracking
- ML model supports incremental training via autolearn loop
- SHAP explanations provide interpretability for health scores

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

