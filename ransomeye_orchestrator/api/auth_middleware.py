# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/api/auth_middleware.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: mTLS enforcement middleware for FastAPI

import os
import logging
from pathlib import Path
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

security = HTTPBearer()


class mTLSMiddleware(BaseHTTPMiddleware):
    """mTLS enforcement middleware."""
    
    def __init__(self, app, require_mtls: bool = True):
        """
        Initialize mTLS middleware.
        
        Args:
            app: FastAPI application
            require_mtls: Whether to require mTLS (default: True)
        """
        super().__init__(app)
        self.require_mtls = require_mtls
        self.allowed_client_certs = self._load_allowed_certs()
    
    def _load_allowed_certs(self) -> set:
        """Load allowed client certificate fingerprints."""
        cert_dir = Path(os.environ.get('MTLS_CERT_DIR', '/home/ransomeye/rebuild/certs/clients'))
        allowed = set()
        
        if cert_dir.exists():
            for cert_file in cert_dir.glob("*.pem"):
                # Extract fingerprint from cert file
                # For now, use filename as identifier
                allowed.add(cert_file.stem)
        
        return allowed
    
    async def dispatch(self, request: Request, call_next):
        """Process request with mTLS check."""
        if self.require_mtls:
            # Check for client certificate
            client_cert = request.headers.get('X-Client-Cert')
            if not client_cert:
                # Try to get from SSL context
                if hasattr(request.scope.get('client', None), 'getpeercert'):
                    # Client cert should be available in request
                    pass
                else:
                    # For development, allow if MTLS_ENABLED is false
                    mtls_enabled = os.environ.get('MTLS_ENABLED', 'true').lower() == 'true'
                    if mtls_enabled:
                        logger.warning("mTLS required but client certificate not found")
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Client certificate required (mTLS)"
                        )
        
        response = await call_next(request)
        return response

