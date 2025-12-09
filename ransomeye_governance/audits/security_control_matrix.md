# Path and File Name : /home/ransomeye/rebuild/ransomeye_governance/audits/security_control_matrix.md
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Mapping of RansomEye features to security controls (NIST/ISO 27001 aligned)

# RansomEye Security Control Matrix

**Project:** RansomEye Enterprise Cybersecurity Platform  
**Last Updated:** 2024-12-19  
**Standard Alignment:** NIST Cybersecurity Framework, ISO 27001

---

## Overview

This matrix maps RansomEye features and components to security controls, ensuring comprehensive coverage of enterprise security requirements.

---

## Control Categories

### 1. Access Control (AC)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| Agent Authentication | Linux/Windows Agent | AC-3: Access Enforcement | mTLS with client certificates (`AGENT_CERT_PATH`) |
| Probe Authentication | DPI Probe | AC-3: Access Enforcement | mTLS with client certificates (`PROBE_CERT_PATH`) |
| API Authentication | All Core APIs | AC-3: Access Enforcement | mTLS middleware, HMAC signatures |
| Playbook Execution | Incident Response | AC-6: Least Privilege | Signed playbooks with role-based execution |

### 2. Audit and Accountability (AU)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| Query Audit | DB Core | AU-2: Audit Events | `ransomeye_db_core/engine/query_audit.py` |
| Evidence Ledger | Forensic | AU-9: Protection of Audit Information | Immutable ledger with checksums |
| Activity Logging | All Modules | AU-12: Audit Generation | Centralized logging to `logs/` directory |
| Chain Bundles | Orchestrator | AU-9: Protection of Audit Information | Signed ZIP/PDF bundles with manifest |

### 3. Configuration Management (CM)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| Policy Hot-Reload | Alert Engine | CM-5: Access Restrictions | YAML policy loader with validation |
| Compliance Scanning | HNMP Engine | CM-6: Configuration Settings | `ransomeye_hnmp_engine/engine/compliance_scanner.py` |
| Systemd Services | All Modules | CM-7: Least Functionality | Centralized in `systemd/` directory |

### 4. Identification and Authentication (IA)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| Certificate Management | Agents/Probe | IA-5: Authenticator Management | Certificate rotation via signed updates |
| Playbook Signing | Incident Response | IA-7: Cryptographic Module Authentication | RSA-4096 signatures on playbooks |
| Bundle Signing | Orchestrator | IA-7: Cryptographic Module Authentication | RSA signing on chain bundles |

### 5. Incident Response (IR)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| Playbook Execution | Incident Response | IR-4: Incident Handling | `ransomeye_response/engine/executor.py` |
| Rollback Capability | Incident Response | IR-4: Incident Handling | Rollback mechanism in playbook executor |
| KillChain Timeline | KillChain Core | IR-4: Incident Handling | MITRE ATT&CK timeline builder |
| Forensic Dump | Forensic | IR-4: Incident Handling | Compressed evidence dumps with ledger |

### 6. System and Communications Protection (SC)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| Data in Transit | All Transport | SC-8: Transmission Confidentiality | mTLS encryption for all agent/probe communications |
| Data at Rest | DB Core | SC-28: Protection of Information at Rest | PII encryption (AES) in PostgreSQL |
| Buffer Persistence | Agents/Probe | SC-8: Transmission Confidentiality | Atomic writes to buffer directory |
| Signed Updates | Agents | SC-13: Cryptographic Protection | GPG/OpenSSL signature verification in update scripts |

### 7. System and Information Integrity (SI)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| SHAP Explainability | All ML Modules | SI-4: Information System Monitoring | Model explainability for auditability |
| Model Registry | AI Core | SI-7: Software, Firmware, and Information Integrity | Model metadata with hash verification |
| Threat Correlation | Correlation Engine | SI-4: Information System Monitoring | Entity graph with confidence scoring |
| IOC Deduplication | Threat Intel | SI-4: Information System Monitoring | Trust scoring and clustering |

