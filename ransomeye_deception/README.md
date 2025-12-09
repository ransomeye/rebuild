# RansomEye Deception Framework (Phase 16)

AI-driven decoy deployment and rotation framework for threat detection.

## Features

- **AI-Driven Placement**: ML model predicts optimal decoy locations
- **Multiple Decoy Types**: File, Service, Process, and Host decoys
- **Atomic Rotation**: Safe rotation with Provision -> Verify -> Deprovision
- **Real-time Monitoring**: File access and service connection detection
- **Alert Integration**: Automatic alert generation on decoy interactions
- **Safe Simulator**: Automated testing with safety policies
- **SHAP Explainability**: ML placement decisions explained

## Architecture

```
ransomeye_deception/
├── dispatcher.py           # Main orchestrator
├── placement_engine.py     # AI placement logic
├── rotator.py              # Lifecycle management
├── deployers/              # Decoy deployers
│   ├── file_decoy.py
│   ├── service_decoy.py
│   ├── process_decoy.py
│   └── host_decoy.py
├── ml/                     # ML components
│   ├── placement_model.py
│   ├── train_placement.py
│   ├── incremental_trainer.py
│   └── shap_support.py
├── monitor/                # Monitoring
│   ├── decoy_monitor.py
│   └── alert_engine.py
├── simulator/              # Attacker simulator
│   ├── attacker_simulator.py
│   └── sim_policies/
├── storage/                # Storage layer
│   ├── config_store.py
│   └── artifact_store.py
├── api/                    # FastAPI endpoints
│   └── deception_api.py
├── tools/                  # Utilities
│   └── sign_action.py
└── metrics/                # Prometheus metrics
    └── exporter.py
```

## API Endpoints

- `POST /deploy` - Deploy a new decoy
- `POST /rotate` - Rotate decoy(s)
- `POST /simulate` - Run attacker simulation
- `GET /status` - Get deployment status
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Environment Variables

See `config/.env.example` for full configuration.

Key variables:
- `DECEPTION_PORT=8010` - API port
- `ROTATION_INTERVAL=60` - Rotation interval in minutes
- `DECEPTION_MODEL_PATH` - Path to placement model

## Systemd Service

Service file: `/home/ransomeye/rebuild/systemd/ransomeye-deception.service`

Enable with:
```bash
sudo systemctl enable ransomeye-deception.service
sudo systemctl start ransomeye-deception.service
```

## Testing

Run tests with:
```bash
cd /home/ransomeye/rebuild
python -m pytest ransomeye_deception/tests/ -v
```

