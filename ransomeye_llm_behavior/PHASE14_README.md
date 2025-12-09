# Phase 14: LLM Behavior Summarizer (Expanded) - Implementation Summary

## Overview

Phase 14 implements an advanced LLM behavior engine with:
- **Context Injection**: Hybrid retrieval (FAISS + BM25) with re-ranking
- **Security Filters**: Policy engine and PII sanitization
- **Deterministic Execution**: LLM runner with temperature=0 and fixed seed
- **Confidence Estimation**: Trainable model with SHAP explainability
- **Regression Testing**: Golden master harness for drift detection
- **Offline-First**: All processing happens locally

## Directory Structure

```
ransomeye_llm_behavior/
├── context/              # Context injection and retrieval
│   ├── context_injector.py
│   ├── retriever.py      # Hybrid FAISS + BM25
│   ├── chunker.py        # Deterministic chunking
│   └── embedder.py       # Local embeddings
├── security/             # Security filters
│   ├── policy_engine.py  # Blocked topics checker
│   ├── sanitizer.py      # PII redaction
│   └── security_filter.py # Orchestrator
├── llm_core/             # LLM execution
│   ├── llm_runner.py     # Deterministic LLM runner
│   ├── confidence_estimator.py # Trainable confidence model
│   ├── response_postproc.py # JSON normalization
│   └── prompt_templates/
│       └── standard_summary.tpl
├── training/             # Model training
│   ├── train_ranker.py
│   ├── train_confidence.py
│   └── incremental_trainer.py
├── regression/           # Regression testing
│   ├── regression_harness.py # Golden master testing
│   ├── golden_manager.py
│   └── prompt_snapshot.py
├── explain/              # Explainability
│   ├── shap_integration.py
│   └── explanation_store.py
├── storage/              # Persistence
│   ├── summary_store.py
│   └── cache.py          # Semantic caching
├── api/                  # FastAPI endpoints
│   └── summarizer_api.py # Port 8007
├── metrics/              # Prometheus metrics
│   └── exporter.py      # Port 9098
└── tools/                # Utilities
    ├── sign_summary.py
    └── verify_signature.py
```

## Key Features

### 1. Context Injection (`context/`)
- **Hybrid Retrieval**: Combines vector (FAISS) and sparse (BM25) search
- **Re-Ranking**: Trainable re-ranker model
- **Deterministic Chunking**: Hash-stable text splitting
- **Local Embeddings**: sentence-transformers or ONNX models

### 2. Security Layer (`security/`)
- **Policy Engine**: Blocks inputs matching keywords/regex patterns
- **PII Sanitizer**: Redacts IPs, SSNs, API keys, emails, credit cards
- **Pre/Post Filtering**: Policy check before LLM, sanitization after

### 3. LLM Core (`llm_core/`)
- **Deterministic Mode**: temperature=0, fixed seed for reproducibility
- **Confidence Estimation**: Trainable regression model
- **Response Post-Processing**: JSON normalization and formatting

### 4. Training (`training/`)
- **Re-Ranker Training**: Trains on query-document pairs
- **Confidence Training**: Trains on prompt-output-confidence triplets
- **Autolearn**: Incremental updates from operator feedback

### 5. Regression Harness (`regression/`)
- **Golden Master**: Stores input + expected output with hashes
- **Drift Detection**: Compares actual vs. expected output hashes
- **Synthetic Test Cases**: Generates test data programmatically

### 6. Explainability (`explain/`)
- **SHAP Integration**: Generates SHAP values for confidence estimates
- **Explanation Store**: Persists SHAP JSONs for audit

## API Endpoints

- `POST /behavior/analyze` - Analyze behavior and generate summary
  - Input: `{ query, context?, deterministic? }`
  - Output: `{ summary_id, summary, confidence_score, security_filtered, shap_values }`
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Environment Variables

- `LLM_PORT` - API port (default: 8007)
- `LLM_METRICS_PORT` - Metrics port (default: 9098)
- `LLM_MODEL_PATH` - Path to GGUF model file
- `BLOCKED_TOPICS_FILE` - Path to blocked topics JSON
- `MODEL_DIR` - Directory for trained models
- `GOLDEN_DIR` - Directory for golden artifacts
- `FEEDBACK_DIR` - Directory for feedback data

## Dependencies

Required packages:
- `sentence-transformers` or ONNX runtime - Embeddings
- `faiss-cpu` - Vector search
- `rank-bm25` - Sparse search
- `llama-cpp-python` - LLM inference
- `scikit-learn` - ML models
- `shap` - Explainability
- `prometheus-client` - Metrics
- `cryptography` - Signing

## Testing

### Regression Testing
```python
from ransomeye_llm_behavior.regression import RegressionHarness

harness = RegressionHarness()
results = harness.run_regression_suite(
    llm_runner=llm_runner,
    context_injector=context_injector,
    num_tests=10,
    create_goldens=False  # Set True to create new goldens
)
```

### Deterministic Execution
```python
llm_result = llm_runner.generate(
    prompt=prompt,
    deterministic=True,  # temperature=0, seed=42
    max_tokens=512
)
```

## Production Notes

1. **Determinism**: Set `deterministic=True` for reproducible outputs
2. **Security**: All outputs are sanitized before leaving the system
3. **Golden Master**: Run regression suite regularly to detect drift
4. **Training**: Train models on labeled data before deployment
5. **Offline**: All processing happens locally - no external API calls

## Integration Points

- **DB Core**: Summaries can be stored in database
- **Alert Engine**: Low confidence scores can trigger alerts
- **KillChain**: Behavioral summaries contribute to attack timelines
- **Forensic Engine**: Uses forensic data as context

## Next Steps

Phase 14 is complete. Ready for:
- Phase 15: SOC Copilot (Advanced) - Multi-modal capabilities
- Integration with other phases
- Production deployment and model training

