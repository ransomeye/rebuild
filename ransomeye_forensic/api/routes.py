# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/api/routes.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Integration glue to add analysis routes to the main FastAPI app

"""
Routes integration module.

This module provides integration glue to add Phase 13 analysis routes
to the main FastAPI application in forensic_api.py.
"""

from .analysis_api import router as analysis_router

# Export router for inclusion in main app
__all__ = ['analysis_router']

