# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/deployers/process_decoy.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Spawns fake processes with enticing names (mocked on Linux as python processes)

import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessDecoy:
    """
    Process decoy deployer.
    Spawns fake processes with enticing names.
    """
    
    def __init__(self):
        """Initialize process decoy deployer."""
        self.active_processes = {}  # decoy_id -> {process, name, pid}
        
        # Process templates
        self.process_templates = {
            'backup_admin': 'python3 -c "import time; time.sleep(3600)"',
            'db_maintenance': 'python3 -c "import time; time.sleep(3600)"',
            'cron_job': 'python3 -c "import time; time.sleep(3600)"',
            'system_monitor': 'python3 -c "import time; time.sleep(3600)"',
            'backup_service': 'python3 -c "import time; time.sleep(3600)"'
        }
        
        logger.info("Process decoy deployer initialized")
    
    async def provision(self, decoy_id: str, location: str,
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Provision a process decoy.
        
        Args:
            decoy_id: Unique decoy ID
            location: Process name
            metadata: Optional metadata
            
        Returns:
            Provision result
        """
        try:
            process_name = location
            
            # Get command template
            if process_name in self.process_templates:
                cmd = self.process_templates[process_name]
            else:
                # Default template
                cmd = f'python3 -c "import time; time.sleep(3600)"'
            
            # Create process with custom name by using exec
            # We'll create a wrapper script that renames itself
            script_content = f"""#!/usr/bin/env python3
import sys
import time
# This process appears as the decoy name
sys.argv[0] = '{process_name}'
time.sleep(3600)
"""
            
            # Write temporary script
            script_path = Path(f"/tmp/{decoy_id}_{process_name}.py")
            script_path.write_text(script_content)
            script_path.chmod(0o755)
            
            # Start process
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Store process info
            self.active_processes[decoy_id] = {
                'process': process,
                'name': process_name,
                'pid': process.pid,
                'script_path': str(script_path)
            }
            
            # Wait a bit to ensure process started
            time.sleep(0.5)
            
            # Verify process is running
            if process.poll() is not None:
                raise RuntimeError(f"Process {process_name} exited immediately")
            
            logger.info(f"Process decoy provisioned: {process_name} (PID: {process.pid})")
            
            return {
                'decoy_id': decoy_id,
                'type': 'process',
                'name': process_name,
                'pid': process.pid
            }
            
        except Exception as e:
            logger.error(f"Error provisioning process decoy: {e}")
            # Cleanup on error
            if decoy_id in self.active_processes:
                await self.deprovision(decoy_id, {})
            raise
    
    async def verify(self, decoy_id: str, provision_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify process decoy is active.
        
        Args:
            decoy_id: Decoy ID
            provision_result: Provision result
            
        Returns:
            Verification result
        """
        try:
            if decoy_id not in self.active_processes:
                return {
                    'verified': False,
                    'error': 'Decoy not found in active processes'
                }
            
            process_info = self.active_processes[decoy_id]
            process = process_info['process']
            
            # Check if process is still running
            if process.poll() is not None:
                return {
                    'verified': False,
                    'error': f"Process exited with code {process.poll()}"
                }
            
            # Verify PID exists
            try:
                os.kill(process.pid, 0)  # Signal 0 checks if process exists
            except ProcessLookupError:
                return {
                    'verified': False,
                    'error': 'Process PID does not exist'
                }
            
            return {
                'verified': True,
                'name': process_info['name'],
                'pid': process.pid
            }
            
        except Exception as e:
            return {
                'verified': False,
                'error': str(e)
            }
    
    async def deprovision(self, decoy_id: str, provision_result: Dict[str, Any]):
        """
        Deprovision process decoy.
        
        Args:
            decoy_id: Decoy ID
            provision_result: Provision result
        """
        try:
            if decoy_id not in self.active_processes:
                return
            
            process_info = self.active_processes[decoy_id]
            process = process_info['process']
            
            # Kill process group
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                # Wait a bit
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass  # Already dead
            
            # Cleanup script
            script_path = Path(process_info.get('script_path', ''))
            if script_path.exists():
                try:
                    script_path.unlink()
                except:
                    pass
            
            logger.info(f"Process decoy deprovisioned: {decoy_id}")
            
            del self.active_processes[decoy_id]
            
        except Exception as e:
            logger.error(f"Error deprovisioning process decoy: {e}")
            raise

