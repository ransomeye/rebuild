# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/api/policy_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI endpoints for viewing active policies and load status

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..loader.policy_loader import get_policy_loader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/policies", tags=["policies"])

# Get policy loader
policy_loader = get_policy_loader()

@router.get("/active")
async def get_active_policies():
    """
    Get information about currently active policies.
    
    Returns:
        Active policy information
    """
    try:
        policy_info = policy_loader.get_active_policy_info()
        return policy_info
    except Exception as e:
        logger.error(f"Error getting active policies: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/rules")
async def get_active_rules():
    """
    Get all active rules.
    
    Returns:
        List of active rules
    """
    try:
        rules = policy_loader.get_active_rules()
        return {
            "rules": rules,
            "count": len(rules)
        }
    except Exception as e:
        logger.error(f"Error getting active rules: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/status")
async def get_policy_status():
    """
    Get policy loading status.
    
    Returns:
        Policy status information
    """
    try:
        status = policy_loader.get_status()
        return status
    except Exception as e:
        logger.error(f"Error getting policy status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

