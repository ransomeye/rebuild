# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/main.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main entry point for Global Validator API server

import os
import sys
from pathlib import Path
import uvicorn
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_global_validator.api.validator_api import app
from ransomeye_global_validator.metrics.exporter import start_metrics_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    # Start metrics server
    try:
        start_metrics_server()
    except Exception as e:
        logger.warning(f"Failed to start metrics server: {e}")
    
    # Start API server
    host = os.environ.get('VALIDATOR_API_HOST', '0.0.0.0')
    port = int(os.environ.get('VALIDATOR_API_PORT', 8100))
    
    logger.info(f"Starting RansomEye Global Validator API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

