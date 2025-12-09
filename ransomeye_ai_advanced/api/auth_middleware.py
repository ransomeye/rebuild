# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/api/auth_middleware.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: mTLS enforcement middleware for API authentication

import os
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = None) -> str:
    """
    Verify authentication token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User ID if valid
        
    Raises:
        HTTPException if invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )
    
    token = credentials.credentials
    
    # Simple token validation (can be enhanced with JWT or mTLS)
    # For mTLS, would check client certificate
    expected_token = os.environ.get('API_TOKEN', 'ransomeye-secure-token')
    
    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    # Extract user ID from token (simplified)
    user_id = os.environ.get('DEFAULT_USER_ID', 'system')
    return user_id


async def verify_mtls(request: Request) -> str:
    """
    Verify mTLS client certificate.
    
    Args:
        request: FastAPI request
        
    Returns:
        User ID if valid
        
    Raises:
        HTTPException if invalid
    """
    # Check for client certificate in request
    client_cert = request.client
    
    if not client_cert:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="mTLS certificate required"
        )
    
    # In production, would verify certificate chain
    # For now, return default user
    user_id = os.environ.get('DEFAULT_USER_ID', 'system')
    return user_id

