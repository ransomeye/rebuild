# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/monitor/decoy_monitor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Listens for interaction events (File access, Socket connection)

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..storage.config_store import ConfigStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DecoyMonitor:
    """
    Monitors decoy interactions (file access, socket connections).
    """
    
    def __init__(self):
        """Initialize decoy monitor."""
        self.config_store = ConfigStore()
        self.running = False
        self.callbacks = []  # List of callback functions
        self.monitoring_tasks = []
        
        logger.info("Decoy monitor initialized")
    
    async def start(self):
        """Start monitoring."""
        if self.running:
            logger.warning("Monitor already running")
            return
        
        self.running = True
        logger.info("Starting decoy monitor...")
        
        # Start polling tasks for each active decoy
        asyncio.create_task(self._monitoring_loop())
        
        logger.info("Decoy monitor started")
    
    async def stop(self):
        """Stop monitoring."""
        self.running = False
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.monitoring_tasks = []
        logger.info("Decoy monitor stopped")
    
    def register_callback(self, callback: Callable):
        """
        Register callback for interaction events.
        
        Args:
            callback: Async function that takes (decoy_id, event_type, event_data)
        """
        self.callbacks.append(callback)
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        last_check = {}
        
        while self.running:
            try:
                # Get active decoys
                active_decoys = await self.config_store.get_active_decoys()
                
                # Monitor each decoy
                for decoy in active_decoys:
                    decoy_id = decoy['id']
                    decoy_type = decoy['type']
                    
                    # Check for interactions based on type
                    if decoy_type == 'file':
                        await self._check_file_access(decoy_id, decoy, last_check)
                    elif decoy_type == 'service':
                        # Service connections are handled by the service itself
                        pass
                    elif decoy_type == 'process':
                        # Process monitoring would check if process was accessed/modified
                        pass
                
                # Sleep before next check
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _check_file_access(self, decoy_id: str, decoy: Dict[str, Any],
                                 last_check: Dict[str, Any]):
        """
        Check for file access events.
        
        Args:
            decoy_id: Decoy ID
            decoy: Decoy configuration
            last_check: Dictionary tracking last check times
        """
        try:
            file_path = Path(decoy['location'])
            
            if not file_path.exists():
                return
            
            # Get current access time
            current_stat = file_path.stat()
            current_atime = current_stat.st_atime
            current_mtime = current_stat.mtime
            
            # Get last check
            last_key = f"{decoy_id}_file"
            last_atime = last_check.get(last_key, {}).get('atime', current_atime)
            last_mtime = last_check.get(last_key, {}).get('mtime', current_mtime)
            
            # Check if file was accessed
            if current_atime > last_atime:
                event_data = {
                    'decoy_id': decoy_id,
                    'type': 'file_access',
                    'path': str(file_path),
                    'timestamp': datetime.fromtimestamp(current_atime).isoformat(),
                    'access_time': current_atime
                }
                await self._trigger_event(decoy_id, 'file_access', event_data)
            
            # Check if file was modified
            if current_mtime > last_mtime:
                event_data = {
                    'decoy_id': decoy_id,
                    'type': 'file_modify',
                    'path': str(file_path),
                    'timestamp': datetime.fromtimestamp(current_mtime).isoformat(),
                    'modify_time': current_mtime
                }
                await self._trigger_event(decoy_id, 'file_modify', event_data)
            
            # Update last check
            last_check[last_key] = {
                'atime': current_atime,
                'mtime': current_mtime
            }
            
        except Exception as e:
            logger.error(f"Error checking file access: {e}")
    
    async def _trigger_event(self, decoy_id: str, event_type: str, event_data: Dict[str, Any]):
        """
        Trigger interaction event.
        
        Args:
            decoy_id: Decoy ID
            event_type: Type of event
            event_data: Event data
        """
        logger.info(f"Decoy interaction: {decoy_id} - {event_type}")
        
        # Call registered callbacks
        for callback in self.callbacks:
            try:
                await callback(decoy_id, event_type, event_data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    async def record_connection(self, decoy_id: str, client_ip: str, port: int):
        """
        Record service connection event.
        
        Args:
            decoy_id: Decoy ID
            client_ip: Client IP address
            port: Port number
        """
        event_data = {
            'decoy_id': decoy_id,
            'type': 'service_connection',
            'client_ip': client_ip,
            'port': port,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self._trigger_event(decoy_id, 'service_connection', event_data)

