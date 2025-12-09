# Training the Deception Framework Placement Model

## Quick Start

To train the model with research-based security data:

```bash
cd /home/ransomeye/rebuild/ransomeye_deception/ml
python3 train_model_now.py
```

## Requirements

- Python 3.7+
- numpy
- scikit-learn

Install dependencies:
```bash
pip install numpy scikit-learn
```

## Training Data

The training script (`train_model_now.py`) generates realistic training data based on:

1. **Honeypot Effectiveness Studies** (Spitzner 2003, Provos 2004)
   - High-value assets attract 3x more interactions
   - Common ports (SSH, HTTP, RDP) get 4x more hits
   - Dense deployments reduce effectiveness by 40%

2. **Network Deception Research** (Al-Shaer 2019)
   - DMZ segments see 60% more attacks
   - Critical segments require strategic placement
   - Isolation vs. visibility trade-offs

3. **Threat Intelligence Patterns** (MITRE ATT&CK)
   - Lateral movement patterns
   - Privilege escalation paths
   - Attack surface preferences

## Training Process

The script generates 10,000 training samples across 6 research-based scenarios:
- High-criticality service decoys (75-92% hit rate)
- Common port services (65-80% hit rate)
- Critical file decoys (70-85% hit rate)
- Dense honeynets (25-40% hit rate - reduced effectiveness)
- Isolated decoys (35-50% hit rate)
- Medium-value mixed deployments (45-65% hit rate)

## Output

After training, you'll get:
- `placement_model.pkl` - Trained model file
- `placement_model.metadata.json` - Training metadata
- `training_data/training_data.json` - Full training dataset

## Model Performance

Expected metrics:
- Training R² Score: > 0.85
- Feature importance highlights host_criticality and existing_density as top factors

## Advanced Training

For training with additional datasets, see:
- `train_with_real_data.py` - Downloads and processes external security datasets
- `train_placement.py` - Trains from historical deployment data in database

