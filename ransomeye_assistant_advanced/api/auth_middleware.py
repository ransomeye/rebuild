# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/api/auth_middleware.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Authentication middleware for mTLS and token-based auth

import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify authentication token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Token string if valid
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    
    # Get expected token from environment
    expected_token = os.environ.get('ASSISTANT_API_TOKEN', None)
    
    # If no token configured, allow all (development mode)
    if expected_token is None:
        logger.warning("No ASSISTANT_API_TOKEN configured - allowing all requests (development mode)")
        return token
    
    # Verify token
    if token != expected_token:
        logger.warning(f"Invalid token attempt: {token[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    
    return token

def verify_mtls():
    """
    Verify mTLS certificate (future implementation).
    
    Returns:
        Certificate subject if valid
        
    Raises:
        HTTPException: If certificate is invalid
    """
    # Note: mTLS verification requires client certificate in request context
    # This would be implemented using FastAPI's Request object to access
    # SSL client certificate from the connection
    raise HTTPException(
        status_code=501,
        detail="mTLS authentication not yet implemented"
    )

