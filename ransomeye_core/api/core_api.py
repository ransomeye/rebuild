# Path and File Name : /home/ransomeye/rebuild/ransomeye_core/api/core_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI-based Core API server with health endpoint and basic orchestration

import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / "config" / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RansomEye Core API",
    description="Core Engine API for RansomEye Platform",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Core API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "ransomeye-core",
            "version": "1.0.0"
        }
        
        # Check database connectivity if configured
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'ransomeye')
        
        try:
            from sqlalchemy import create_engine, text
            db_user = os.environ.get('DB_USER', 'gagan')
            db_pass = os.environ.get('DB_PASS', 'gagan')
            connection_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
            engine = create_engine(connection_string, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health_status["database"] = "connected"
            engine.dispose()
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            health_status["database"] = "disconnected"
            health_status["status"] = "degraded"
        
        return JSONResponse(content=health_status)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/status")
async def api_status():
    """API status endpoint."""
    return {
        "api_version": "v1",
        "endpoints": {
            "health": "/health",
            "status": "/api/v1/status",
            "root": "/"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('CORE_API_HOST', '0.0.0.0')
    port = int(os.environ.get('CORE_API_PORT', 8080))
    
    # TLS configuration
    tls_enabled = os.environ.get('TLS_ENABLED', 'false').lower() == 'true'
    cert_path = os.environ.get('TLS_CERT_PATH', '')
    key_path = os.environ.get('TLS_KEY_PATH', '')
    
    if tls_enabled and cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_keyfile=key_path,
            ssl_certfile=cert_path
        )
    else:
        uvicorn.run(app, host=host, port=port)

