# RansomEye Linux Agent (Phase 21)

## Overview

The RansomEye Linux Agent is a standalone background service that collects telemetry, performs local threat detection using ML models, and securely uploads data to the Core platform using mTLS.

## Features

- **Persistent Background Service**: Runs as systemd service under `ransomeye` user
- **Telemetry Collection**: Process, network, and file system monitoring using `psutil` and `/proc`
- **Local ML Detection**: Real-time threat detection with SHAP explainability
- **Offline Buffering**: Atomic writes to buffer directory when Core is unreachable
- **Secure Updates**: Signed update bundles with automatic rollback on failure
- **mTLS Communication**: Mutual TLS authentication with Core API

## Architecture

```
ransomeye_linux_agent/
├── engine/              # Core agent logic
│   ├── agent_main.py    # Main entrypoint with signal handling
│   ├── collector.py     # Telemetry collection
│   ├── detector.py      # Threat detection (rules + ML)
│   └── persistence.py   # Atomic file writes
├── transport/           # Communication with Core
│   ├── agent_client.py  # mTLS client
│   ├── heartbeat.py     # Periodic heartbeat
│   └── uploader.py      # Buffer upload worker
├── updater/             # Update management
│   ├── apply_update.sh  # Atomic update with rollback
│   ├── verifier.sh      # Signature verification
│   └── build_update_bundle.py  # Update packaging
├── models/              # ML models
│   ├── inferencer.py    # Model inference wrapper
│   ├── model_registry.py # Model version management
│   ├── shap_support.py  # SHAP explainability
│   └── train/           # Training scripts
├── security/            # Security utilities
│   ├── key_manager.py   # Key permission checks
│   └── config_validator.py  # Configuration validation
├── cli/                 # Command-line tools
│   ├── agent_ctl.py     # Admin CLI
│   └── inspect_buffer.py  # Buffer inspection
└── tools/               # Utilities
    └── self_test.sh     # Post-update self-test
```

## Installation

### Prerequisites

- Python 3.8+
- systemd
- Root access for installation

### Quick Install

```bash
sudo ./install.sh
```

The installer will:
1. Create `ransomeye` user and group
2. Copy files to `/opt/ransomeye-agent`
3. Create configuration directories
4. Set up systemd service
5. Create CLI symlinks

### Post-Installation Configuration

1. **Configure Certificates**:
   ```bash
   # Place certificates in:
   /etc/ransomeye-agent/certs/agent.crt
   /etc/ransomeye-agent/certs/agent.key
   /etc/ransomeye-agent/certs/ca.crt
   
   # Set permissions:
   chmod 600 /etc/ransomeye-agent/certs/*.key
   ```

2. **Configure Update Key**:
   ```bash
   # Place public key in:
   /etc/ransomeye-agent/keys/update_key.pub
   ```

3. **Edit Environment**:
   ```bash
   # Edit configuration:
   sudo nano /etc/ransomeye-agent/agent.env
   
   # Update CORE_API_URL and other settings
   ```

4. **Start Service**:
   ```bash
   sudo systemctl start ransomeye-agent
   sudo systemctl status ransomeye-agent
   ```

## Environment Variables

### Required
- `CORE_API_URL`: Core API endpoint URL

### Optional
- `AGENT_CERT_PATH`: Agent certificate path (default: `/etc/ransomeye-agent/certs/agent.crt`)
- `AGENT_KEY_PATH`: Agent private key path (default: `/etc/ransomeye-agent/certs/agent.key`)
- `CA_CERT_PATH`: CA certificate path (default: `/etc/ransomeye-agent/certs/ca.crt`)
- `AGENT_UPDATE_KEY_PATH`: Update public key path (default: `/etc/ransomeye-agent/keys/update_key.pub`)
- `BUFFER_DIR`: Buffer directory (default: `/var/lib/ransomeye-agent/buffer`)
- `MODEL_PATH`: ML model path (default: `/opt/ransomeye-agent/models/detector_model.pkl`)
- `DETECTION_THRESHOLD`: ML detection threshold (default: `0.7`)
- `HEARTBEAT_INTERVAL`: Heartbeat interval in seconds (default: `60`)
- `COLLECTION_INTERVAL`: Telemetry collection interval in seconds (default: `5.0`)
- `UPLOAD_BATCH_SIZE`: Number of events to upload per batch (default: `10`)
- `MONITOR_DIRS`: Comma-separated directories to monitor (default: `/tmp,/var/tmp,/home`)
- `AGENT_METRICS_PORT`: Metrics port (default: `9110`)

## Usage

### Service Management

```bash
# Start service
sudo systemctl start ransomeye-agent

# Stop service
sudo systemctl stop ransomeye-agent

# Restart service
sudo systemctl restart ransomeye-agent

# Check status
sudo systemctl status ransomeye-agent
```

### CLI Tools

```bash
# Check agent status
ransomeye-agent-ctl status

# Show buffer statistics
ransomeye-agent-ctl stats

# Show logs
ransomeye-agent-ctl logs -n 100

# Flush buffer
ransomeye-agent-ctl flush

# Inspect buffer files
ransomeye-agent-inspect --list
ransomeye-agent-inspect <filename>
```

## Updates

### Building Update Bundle

```bash
python3 updater/build_update_bundle.py <source_dir> <output.tar.gz> [private_key.pem]
```

### Applying Updates

```bash
sudo /opt/ransomeye-agent/updater/apply_update.sh <update_bundle.tar.gz>
```

The update script will:
1. Verify signature
2. Stop service
3. Create backup
4. Extract new files
5. Start service
6. Run self-test
7. Rollback on failure

## Model Training

```bash
# Train detection model
python3 models/train/train_detector.py [output_path]
```

## Security

- **Key Permissions**: All key files must have `0600` permissions (owner read/write only)
- **User Isolation**: Agent runs as non-root user `ransomeye`
- **mTLS**: All communication with Core uses mutual TLS authentication
- **Signed Updates**: Updates must be signed with operator's private key
- **Atomic Writes**: Buffer writes use atomic file operations

## Troubleshooting

### Service Not Starting

1. Check logs: `journalctl -u ransomeye-agent -n 50`
2. Verify configuration: `ransomeye-agent-ctl status`
3. Check certificates: Ensure certificates exist and have correct permissions
4. Validate config: Check `/etc/ransomeye-agent/agent.env`

### Buffer Not Uploading

1. Check Core connectivity: Verify `CORE_API_URL` is reachable
2. Check buffer: `ransomeye-agent-inspect --list`
3. Check uploader logs: `journalctl -u ransomeye-agent | grep uploader`

### Detection Issues

1. Check model: Verify model file exists at `MODEL_PATH`
2. Check threshold: Adjust `DETECTION_THRESHOLD` if needed
3. Review detection logs: `journalctl -u ransomeye-agent | grep detector`

## Development

### Running Locally

```bash
# Set environment variables
export CORE_API_URL=https://localhost:8443
export BUFFER_DIR=/tmp/ransomeye-buffer

# Run agent
python3 engine/agent_main.py
```

## Notes

- Agent requires root only for installation
- All runtime operations run as `ransomeye` user
- Buffer directory must be writable by agent user
- Model file is optional (default model used if not found)
- SHAP explainability requires `shap` package (optional)

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

