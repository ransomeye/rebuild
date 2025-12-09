# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/api/auth_middleware.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Authentication middleware enforcing localhost origin check

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class LocalhostOnlyMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce localhost-only access."""
    
    async def dispatch(self, request: Request, call_next):
        """Check request origin and enforce localhost restriction."""
        client_host = request.client.host if request.client else None
        
        # Allow localhost and 127.0.0.1
        allowed_hosts = ['127.0.0.1', 'localhost', '::1']
        
        if client_host not in allowed_hosts:
            logger.warning(f"Rejected request from non-localhost: {client_host}")
            raise HTTPException(status_code=403, detail="Access denied: localhost only")
        
        response = await call_next(request)
        return response

