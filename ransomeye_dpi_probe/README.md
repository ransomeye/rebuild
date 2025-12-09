# RansomEye DPI Probe (Phase 23)

High-performance Deep Packet Inspection probe with ML-based flow classification, privacy filtering, and secure upload capabilities.

## Features

- **High-Performance Capture**: Uses Scapy with raw sockets for efficient packet capture
- **Flow Classification**: ML-based detection of C2 beaconing, data exfiltration, and other threats
- **SHAP Explainability**: Every classification includes SHAP explanation
- **Privacy First**: Automatic PII redaction (credit cards, SSNs, emails, etc.)
- **Signed Uploads**: Cryptographic receipt verification for chain-of-custody
- **Autolearn**: Incremental model training with feedback
- **Resumable Uploads**: Automatic retry and resume for failed uploads
- **Prometheus Metrics**: Comprehensive metrics export

## Architecture

```
ransomeye_dpi_probe/
├── engine/           # Capture daemon, flow manager, PCAP writer, privacy filter
├── ml/               # Asset classifier, training, SHAP support
├── transport/        # mTLS client, uploader, receipt store
├── storage/          # Buffer management, manifest builder
├── tools/            # Traffic generator, update bundle builder
├── admin/            # Installation scripts
├── api/              # Admin API (localhost only)
├── metrics/          # Prometheus exporter
└── main.py           # Main orchestrator
```

## Installation

```bash
sudo ./admin/install_probe.sh
```

This will:
- Create `ransomeye-probe` user and group
- Set up directories and permissions
- Grant `CAP_NET_RAW` and `CAP_NET_ADMIN` capabilities
- Install systemd services

## Configuration

Copy `config/sample.env` and configure:

```bash
cp config/sample.env /etc/ransomeye-probe/.env
# Edit /etc/ransomeye-probe/.env
```

Key environment variables:
- `CAPTURE_IFACE`: Network interface to monitor
- `CORE_API_URL`: Core API endpoint
- `BUFFER_DIR`: Buffer directory for captured packets
- `MODEL_DIR`: Directory for ML models
- `PROBE_CERT_PATH`: mTLS client certificate
- `SERVER_PUBLIC_KEY_PATH`: Server public key for receipt verification

## Services

Three systemd services:

1. **ransomeye-probe.service**: Main capture daemon
2. **ransomeye-probe-admin.service**: Admin API (localhost:9080)
3. **ransomeye-probe-metrics.service**: Prometheus metrics (port 9092)

```bash
systemctl start ransomeye-probe
systemctl start ransomeye-probe-admin
systemctl start ransomeye-probe-metrics
```

## Admin API

Admin API runs on `127.0.0.1:9080` (localhost only):

- `GET /health`: Health check
- `GET /stats`: Probe statistics
- `POST /capture/start`: Start capture daemon
- `POST /capture/stop`: Stop capture daemon
- `POST /upload/force`: Force upload of pending chunks

## Training

Train the flow classifier:

```bash
python -m ransomeye_dpi_probe.ml.train_classifier --synthetic --samples 1000 --model-dir /path/to/models
```

Or with real data:

```bash
python -m ransomeye_dpi_probe.ml.train_classifier --data training_data.json --model-dir /path/to/models
```

## Testing

Generate synthetic traffic:

```bash
python -m ransomeye_dpi_probe.tools.traffic_generator --protocol tcp --duration 60
```

## Metrics

Prometheus metrics available on port 9092:

- `ransomeye_probe_packet_rate`: Packets per second
- `ransomeye_probe_drop_rate`: Dropped packets per second
- `ransomeye_probe_pii_redacted_bytes_total`: Total bytes redacted
- `ransomeye_probe_active_flows`: Active flow count
- `ransomeye_probe_upload_success_total`: Successful uploads
- `ransomeye_probe_upload_failures_total`: Upload failures

## Privacy Filtering

The privacy filter automatically redacts:
- Credit card numbers (with Luhn validation)
- Social Security Numbers
- Email addresses (in strict mode)
- Private IP addresses
- API keys and tokens
- Passwords

Configure via `PROBE_PRIVACY_REDACT` environment variable.

## Receipt Verification

All uploads are verified using cryptographic receipts from the server:
1. Upload chunk to Core API
2. Server returns signed receipt
3. Probe verifies signature using server's public key
4. Receipt stored locally for audit

## Requirements

See main project `requirements.txt`. Key dependencies:
- `scapy`: Packet capture
- `scikit-learn`: ML classification
- `shap`: Explainability
- `prometheus-client`: Metrics
- `cryptography`: Signatures
- `fastapi`: Admin API

## License

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

