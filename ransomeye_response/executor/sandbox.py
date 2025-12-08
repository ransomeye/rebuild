# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/executor/sandbox.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Isolated environment for running local script steps

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SandboxRunner:
    """
    Runs local scripts in a sandboxed environment.
    """
    
    def __init__(self):
        """Initialize sandbox runner."""
        self.allowed_scripts_dir = Path(os.environ.get(
            'ALLOWED_SCRIPTS_DIR',
            '/home/ransomeye/rebuild/ransomeye_response/scripts'
        ))
        self.allowed_scripts_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self, target: Dict[str, Any], parameters: Dict[str, Any],
            context: Dict[str, Any]) -> str:
        """
        Run a script in sandbox.
        
        Args:
            target: Target specification
            parameters: Script parameters
            context: Execution context
            
        Returns:
            Script output
        """
        script_name = parameters.get('script')
        if not script_name:
            raise ValueError("Script name not provided in parameters")
        
        # Resolve script path (must be in allowed directory)
        script_path = self.allowed_scripts_dir / script_name
        
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Verify script is within allowed directory (prevent path traversal)
        try:
            script_path.resolve().relative_to(self.allowed_scripts_dir.resolve())
        except ValueError:
            raise SecurityError(f"Script path outside allowed directory: {script_path}")
        
        # Execute script in temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Set environment variables
                env = os.environ.copy()
                env['PLAYBOOK_CONTEXT'] = str(context)
                
                # Execute script
                result = subprocess.run(
                    ['/bin/bash', str(script_path)],
                    cwd=temp_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=parameters.get('timeout', 300)
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"Script failed: {result.stderr}")
                
                logger.info(f"Script executed successfully: {script_name}")
                return result.stdout
                
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"Script timeout: {script_name}")
            except Exception as e:
                logger.error(f"Script execution failed: {e}")
                raise

class SecurityError(Exception):
    """Security-related error."""
    pass