### 8. Risk Assessment (RA)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| CVE Compliance | Network Scanner | RA-5: Vulnerability Scanning | `ransomeye_net_scanner/engine/cve_checker.py` |
| Fleet Health Scoring | HNMP Engine | RA-3: Risk Assessment | Compliance-based health scoring |
| Confidence Prediction | Correlation Engine | RA-3: Risk Assessment | ML-based confidence scoring with SHAP |

### 9. Security Assessment and Authorization (CA)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| Global Validator | Master Core | CA-2: Security Assessments | Synthetic end-to-end validation |
| Gate Verification | Governance | CA-2: Security Assessments | Automated gate checks (`check_gates.py`) |
| Port Audit | Governance | CA-2: Security Assessments | Hardcoded port detection (`port_usage_audit.py`) |

### 10. Planning (PL)

| Feature | Component | Control | Implementation |
|---------|-----------|---------|----------------|
| Implementation Plan | Governance | PL-2: System Security Plan | 12-week roadmap in `roadmap/implementation_plan.md` |
| Deliverable Matrix | Governance | PL-2: System Security Plan | CSV tracking in `roadmap/deliverable_matrix.csv` |
| Priority Tracker | Governance | PL-2: System Security Plan | JSON status in `roadmap/priority_tracker.json` |

---

## Feature-to-Control Mapping

### DPI Flow Classification
- **Security Controls:**
  - SC-8: Transmission Confidentiality (encrypted transport)
  - SI-4: Information System Monitoring (flow analysis)
  - SI-7: Software Integrity (ML model verification)
- **Implementation:** `ransomeye_dpi_probe/engine/capture_daemon.py`, `ransomeye_dpi_probe/ml/asset_classifier.pkl`

### Memory Diffing
- **Security Controls:**
  - IR-4: Incident Handling (forensic analysis)
  - AU-9: Protection of Audit Information (evidence integrity)
- **Implementation:** `ransomeye_forensic/diff/diff_memory.py`

### Malware DNA Extraction
- **Security Controls:**
  - SI-4: Information System Monitoring (threat detection)
  - SI-7: Software Integrity (YARA signature verification)
- **Implementation:** `ransomeye_forensic/dna/malware_dna.py`, `ransomeye_forensic/dna/yara_wrapper.py`

### Deception Framework
- **Security Controls:**
  - SI-4: Information System Monitoring (decoy placement)
  - AC-3: Access Enforcement (decoy access control)
- **Implementation:** `ransomeye_deception/engine/dispatcher.py`, `ransomeye_deception/engine/placement_engine.py`

### SOC Copilot (RAG)
- **Security Controls:**
  - SI-4: Information System Monitoring (assisted analysis)
  - AU-12: Audit Generation (feedback logging)
- **Implementation:** `ransomeye_assistant/engine/retriever_tfidf.py`, `ransomeye_assistant/engine/feedback_collector.py`

---

## Compliance Notes

1. **Offline Operation:** All modules operate offline/air-gapped, ensuring SC-7 (Boundary Protection) compliance.

2. **Data Retention:** DB Core enforces 7-year retention (configurable via `RETENTION_YEARS`), supporting AU-11 (Audit Record Retention).

3. **Model Explainability:** All ML models include SHAP outputs, supporting SI-4 (Information System Monitoring) auditability requirements.

4. **Signed Artifacts:** Playbooks, updates, and bundles are cryptographically signed, supporting SI-7 (Software Integrity).

5. **Centralized Logging:** All modules log to `logs/` directory with journald integration, supporting AU-12 (Audit Generation).

---

## Validation

This matrix is validated by:
- Phase 20: Global Validator (synthetic end-to-end testing)
- Phase 24: Project Governance (automated gate checks)

**Last Validated:** 2024-12-19

