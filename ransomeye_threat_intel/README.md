# RansomEye Threat Intelligence / Day Zero (Phase 28)

## Overview

The Threat Intelligence module provides a Unified Threat Knowledge Graph and Narrative Reporting Engine for Day-Zero data hydration. It ingests threat intelligence from multiple sources and generates human-readable narrative reports.

## Features

- **Day-Zero Data Download**: Automated download of full historical threat intelligence data
- **Unified Knowledge Graph**: Relational database schema linking CVEs, CWEs, CAPEC, ATT&CK, and IOCs
- **Multi-Source Ingestion**: NVD, CISA KEV, MITRE (ATT&CK, CAPEC, CWE), Abuse.ch (MalwareBazaar, ThreatFox)
- **Narrative Engine**: Generates human-readable incident stories using Jinja2 templates
- **Streaming Support**: Handles large datasets without memory overflow

## Directory Structure

```
ransomeye_threat_intel/
├── tools/                    # Data download scripts
│   └── download_threat_data.sh
├── schema/                   # Database schema
│   └── knowledge_graph.py
├── ingestors/                # Data loaders
│   ├── nvd_loader.py
│   ├── cisa_kev_loader.py
│   ├── mitre_loader.py
│   └── abuse_ch_loader.py
├── narrative/                # Narrative engine
│   ├── story_builder.py
│   └── templates/
│       └── incident_story.j2
├── tests/                    # Unit tests
│   └── test_narrative_gen.py
└── data/                     # Downloaded data files
```

## Quick Start

### 1. Download Threat Data

```bash
bash ransomeye_threat_intel/tools/download_threat_data.sh
```

This downloads:
- NVD CVE data (2002 to current year)
- CISA Known Exploited Vulnerabilities
- MITRE ATT&CK, CAPEC, and CWE
- MalwareBazaar and ThreatFox exports

### 2. Create Database Schema

```bash
python3 ransomeye_threat_intel/schema/knowledge_graph.py
```

### 3. Ingest Data

```bash
# Load NVD data
python3 ransomeye_threat_intel/ingestors/nvd_loader.py

# Load CISA KEV
python3 ransomeye_threat_intel/ingestors/cisa_kev_loader.py

# Load MITRE data
python3 ransomeye_threat_intel/ingestors/mitre_loader.py

# Load Abuse.ch data
python3 ransomeye_threat_intel/ingestors/abuse_ch_loader.py
```

### 4. Generate Narrative Story

```bash
python3 ransomeye_threat_intel/narrative/story_builder.py CVE-2021-44228 --host-id host-001
```

## Data Sources

1. **NIST NVD**: CVE vulnerability database (2002-present)
2. **CISA KEV**: Known Exploited Vulnerabilities catalog
3. **MITRE ATT&CK**: Adversarial tactics and techniques
4. **MITRE CAPEC**: Common Attack Pattern Enumeration
5. **MITRE CWE**: Common Weakness Enumeration
6. **MalwareBazaar**: Malware hash database
7. **ThreatFox**: IOC database

## Knowledge Graph Schema

- **vulnerabilities**: CVE records with severity and CVSS scores
- **weaknesses**: CWE weakness definitions
- **attack_patterns**: CAPEC attack patterns
- **tactics**: MITRE ATT&CK tactics
- **mitigations**: CISA KEV required actions
- **iocs**: Indicators of Compromise (IPs, hashes, domains)

## Requirements

- Python 3.8+
- PostgreSQL
- `sqlalchemy`
- `psycopg2-binary`
- `jinja2`
- `wget` or `curl` (for download script)

## Environment Variables

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`: Database credentials
- `REBUILD_ROOT`: Project root directory

## Offline Operation

All ingestors accept local file paths and do not make network calls during ingestion. Download data first, then ingest from local files.

## Support

- **Email**: Gagan@RansomEye.Tech
- **Project**: RansomEye.Tech

---

© RansomEye.Tech | Support: Gagan@RansomEye.Tech
