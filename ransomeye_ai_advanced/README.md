# Phase 17: AI Multi-Agent Governor

**Path:** `/home/ransomeye/rebuild/ransomeye_ai_advanced/`

**Version:** 1.0.0

**Author:** nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU

## Overview

Phase 17 implements the Advanced AI Assistant Engine with multi-agent orchestration, LLM governance, and safety controls. This phase extends Phase 7/15 with:

- **Multi-Agent Architecture**: Specialized agents (Planner, Retriever, Reasoner, Verifier, Summarizer) communicating via message bus
- **LLM Governor**: Rate limiting, policy enforcement, and hallucination detection
- **Training Infrastructure**: Trainable validator and reranker models with incremental learning
- **Regression Testing**: Golden Master pattern for deterministic testing
- **Storage**: PostgreSQL integration for conversations and summaries
- **Metrics**: Prometheus metrics for monitoring

## Architecture

### Multi-Agent System

```
User Query
    ↓
Orchestrator
    ↓
Planner Agent → Task Plan
    ↓
Retriever Agent → Context
    ↓
Reasoner Agent → Chain-of-Thought
    ↓
Verifier Agent → Validation
    ↓
Summarizer Agent → Final Answer
```

### Governor Pipeline

```
Request → Rate Limiter → Policy Engine → LLM → Validator → Response
```

## Components

### Multi-Agent Core (`multi_agent/`)

- **orchestrator.py**: Coordinates agent execution
- **message_bus.py**: AsyncIO-based message bus for agent communication
- **agents/base_agent.py**: Abstract base class for agents
- **agents/planner_agent.py**: Breaks queries into sub-tasks
- **agents/retriever_agent.py**: Retrieves context from knowledge base
- **agents/reasoner_agent.py**: Performs chain-of-thought reasoning
- **agents/verifier_agent.py**: Validates answers against context
- **agents/summarizer_agent.py**: Formats final responses

### Governor (`governor/`)

- **llm_governor.py**: Main governor entry point
- **rate_limiter.py**: Token bucket rate limiting
- **policy_engine.py**: Safety policy enforcement
- **validator.py**: Hallucination detection

### Models & Training (`models/`)

- **trainer/train_validator.py**: Train hallucination validator
- **trainer/train_reranker.py**: Train context reranker
- **trainer/incremental_trainer.py**: Autolearn loop
- **model_registry.py**: Model versioning
- **shap_support.py**: SHAP explainability

### Regression Testing (`regression/`)

- **regression_harness.py**: Golden Master test engine
- **golden_manager.py**: Manages reference data

### Storage (`storage/`)

- **conversation_store.py**: Stores agent traces to PostgreSQL
- **summary_store.py**: Stores answers and SHAP explanations

### API (`api/`)

- **advanced_api.py**: FastAPI endpoints (`POST /agent/chat`)
- **auth_middleware.py**: mTLS enforcement

### Tools (`tools/`)

- **sign_artifact.py**: Sign artifacts with cryptographic hashes
- **verify_artifact.py**: Verify artifact signatures
- **bench_pipeline.py**: Performance benchmarking

### Metrics (`metrics/`)

- **exporter.py**: Prometheus metrics exporter

## Environment Variables

```bash
# API Configuration
ASSISTANT_API_PORT=8008
AI_METRICS_PORT=9100

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ransomeye
DB_USER=gagan
DB_PASS=gagan

# LLM Configuration
LLM_MODEL_PATH=/path/to/model.gguf
MODEL_VERSION=1.0.0

# Rate Limiting
AI_QPS_LIMIT=10.0

# Model Paths
VALIDATOR_MODEL_PATH=/path/to/validator.pkl
RERANKER_MODEL_PATH=/path/to/reranker.pkl

# Policy
AI_POLICY_PATH=/path/to/policy.json

# Authentication
API_TOKEN=ransomeye-secure-token
```

## Usage

### Start API Server

```bash
cd /home/ransomeye/rebuild/ransomeye_ai_advanced
python -m api.advanced_api
```

### Train Validator Model

```bash
python -m models.trainer.train_validator \
    --data data/validator_training.json \
    --output models/validator_model.pkl
```

### Run Regression Tests

```bash
python -m regression.regression_harness \
    --create-golden  # First time
python -m regression.regression_harness  # Subsequent runs
```

### Benchmark Pipeline

```bash
python -m tools.bench_pipeline \
    --queries-file queries.txt \
    --iterations 10 \
    --output logs/benchmark.json
```

## API Endpoints

### POST /agent/chat

Process a chat query through the multi-agent pipeline.

**Request:**
```json
{
  "query": "What is the status of the security system?",
  "conversation_id": "optional-id",
  "user_id": "optional-user-id",
  "include_shap": true
}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "query": "What is the status of the security system?",
  "answer": "Based on the available information...",
  "verification": {
    "is_valid": true,
    "confidence": 0.95
  },
  "metadata": {...}
}
```

## Testing

All components include unit tests and integration tests. Run:

```bash
pytest tests/
```

## Integration

Phase 17 integrates with:
- **Phase 5/14**: LLM Runner for inference
- **Phase 7/15**: Retriever for context retrieval
- **Phase 10**: DB Core for storage
- **Phase 20**: Global Validator for end-to-end validation

## Compliance

✅ All files include required headers
✅ No hardcoded values (uses environment variables)
✅ PostgreSQL integration
✅ SHAP explainability support
✅ Multi-format export capability
✅ Offline-ready (no external API dependencies)
✅ Restart-safe design

## Next Steps

After Phase 17 is validated, proceed to **Phase 18: Threat Intel Feed Engine**.

