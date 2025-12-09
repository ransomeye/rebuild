# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/api/probe_admin_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI admin API server on localhost:9080 for configuration and status

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_dpi_probe.engine.capture_daemon import CaptureDaemon
from ransomeye_dpi_probe.transport.uploader import ChunkUploader
from ransomeye_dpi_probe.transport.signed_receipt_store import SignedReceiptStore
from ransomeye_dpi_probe.api.auth_middleware import LocalhostOnlyMiddleware


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RansomEye DPI Probe Admin API", version="1.0.0")

# Apply localhost-only middleware
app.add_middleware(LocalhostOnlyMiddleware)

# Global daemon instance (will be initialized in startup)
capture_daemon: Optional[CaptureDaemon] = None
uploader: Optional[ChunkUploader] = None


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global capture_daemon, uploader
    
    try:
        # Initialize receipt store
        receipt_store = SignedReceiptStore(
            store_dir=os.environ.get('RECEIPT_STORE_DIR', '/var/lib/ransomeye-probe/receipts'),
            server_public_key_path=os.environ.get('SERVER_PUBLIC_KEY_PATH', '/etc/ransomeye-probe/certs/server.pub')
        )
        
        # Initialize uploader
        buffer_dir = os.environ.get('BUFFER_DIR', '/var/lib/ransomeye-probe/buffer')
        uploader = ChunkUploader(buffer_dir, receipt_store)
        
        # Initialize capture daemon
        capture_daemon = CaptureDaemon()
        
        logger.info("Admin API initialized")
    except Exception as e:
        logger.error(f"Error during startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global capture_daemon, uploader
    
    if capture_daemon:
        capture_daemon.stop()
    if uploader:
        uploader.stop()
    
    logger.info("Admin API shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "daemon_running": capture_daemon.running if capture_daemon else False,
        "uploader_running": uploader.running if uploader else False
    }


@app.get("/stats")
async def get_stats():
    """Get probe statistics."""
    if not capture_daemon:
        raise HTTPException(status_code=503, detail="Capture daemon not initialized")
    
    daemon_stats = capture_daemon.get_stats()
    uploader_stats = uploader.get_stats() if uploader else {}
    
    return {
        "capture": daemon_stats,
        "upload": uploader_stats
    }


class UploadRequest(BaseModel):
    """Upload request model."""
    force: bool = False


@app.post("/upload/force")
async def force_upload(request: UploadRequest):
    """Force upload of pending chunks."""
    if not uploader:
        raise HTTPException(status_code=503, detail="Uploader not initialized")
    
    try:
        uploader.upload_pending()
        return {
            "status": "success",
            "message": "Upload triggered",
            "stats": uploader.get_stats()
        }
    except Exception as e:
        logger.error(f"Error forcing upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/capture/start")
async def start_capture():
    """Start capture daemon."""
    if not capture_daemon:
        raise HTTPException(status_code=503, detail="Capture daemon not initialized")
    
    if capture_daemon.running:
        return {"status": "already_running", "message": "Capture daemon already running"}
    
    try:
        capture_daemon.start()
        return {"status": "started", "message": "Capture daemon started"}
    except Exception as e:
        logger.error(f"Error starting capture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/capture/stop")
async def stop_capture():
    """Stop capture daemon."""
    if not capture_daemon:
        raise HTTPException(status_code=503, detail="Capture daemon not initialized")
    
    if not capture_daemon.running:
        return {"status": "not_running", "message": "Capture daemon not running"}
    
    try:
        capture_daemon.stop()
        return {"status": "stopped", "message": "Capture daemon stopped"}
    except Exception as e:
        logger.error(f"Error stopping capture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/uploader/start")
async def start_uploader():
    """Start uploader."""
    if not uploader:
        raise HTTPException(status_code=503, detail="Uploader not initialized")
    
    if uploader.running:
        return {"status": "already_running", "message": "Uploader already running"}
    
    try:
        uploader.start()
        return {"status": "started", "message": "Uploader started"}
    except Exception as e:
        logger.error(f"Error starting uploader: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/uploader/stop")
async def stop_uploader():
    """Stop uploader."""
    if not uploader:
        raise HTTPException(status_code=503, detail="Uploader not initialized")
    
    if not uploader.running:
        return {"status": "not_running", "message": "Uploader not running"}
    
    try:
        uploader.stop()
        return {"status": "stopped", "message": "Uploader stopped"}
    except Exception as e:
        logger.error(f"Error stopping uploader: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Main entry point."""
    admin_port = int(os.environ.get('PROBE_ADMIN_PORT', '9080'))
    admin_host = os.environ.get('PROBE_ADMIN_HOST', '127.0.0.1')
    
    logger.info(f"Starting Admin API on {admin_host}:{admin_port}")
    
    uvicorn.run(
        app,
        host=admin_host,
        port=admin_port,
        log_level="info"
    )


if __name__ == '__main__':
    main()

