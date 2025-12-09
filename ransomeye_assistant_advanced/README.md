# Phase 15: Advanced SOC Copilot (Multi-Modal & Playbook Routing)

## Overview

Phase 15 extends Phase 7 (SOC Copilot) with advanced multi-modal capabilities including OCR, vision detection, and intelligent playbook routing. This phase enables the SOC Copilot to process images, screenshots, and PDFs, extract text and detect security-relevant objects, and automatically suggest appropriate incident response playbooks.

## Features

### 1. Multi-Modal Ingestion
- **OCR (Optical Character Recognition)**: Extracts text from images using Tesseract
- **Vision Detection**: Detects security-relevant objects (error dialogs, terminals, browsers) using ONNX-based YOLO model
- **Image Captioning**: Combines OCR text and detected objects into scene descriptions
- **PDF Processing**: Extracts text from PDF documents

### 2. Intelligent Playbook Routing
- **ML-Based Matching**: Uses RandomForestClassifier to map incident summaries to playbook IDs
- **Feature Engineering**: Converts text and detected objects into feature vectors
- **SHAP Explainability**: Provides explanations for why specific playbooks are suggested
- **Rule-Based Fallback**: Falls back to rule-based matching when ML model unavailable

### 3. Feedback & Autolearn
- **Feedback Collection**: Records analyst feedback on playbook suggestions
- **Signed Training Bundles**: Exports feedback as signed .tar.gz bundles for offline model improvement
- **Provenance Tracking**: Links artifacts to incidents in database

### 4. Storage & Embeddings
- **Artifact Store**: Chunked storage for uploaded images/logs with metadata
- **Multi-Modal Embeddings**: Concatenates text and image embeddings for similarity search
- **FAISS Vector Store**: Fast similarity search for artifact retrieval

## Directory Structure

```
ransomeye_assistant_advanced/
├── api/
│   ├── assistant_api.py          # FastAPI application (port 8008)
│   └── auth_middleware.py        # Token/mTLS authentication
├── multi_modal/
│   ├── multi_modal.py            # Multi-modal orchestrator
│   ├── image_pipeline.py        # Image preprocessing
│   ├── ocr/
│   │   ├── ocr_runner.py        # Tesseract OCR wrapper
│   │   └── train_ocr.py         # OCR training interface
│   ├── vision/
│   │   └── det_runner.py        # ONNX vision detector
│   └── image_captioner/
│       └── captioner.py         # Scene description generator
├── playbook/
│   ├── playbook_router.py       # Main playbook router
│   ├── playbook_matcher.py     # ML-based playbook matcher
│   └── train_playbook_mapper.py # Training script
├── embedding/
│   ├── mm_embedder.py          # Multi-modal embedder
│   └── vector_store.py         # FAISS vector store
├── storage/
│   ├── artifact_store.py       # Artifact storage
│   └── provenance.py           # Provenance tracker
├── feedback/
│   ├── feedback_collector.py   # Feedback collection
│   └── feedback_exporter.py    # Signed bundle exporter
├── explain/
│   └── shap_integration.py     # SHAP explainability
├── cli/
│   └── assistant_cli.py        # CLI tools
├── metrics/
│   └── exporter.py             # Prometheus metrics
└── config/
    └── sample.env               # Environment configuration
```

## API Endpoints

### POST /ingest
Upload a multi-modal artifact (image/PDF) for processing.

**Request:**
- `file`: Image or PDF file
- `description` (optional): Artifact description
- `incident_id` (optional): Associated incident ID

**Response:**
```json
{
  "artifact_id": "uuid",
  "metadata": {...},
  "ocr_text": "extracted text",
  "detected_objects": ["error_dialog", "terminal"],
  "scene_description": "Scene description"
}
```

### POST /suggest_playbook
Suggest a playbook based on artifact or incident summary.

**Request:**
```json
{
  "artifact_id": "uuid",
  "incident_summary": "Ransomware detected on host",
  "include_shap": true
}
```

