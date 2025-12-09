# Phase 13: Forensic Engine (Memory Diff & Malware DNA) - Implementation Summary

## Overview

Phase 13 implements advanced forensic analysis capabilities including:
- **Memory Diffing**: Streaming comparison of memory snapshots using rolling hashes
- **Malware DNA Extraction**: Feature extraction from binaries/artifacts
- **ML Classification**: Trainable models with SHAP explainability
- **Autolearn**: Incremental model updates from operator feedback

## Directory Structure

```
ransomeye_forensic/
├── diff/                    # Memory diffing module
│   ├── __init__.py
│   ├── diff_memory.py       # Main diffing logic
│   ├── snapshot_reader.py   # Memory snapshot parser
│   └── diff_algorithms.py   # Rolling hash & entropy algorithms
├── dna/                     # Malware DNA extraction
│   ├── __init__.py
│   ├── malware_dna.py       # Feature extraction
│   ├── sequence_extractor.py # API call sequence extraction
│   ├── dna_serializer.py    # Canonical DNA serialization
│   └── yara_wrapper.py      # YARA rule integration
├── ml/                      # ML classification
│   ├── __init__.py
│   ├── model_registry.py    # Model version management
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── classifier.py    # ML classifier with SHAP
│   │   └── fingerprinter.py # LSH/embedding generation
│   └── trainer/
│       ├── __init__.py
│       ├── train_classifier.py    # Full model training
│       └── incremental_trainer.py # Autolearn updates
├── api/
│   └── analysis_api.py      # New analysis endpoints
└── tests/
    └── test_phase13.py      # Integration tests
```

## Key Features

### 1. Memory Diffing (`diff/`)

- **Streaming Processing**: Handles large snapshots without loading entirely into RAM
- **Rolling Hash Algorithm**: Rabin-Karp implementation for efficient chunk comparison
- **Entropy Analysis**: Detects packed/encrypted regions
- **Page-level Comparison**: Identifies changed, added, and removed memory pages

**Usage:**
```python
from ransomeye_forensic.diff import MemoryDiffer

differ = MemoryDiffer()
result = differ.diff_snapshots("snapshot_a.raw", "snapshot_b.raw")
```

### 2. Malware DNA Extraction (`dna/`)

- **Static Features**: Hashes, entropy, strings, imports, sections
- **Dynamic Features**: API call sequences (simulated)
- **YARA Integration**: Rule-based detection
- **Canonical Serialization**: Deterministic JSON format for comparison

**Usage:**
```python
from ransomeye_forensic.dna import MalwareDNAExtractor, DNASerializer

extractor = MalwareDNAExtractor()
dna_data = extractor.extract_dna("artifact.bin", artifact_type="binary")

serializer = DNASerializer()
dna_hash = serializer.compute_dna_hash(dna_data)
```

### 3. ML Classification (`ml/`)

- **Trainable Models**: RandomForest classifier with scikit-learn
- **SHAP Explainability**: Feature contribution analysis for every prediction
- **Fingerprinting**: LSH/embedding generation for clustering
- **Model Registry**: Version management and integrity verification

**Usage:**
```python
from ransomeye_forensic.ml.inference import ForensicClassifier

classifier = ForensicClassifier(model_path="model.pkl")
prediction = classifier.predict(dna_data, return_shap=True)
# Returns: is_malicious, malicious_score, confidence, shap_values
```

### 4. Training & Autolearn (`ml/trainer/`)

- **Full Training**: Train models on labeled DNA data
- **Incremental Updates**: Autolearn from operator feedback
- **Feedback Loop**: Record corrections and trigger retraining

**Usage:**
```python
from ransomeye_forensic.ml.trainer import ClassifierTrainer, IncrementalTrainer

# Full training
trainer = ClassifierTrainer()
results = trainer.train_from_file("training_data.json", model_id="v1.0")

# Incremental update
incremental = IncrementalTrainer(model_path="model.pkl")
incremental.record_feedback(dna_id, dna_data, predicted_label, operator_label)
update_result = incremental.incremental_update()
```

## API Endpoints

New endpoints added to `/analysis`:

- `POST /analysis/diff` - Compare two memory snapshots
- `POST /analysis/dna/extract` - Extract DNA and classify artifact
- `POST /analysis/feedback` - Submit operator feedback for autolearn
- `GET /analysis/dna/{dna_id}` - Retrieve stored DNA signature
- `GET /analysis/diff/{diff_id}` - Retrieve stored diff results

## Testing

Comprehensive test suite in `tests/test_phase13.py`:

- **Synthetic Data Generator**: Creates test binaries/memory dumps (no real malware)
- **Memory Diffing Tests**: Rolling hash, entropy, snapshot comparison
- **DNA Extraction Tests**: Feature extraction, serialization, YARA scanning
- **ML Classification Tests**: Prediction, SHAP values, fingerprinting

Run tests:
```bash
cd /home/ransomeye/rebuild
python -m pytest ransomeye_forensic/tests/test_phase13.py -v
```

## Dependencies

Required packages (add to `requirements.txt`):
- `scikit-learn` - ML models
- `shap` - Explainability
- `yara-python` - YARA rule engine (optional)
- `numpy` - Numerical operations

## Environment Variables

- `MODEL_DIR` - Directory for ML models (default: `ransomeye_forensic/ml/models`)
- `YARA_RULES_DIR` - Directory for YARA rules (default: `ransomeye_forensic/rules/yara`)
- `FEEDBACK_DIR` - Directory for feedback data (default: `ransomeye_forensic/ml/feedback`)
- `ARTIFACT_STORAGE_DIR` - Artifact storage directory

## Production Notes

1. **Streaming**: Memory diffing uses page-based approach to handle 32GB+ snapshots
2. **SHAP**: TreeExplainer used for tree models; falls back to heuristic if unavailable
3. **YARA**: Gracefully handles missing rules directory
4. **Training**: Models must be trained before classification (heuristic fallback available)
5. **Synthetic Tests**: All test data is generated at runtime - no real malware samples

## Integration Points

- **DB Core**: DNA signatures and diff results should be stored in `artifacts` table
- **Alert Engine**: High-confidence malicious classifications trigger alerts
- **KillChain**: DNA features contribute to attack timeline
- **LLM Summarizer**: SHAP values included in incident summaries

## Next Steps

Phase 13 is complete. Ready for:
- Phase 14: LLM Behavior Summarizer (Expanded)
- Integration with other phases
- Production deployment and model training

