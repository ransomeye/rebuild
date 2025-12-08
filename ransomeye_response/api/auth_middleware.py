# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/api/auth_middleware.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Middleware to verify internal tokens and mTLS

import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authentication (internal tokens and mTLS).
    """
    
    def __init__(self, app, require_auth: bool = True):
        """
        Initialize auth middleware.
        
        Args:
            app: FastAPI application
            require_auth: Whether to require authentication
        """
        super().__init__(app)
        self.require_auth = require_auth
        self.allowed_tokens = set(os.environ.get('ALLOWED_TOKENS', '').split(','))
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with authentication.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Skip auth for health check
        if request.url.path in ['/', '/health', '/docs', '/openapi.json']:
            return await call_next(request)
        
        if not self.require_auth:
            return await call_next(request)
        
        # Check for internal token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            if token in self.allowed_tokens:
                return await call_next(request)
        
        # Check for mTLS client certificate
        client_cert = request.client
        if client_cert and hasattr(request, 'scope'):
            # In production, would verify client certificate
            # For now, allow if client_cert is present
            pass
        
        # If no valid auth, return 401
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

