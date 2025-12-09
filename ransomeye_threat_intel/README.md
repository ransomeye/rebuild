# Phase 18: Threat Intel Feed Engine

**Path:** `/home/ransomeye/rebuild/ransomeye_threat_intel/`

**Version:** 1.0.0

**Author:** nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU

## Overview

Phase 18 implements the Threat Intelligence Feed Engine with multi-source ingestion, normalization, deduplication, clustering, and ML-based trust scoring. This phase provides:

- **Multi-Source Ingestion**: STIX 2.1 (MISP/Wiz), API-based (MalwareBazaar, Ransomware.live), CSV/JSON
- **Normalization**: IP (IPv6 expand/compress), Domain (lowercase, strip protocols), Hash (lowercase)
- **Deduplication**: Exact (fingerprint) and Fuzzy (Levenshtein/SimHash)
- **Clustering**: Campaign grouping using connected components and ML-based clustering
- **Trust Scoring**: ML-based trust scoring with SHAP explainability
- **Storage**: PostgreSQL for IOCs, campaigns, and provenance
- **API**: FastAPI endpoints for ingestion, lookup, and export
- **Metrics**: Prometheus metrics for monitoring

## Architecture

```
Feed Sources → Ingestors → Normalizer → Enricher → Deduplicator → Clusterer → Trust Scorer → Storage
                                                                                    ↓
                                                                              Provenance Store
```

## Components

### Ingestors (`ingestors/`)

- **misp_ingestor.py**: STIX 2.1 JSON parser (Wiz/MITRE format)
- **api_ingestor.py**: Generic HTTP ingestor for JSON/CSV (MalwareBazaar, Ransomware.live)
- **poller.py**: Scheduled feed polling

### Normalizer (`normalizer/`)

- **normalizer.py**: Canonicalization for IP, Domain, Hash, URL
- **schema/canonical_ioc.schema.json**: JSON schema for normalized IOCs
- **enrichment.py**: GeoIP/ASN enrichment

### Deduplication (`dedup/`)

- **fingerprint.py**: SHA256 fingerprint generation
- **deduper.py**: Exact and fuzzy deduplication

### Clustering (`clusterer/`)

- **clusterer.py**: Campaign clustering (connected components + ML)
- **train_clusterer.py**: Embedding training for vector-based clustering

### Trust Scoring (`trust/`)

- **trust_score.py**: ML-based trust scoring with SHAP
- **train_trust_model.py**: Trust model training
- **incremental_trainer.py**: Autolearn from analyst feedback

### Storage (`storage/`)

- **ti_store.py**: PostgreSQL interface for IOCs and campaigns
- **provenance_store.py**: Source history tracking

### API (`api/`)

- **ti_api.py**: FastAPI endpoints (Port 8013)
- **auth_middleware.py**: mTLS/Token authentication

### Tools (`tools/`)

- **sign_manifest.py**: Manifest signing
- **verify_manifest.py**: Signature verification
- **export_bundle.py**: Signed IOC bundle export

### Metrics (`metrics/`)

- **exporter.py**: Prometheus metrics (Port 9095)

## Environment Variables

```bash
# API Configuration
TI_API_PORT=8013
TI_METRICS_PORT=9095

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ransomeye
DB_USER=gagan
DB_PASS=gagan

# Feed Sources
MISP_URL=https://misp.example.com
MISP_KEY=your-misp-key
TI_POLL_INTERVAL_SEC=3600

# GeoIP
GEOIP_DB_PATH=/path/to/GeoIP2.mmdb

# Models
TRUST_MODEL_PATH=/path/to/trust_model.pkl
CLUSTERER_MODEL_PATH=/path/to/clusterer_model.pkl

# Signing
TI_SIGN_KEY_PATH=/path/to/signing-key

# Authentication
TI_API_TOKEN=ransomeye-secure-token
```

## Usage

### Start API Server

```bash
cd /home/ransomeye/rebuild/ransomeye_threat_intel
python -m api.ti_api
```

### Ingest IOCs

```bash
curl -X POST http://localhost:8013/ingest \
  -H "Authorization: Bearer ransomeye-secure-token" \
  -H "Content-Type: application/json" \
  -d '{"iocs": [{"value": "192.168.1.1", "type": "ipv4", "source": "test"}]}'
```

### Query IOC

```bash
curl http://localhost:8013/ioc/192.168.1.1 \
  -H "Authorization: Bearer ransomeye-secure-token"
```

### Train Trust Model

```bash
python -m trust.train_trust_model \
    --data data/trust_training.json \
    --output models/trust_model.pkl
```

## API Endpoints

### POST /ingest

Ingest raw IOCs.

**Request:**
```json
{
  "iocs": [
    {
      "value": "192.168.1.1",
      "type": "ipv4",
      "source": "misp",
      "description": "Malicious IP"
    }
  ]
}
```

### GET /ioc/{value}

Get IOC with trust score, SHAP explanation, and campaign ID.

**Response:**
```json
{
  "value": "192.168.1.1",
  "type": "ipv4",
  "trust_score": 0.85,
  "shap_explanation": {...},
  "campaign_id": 123
}
```

### POST /export/bundle

Export IOC bundle as signed tarball.

## Compliance

✅ All files include required headers
✅ No hardcoded values (uses environment variables)
✅ PostgreSQL integration
✅ SHAP explainability support
✅ Signed exports
✅ Offline-ready (no external API dependencies during runtime)
✅ Restart-safe design

## Next Steps

After Phase 18 is validated, proceed to **Phase 19: HNMP Engine (Host Posture & Health)**.

