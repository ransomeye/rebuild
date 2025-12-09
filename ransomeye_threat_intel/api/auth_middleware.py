# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/api/auth_middleware.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: mTLS/Token check for API authentication

import os
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = None) -> str:
    """Verify authentication token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )
    
    token = credentials.credentials
    expected_token = os.environ.get('TI_API_TOKEN', 'ransomeye-secure-token')
    
    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return os.environ.get('DEFAULT_USER_ID', 'system')

