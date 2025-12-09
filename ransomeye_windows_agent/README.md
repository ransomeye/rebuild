# RansomEye Windows Agent (Phase 22)

## Overview

The RansomEye Windows Agent is a standalone background service that collects telemetry using ETW (Event Tracing for Windows), performs local threat detection using ML models, and securely uploads data to the Core platform using mTLS.

## Features

- **Windows Service Integration**: Runs as Windows Service using pywin32 ServiceFramework
- **ETW Telemetry Collection**: High-fidelity, low-overhead monitoring via ETW with EventLog fallback
- **Local ML Detection**: Real-time threat detection with SHAP explainability
- **Offline Buffering**: Atomic writes to buffer directory when Core is unreachable (Windows-safe using os.replace)
- **Secure Updates**: Signed update bundles with automatic rollback on failure
- **mTLS Communication**: Mutual TLS authentication with Core API
- **MSI Installer**: Professional MSI installer using WiX Toolset

## Architecture

```
ransomeye_windows_agent/
├── engine/              # Core agent logic
│   ├── agent_main.py     # Main entrypoint with thread management
│   ├── collector_etw.py  # ETW/EventLog telemetry collection
│   ├── detector.py       # Threat detection (rules + ML)
│   └── persistence.py    # Atomic file writes (Windows-safe)
├── windows_service/      # Windows Service wrapper
│   └── ransomeye_agent_service.py  # ServiceFramework implementation
├── transport/           # Communication with Core
│   ├── agent_client.py  # mTLS client
│   ├── heartbeat.py     # Periodic heartbeat
│   └── uploader.py      # Buffer upload worker
├── updater/             # Update management
│   ├── apply_update.ps1      # Atomic update with rollback
│   ├── verify_update.ps1     # Signature verification
│   └── build_update_bundle.ps1  # Update packaging
├── installer/           # MSI installer
│   ├── build_installer.ps1  # WiX MSI builder
│   ├── install.bat      # Installation wrapper
│   └── uninstall.bat    # Uninstallation script
├── models/              # ML models
│   ├── inferencer.py    # Model inference wrapper
│   ├── model_registry.py # Model version management
│   └── shap_support.py  # SHAP explainability
├── security/            # Security utilities
│   ├── key_manager.py   # NTFS ACL checks
│   └── config_validator.py  # Configuration validation
└── cli/                 # Command-line tools
    ├── agent_ctl.ps1    # Admin CLI
    └── inspect_buffer.ps1  # Debug tool
```

## Installation

### Prerequisites

- Windows 10/11 or Windows Server 2016+
- Python 3.8+ (for development)
- WiX Toolset (for building MSI)
- Administrator privileges

### MSI Installation

1. Build the MSI installer:
```powershell
cd installer
.\build_installer.ps1 -Version "1.0.0"
```

2. Install using the generated MSI:
```powershell
.\install.bat
```

Or manually:
```cmd
msiexec /i RansomEyeAgent.msi /qn
```

### Manual Installation

1. Install Python dependencies:
```powershell
pip install -r requirements.txt
```

2. Install as Windows Service:
```powershell
python windows_service\ransomeye_agent_service.py install
```

3. Start the service:
```powershell
net start RansomEyeAgent
```

## Configuration

### Environment Variables

Set these system-wide or in the service environment:

- `CORE_API_URL`: Core API endpoint (default: `https://localhost:8443`)
- `AGENT_CERT_PATH`: Path to agent certificate (default: `%ProgramData%\RansomEye\certs\agent.crt`)
- `AGENT_KEY_PATH`: Path to agent private key (default: `%ProgramData%\RansomEye\certs\agent.key`)
- `CA_CERT_PATH`: Path to CA certificate (default: `%ProgramData%\RansomEye\certs\ca.crt`)
- `BUFFER_DIR`: Buffer directory for offline storage (default: `%ProgramData%\RansomEye\buffer`)
- `MODEL_PATH`: Path to ML model file (default: `%ProgramData%\RansomEye\models\detector_model.pkl`)
- `HEARTBEAT_INTERVAL_SEC`: Heartbeat interval in seconds (default: `60`)
- `UPLOAD_BATCH_SIZE`: Number of events to upload per batch (default: `10`)
- `AGENT_MAX_BUFFER_MB`: Maximum buffer size in MB (default: `1000`)
- `ENABLE_ETW`: Enable ETW collection (default: `true`)

## Usage

### Service Management

```powershell
# Check status
.\cli\agent_ctl.ps1 status

# Start service
.\cli\agent_ctl.ps1 start

# Stop service
.\cli\agent_ctl.ps1 stop

# Restart service
.\cli\agent_ctl.ps1 restart

# Check health
.\cli\agent_ctl.ps1 health

# View configuration
.\cli\agent_ctl.ps1 config

# Flush buffer
.\cli\agent_ctl.ps1 flush-buffer
```

### Inspect Buffer

```powershell
.\cli\inspect_buffer.ps1 -Limit 20
```

### Update Agent

1. Build update bundle:
```powershell
.\updater\build_update_bundle.ps1 -SourcePath ".\" -OutputPath ".\update.zip" -Version "1.0.1"
```

2. Apply update:
```powershell
.\updater\apply_update.ps1 -UpdateBundlePath ".\update.zip"
```

## Development

### Running in Console Mode

```powershell
python engine\agent_main.py
```

### Service Commands

```powershell
# Install service
python windows_service\ransomeye_agent_service.py install

# Start service
python windows_service\ransomeye_agent_service.py start

# Stop service
python windows_service\ransomeye_agent_service.py stop

# Remove service
python windows_service\ransomeye_agent_service.py remove
```

## Security

- **mTLS**: All communication with Core uses mutual TLS authentication
- **Signed Updates**: Updates must be signed with operator's private key
- **NTFS ACLs**: Key files are protected with proper NTFS permissions
- **PII Redaction**: Telemetry data is redacted before upload

## Troubleshooting

### Service Won't Start

1. Check event logs: `Get-EventLog -LogName Application -Source RansomEyeAgent`
2. Check service status: `Get-Service RansomEyeAgent`
3. Check configuration: `.\cli\agent_ctl.ps1 config`

### Buffer Not Uploading

1. Check Core API connectivity
2. Verify certificates are valid
3. Inspect buffer: `.\cli\inspect_buffer.ps1`
4. Check logs: `%ProgramData%\RansomEye\logs\agent_service.log`

### ETW Not Working

The agent automatically falls back to EventLog and psutil if ETW is unavailable. Check logs for fallback messages.

## License

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

