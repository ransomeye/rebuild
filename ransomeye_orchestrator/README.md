# RansomEye Orchestrator - Phase 12

**Master Flow Orchestrator & Bundler**

## Overview

The RansomEye Orchestrator provides:
- **Durable Job Queue**: Postgres-backed queue with atomic locking
- **Streaming Bundle Builder**: Creates compressed bundles with zstandard/gzip
- **Cryptographic Verification**: RSA-PSS signing and verification
- **Rehydration Engine**: Restores incidents from bundles with idempotency
- **FastAPI**: RESTful API on port 8012
- **Prometheus Metrics**: Metrics exporter on port 9094

## Directory Structure

```
ransomeye_orchestrator/
├── queue/                  # Job queue and workers
│   ├── job_queue.py       # Postgres-backed queue with locking
│   └── worker_pool.py     # Async worker pool
├── bundle/                 # Bundle creation
│   ├── bundle_builder.py  # Main bundle builder
│   ├── chunker.py         # Streaming chunker with SHA256
│   ├── manifest.py        # Manifest generator
│   ├── signer.py          # RSA signing
│   └── verifier.py        # Signature verification
├── rehydrate/              # Rehydration engine
│   ├── rebuild_incident.py    # Main rehydration logic
│   ├── state_reconciler.py    # DB state reconciliation
│   └── artifact_ingestor.py   # Artifact restoration
├── storage/                # Storage management
│   ├── bundle_store.py    # Completed bundle storage
│   └── temp_store.py      # Temporary staging
├── api/                    # FastAPI endpoints
│   ├── orch_api.py        # Main API (port 8012)
│   └── auth_middleware.py # mTLS middleware
├── metrics/                # Prometheus metrics
│   └── exporter.py        # Metrics exporter (port 9094)
└── tools/                  # CLI tools
    ├── create_incident_bundle.py
    └── verify_bundle.py
```

## Features

### Durable Job Queue
- Postgres-backed with `SELECT ... FOR UPDATE SKIP LOCKED`
- Atomic job processing (no duplicate processing)
- Retry logic with configurable max retries
- Idempotency key support

### Streaming Bundle Builder
- Fetches data from KillChain, DB, and Forensic APIs
- Streams files (no RAM loading for large files)
- Zstandard compression (fallback to gzip)
- On-the-fly SHA256 calculation
- Chunking support for very large files

### Cryptographic Security
- RSA-PSS-SHA256 signing
- Fail-closed verification
- Manifest integrity checking
- File hash verification

### Rehydration Engine
- Signature verification (fail-closed)
- Idempotent restoration
- ON CONFLICT DO NOTHING for duplicates
- Artifact file restoration

## Setup

### Environment Variables

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ransomeye
DB_USER=gagan
DB_PASS=gagan

# Orchestrator
ORCH_API_PORT=8012
ORCH_METRICS_PORT=9094
ORCH_WORKER_COUNT=4

# Signing/Verification
ORCH_SIGN_KEY_PATH=/home/ransomeye/rebuild/certs/orch_sign_private.pem
ORCH_VERIFY_KEY_PATH=/home/ransomeye/rebuild/certs/orch_verify_public.pem

# Storage
OUTPUT_DIR=/home/ransomeye/rebuild/data
FORENSIC_STORAGE_PATH=/home/ransomeye/rebuild/data/forensic

# API URLs
CORE_API_URL=http://localhost:8080
KILLCHAIN_API_PORT=8005
FORENSIC_API_PORT=8006
DB_API_PORT=8009

# mTLS (optional)
MTLS_ENABLED=false
MTLS_CERT_DIR=/home/ransomeye/rebuild/certs/clients
```

### Start Service

```bash
systemctl start ransomeye-orchestrator
```

## Usage

### API Endpoints

#### Create Bundle
```bash
curl -X POST http://localhost:8012/bundle/create \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "incident-123",
    "priority": 100,
    "chunk_size_mb": 256
  }'
```

#### Start Rehydration
```bash
curl -X POST http://localhost:8012/rehydrate/start \
  -H "Content-Type: application/json" \
  -d '{
    "bundle_path": "/path/to/bundle.tar.zst",
    "verify_signature": true,
    "idempotency_key": "rehydrate-123"
  }'
```

#### Get Job Status
```bash
curl http://localhost:8012/jobs/{job_id}
```

### CLI Tools

#### Create Bundle
```bash
python3 tools/create_incident_bundle.py incident-123 -o /path/to/output
```

#### Verify Bundle
```bash
python3 tools/verify_bundle.py /path/to/bundle.tar.zst
```

## Database Schema

The orchestrator creates these tables:
- `orchestrator_jobs`: Job queue table
- `orchestrator_idempotency`: Idempotency tracking

## Streaming & Performance

- **Chunking**: Large files are chunked (default 256MB) with on-the-fly SHA256
- **Compression**: Zstandard preferred, gzip fallback
- **Memory**: Streaming I/O prevents RAM exhaustion
- **Locking**: `FOR UPDATE SKIP LOCKED` ensures atomic job processing

## Security

- **Signing**: RSA-PSS-SHA256 with private key
- **Verification**: Fail-closed (rejects invalid signatures)
- **mTLS**: Optional client certificate verification
- **Idempotency**: Prevents duplicate processing

## Metrics

Prometheus metrics available on port 9094:
- `orch_jobs_queued`: Number of queued jobs
- `orch_jobs_total`: Total jobs processed
- `orch_bundle_size_bytes`: Bundle sizes
- `orch_bundle_duration_seconds`: Bundle creation time

## Dependencies

Required Python packages:
- `psycopg2-binary>=2.9.0`
- `fastapi>=0.104.0`
- `uvicorn>=0.24.0`
- `prometheus-client>=0.19.0`
- `cryptography>=41.0.0`
- `requests>=2.31.0`
- `zstandard>=0.22.0` (optional, fallback to gzip)

## Troubleshooting

### Job Queue Issues
- Check PostgreSQL connection
- Verify table exists: `SELECT * FROM orchestrator_jobs LIMIT 1;`
- Check for locked jobs: `SELECT * FROM orchestrator_jobs WHERE status = 'processing';`

### Bundle Creation Fails
- Check API endpoints are accessible
- Verify artifact files exist
- Check disk space in temp directory

### Verification Fails
- Ensure `ORCH_VERIFY_KEY_PATH` is set correctly
- Check signature file exists in bundle
- Verify manifest hash matches

## License

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

