# RansomEye UI & Dashboards - Phase 11

**Unified UI Stack: React + Grafana**

## Overview

The RansomEye UI module provides:
- **React Application** (Port 3000): Offline-first React app with IndexedDB storage
- **Grafana** (Port 3001): Standalone Grafana instance with PostgreSQL datasource
- **Dashboard Tools**: Bundling and signing utilities

## Directory Structure

```
ransomeye_ui/
├── app/                    # React application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API and storage services
│   │   ├── contexts/       # React contexts
│   │   └── schema/         # JSON schemas
│   ├── public/             # Static assets
│   └── package.json        # Dependencies
├── grafana/                # Grafana installation
│   ├── bin/                # Grafana binaries
│   ├── config/             # Grafana configuration
│   ├── provisioning/       # Datasources and dashboards
│   └── install_grafana.sh # Installation script
└── tools/                  # Utility scripts
    ├── bundle_dashboard.py # Dashboard bundling
    └── sign_export.py      # Export signing
```

## Features

### React Application (Port 3000)

- **Offline-First**: Uses Dexie.js (IndexedDB) for local storage
- **Service Worker**: PWA support for offline functionality
- **Dashboard Editor**: Visual JSON editor with schema validation
- **Model Registry**: View and retrain AI models
- **Alerts View**: Filter and manage security alerts
- **Read-Only Mode**: Functions when backend is offline

### Grafana (Port 3001)

- **Standalone Installation**: Isolated Grafana instance
- **PostgreSQL Datasource**: Pre-configured connection to Phase 10 DB
- **Dashboard Provisioning**: Automatic dashboard loading
- **Port 3001**: Explicitly configured to avoid conflict with React UI

## Setup

### 1. Build React Application

```bash
cd /home/ransomeye/rebuild/ransomeye_ui/app
npm install
npm run build
```

### 2. Install Grafana

```bash
cd /home/ransomeye/rebuild/ransomeye_ui/grafana
./install_grafana.sh
```

### 3. Configure Environment

Ensure these environment variables are set in `.env`:

```bash
FRONTEND_PORT=3000
GRAFANA_PORT=3001
BACKEND_API_PORT=8080
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ransomeye
DB_USER=gagan
DB_PASS=gagan
UI_SIGN_KEY_PATH=/home/ransomeye/rebuild/certs/ui_sign_private.pem
```

### 4. Start Services

```bash
# Start React UI (port 3000)
systemctl start ransomeye-ui

# Start Grafana (port 3001)
systemctl start ransomeye-grafana
```

## Usage

### React UI

- **URL**: http://localhost:3000
- **Dashboard**: Main dashboard view
- **Alerts**: Security alerts management
- **Models**: AI model registry
- **Editor**: Dashboard JSON editor

### Grafana

- **URL**: http://localhost:3001
- **Login**: `gagan` / `gagan`
- **Datasource**: Pre-configured PostgreSQL connection

### Dashboard Bundling

```bash
# Bundle a dashboard
python3 tools/bundle_dashboard.py app/src/schema/dashboard.json -o exports/

# Bundle with signature
python3 tools/bundle_dashboard.py dashboard.json --sign
```

### Export Signing

```bash
# Sign a manifest
python3 tools/sign_export.py bundle/manifest.json
```

## Offline-First Architecture

The React app implements offline-first patterns:

1. **API Calls**: Try API first, fallback to IndexedDB on failure
2. **Data Sync**: Automatically sync API data to IndexedDB
3. **Read-Only Mode**: Full read access when offline
4. **Service Worker**: Caches static assets for offline use

## Port Configuration

**CRITICAL**: Port conflict resolution:

- **React UI**: Port 3000 (configured in `vite.config.ts` and systemd)
- **Grafana**: Port 3001 (configured in `grafana/config/custom.ini`)

Both services are explicitly configured to avoid conflicts.

## Development

### React Development Server

```bash
cd app
npm run dev
```

### Build for Production

```bash
cd app
npm run build
```

Output: `app/dist/`

## Dependencies

### React App

- `react`, `react-dom`: UI framework
- `vite`: Build tool
- `dexie`: IndexedDB wrapper
- `axios`: HTTP client
- `react-grid-layout`: Dashboard layout
- `ajv`: JSON schema validation

### Grafana

- Standalone binary (installed via `install_grafana.sh`)
- PostgreSQL datasource plugin

## Troubleshooting

### Port Conflicts

If port 3000 or 3001 is in use:

```bash
# Check port usage
sudo lsof -i :3000
sudo lsof -i :3001

# Kill process if needed
sudo kill -9 <PID>
```

### Grafana Not Starting

1. Check Grafana is installed: `ls grafana/bin/grafana-server`
2. Verify config: `cat grafana/config/custom.ini | grep http_port`
3. Check logs: `journalctl -u ransomeye-grafana -f`

### React App Not Loading

1. Verify build: `ls app/dist/`
2. Check service: `systemctl status ransomeye-ui`
3. Check logs: `journalctl -u ransomeye-ui -f`

### Offline Mode Issues

1. Check IndexedDB: Open browser DevTools → Application → IndexedDB
2. Verify service worker: DevTools → Application → Service Workers
3. Clear cache if needed: DevTools → Application → Clear Storage

## Security Notes

1. **Grafana Credentials**: Change default `gagan/gagan` in production
2. **Signing Key**: Store `UI_SIGN_KEY_PATH` securely
3. **CORS**: Configure CORS for API endpoints
4. **HTTPS**: Use HTTPS in production

## License

© RansomEye.Tech | Support: Gagan@RansomEye.Tech