**Response:**
```json
{
  "playbook_id": 1,
  "playbook_name": "Isolate Host",
  "confidence": 0.85,
  "shap_explanations": {...},
  "reasoning": "Detected ransomware indicators..."
}
```

### POST /feedback
Submit feedback on playbook suggestion.

**Request:**
```json
{
  "artifact_id": "uuid",
  "playbook_id": 1,
  "accepted": true,
  "comment": "Optional comment"
}
```

## Environment Variables

See `config/sample.env` for all configuration options. Key variables:

- `ASSISTANT_API_PORT`: API port (default: 8008)
- `ASSISTANT_METRICS_PORT`: Metrics port (default: 9100)
- `ARTIFACT_STORAGE_DIR`: Artifact storage directory
- `VISION_MODEL_PATH`: Path to ONNX vision model
- `PLAYBOOK_MODEL_PATH`: Path to trained playbook matcher model
- `TESSDATA_PREFIX`: Tesseract data directory

## Dependencies

### Required Python Packages:
- `fastapi`, `uvicorn` - API framework
- `pytesseract` - OCR
- `onnxruntime` - Vision model inference
- `scikit-learn` - ML models
- `sentence-transformers` - Text embeddings
- `faiss-cpu` - Vector search
- `shap` - Explainability
- `prometheus-client` - Metrics
- `cryptography` - Signing
- `sqlalchemy`, `psycopg2` - Database
- `Pillow` - Image processing

### System Dependencies:
- `tesseract-ocr` - OCR binary
- PostgreSQL - Database

## Installation

1. Install system dependencies:
```bash
sudo apt-get install tesseract-ocr
```

2. Install Python packages (add to unified requirements.txt):
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp config/sample.env config/.env
# Edit config/.env with your settings
```

4. Start service:
```bash
sudo systemctl enable ransomeye-assistant-advanced
sudo systemctl start ransomeye-assistant-advanced
```

## Usage

### CLI Tool

Ingest an artifact:
```bash
python -m ransomeye_assistant_advanced.cli.assistant_cli ingest screenshot.png --incident-id INC-001
```

Suggest a playbook:
```bash
python -m ransomeye_assistant_advanced.cli.assistant_cli suggest --artifact-id <uuid>
```

Submit feedback:
```bash
python -m ransomeye_assistant_advanced.cli.assistant_cli feedback <artifact-id> <playbook-id> --accepted
```

### Training Playbook Matcher

Train the playbook matcher model from feedback data:
```bash
python -m ransomeye_assistant_advanced.playbook.train_playbook_mapper
```

## Integration

- **Phase 6 (Response)**: Fetches playbooks from playbook registry
- **Phase 7 (Assistant)**: Extends existing assistant capabilities
- **Database**: Stores artifacts, feedback, and provenance links

## Metrics

Prometheus metrics available at `/metrics`:
- `assistant_advanced_ingest_total` - Total artifacts ingested
- `assistant_advanced_ocr_duration_seconds` - OCR processing time
- `assistant_advanced_vision_duration_seconds` - Vision detection time
- `assistant_advanced_playbook_confidence` - Playbook suggestion confidence
- `assistant_advanced_feedback_total` - Feedback submissions

## Offline Operation

All processing is done locally:
- OCR: Tesseract (local binary)
- Vision: ONNX runtime (local model)
- Embeddings: sentence-transformers (local model)
- ML: scikit-learn (local models)

No external API calls required.

## Security

- Token-based authentication (configurable)
- Signed feedback bundles (RSA-4096)
- Artifact storage with hash verification
- Provenance tracking for audit

## Testing

Unit tests should be added to `tests/` directory:
- OCR extraction tests
- Vision detection tests
- Playbook matching tests
- Feedback collection tests

## Status

✅ **Phase 15 Complete**

All components implemented:
- Multi-modal ingestion pipeline
- Intelligent playbook routing
- Feedback collection and export
- SHAP explainability
- CLI tools
- Metrics export
- Systemd service

## Next Steps

- Phase 16: Deception Framework
- Integration testing with other phases
- Model training on production feedback data

