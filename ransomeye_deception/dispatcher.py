# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/dispatcher.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main orchestrator that schedules placement jobs and triggers rotation based on ROTATION_INTERVAL

import os
import sys
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .placement_engine import PlacementEngine
from .rotator import Rotator
from .storage.config_store import ConfigStore
from .monitor.decoy_monitor import DecoyMonitor
from .monitor.alert_engine import AlertEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Dispatcher:
    """
    Main orchestrator for decoy deployment and rotation.
    Schedules placement jobs and manages rotation cycles.
    """
    
    def __init__(self):
        """Initialize dispatcher."""
        self.placement_engine = PlacementEngine()
        self.config_store = ConfigStore()
        self.monitor = DecoyMonitor()
        self.alert_engine = AlertEngine()
        
        # Create rotator with connection callback
        self.rotator = Rotator(connection_callback=self._on_service_connection)
        
        # Register alert callback
        self.monitor.register_callback(self._on_decoy_interaction)
        
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Rotation interval from env (in minutes)
        rotation_interval_min = int(os.environ.get('ROTATION_INTERVAL', '60'))
        self.rotation_interval = timedelta(minutes=rotation_interval_min)
        
        logger.info(f"Dispatcher initialized with rotation interval: {rotation_interval_min} minutes")
    
    async def start(self):
        """Start dispatcher background tasks."""
        if self.running:
            logger.warning("Dispatcher already running")
            return
        
        self.running = True
        logger.info("Starting dispatcher...")
        
        # Start monitoring
        await self.monitor.start()
        
        # Start rotation scheduler
        asyncio.create_task(self._rotation_scheduler())
        
        logger.info("Dispatcher started")
    
    async def stop(self):
        """Stop dispatcher."""
        self.running = False
        await self.monitor.stop()
        self.executor.shutdown(wait=True)
        logger.info("Dispatcher stopped")
    
    async def _rotation_scheduler(self):
        """Background task that triggers rotation at intervals."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Get all active decoys
                active_decoys = await self.config_store.get_active_decoys()
                
                if not active_decoys:
                    continue
                
                # Check which decoys need rotation
                now = datetime.utcnow()
                for decoy in active_decoys:
                    last_rotation = decoy.get('last_rotated_at')
                    if last_rotation:
                        last_rotation = datetime.fromisoformat(last_rotation)
                        if now - last_rotation >= self.rotation_interval:
                            logger.info(f"Triggering rotation for decoy {decoy['id']}")
                            await self.rotate_decoy(decoy['id'])
                    else:
                        # First rotation if never rotated
                        await self.rotate_decoy(decoy['id'])
                        
            except Exception as e:
                logger.error(f"Error in rotation scheduler: {e}")
                await asyncio.sleep(60)
    
    async def deploy_decoy(self, decoy_type: str, target_location: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Deploy a new decoy using placement engine.
        
        Args:
            decoy_type: Type of decoy (file, service, process, host)
            target_location: Optional specific location, otherwise AI selects
            metadata: Optional metadata for placement
            
        Returns:
            Deployment result dictionary
        """
        try:
            logger.info(f"Deploying {decoy_type} decoy")
            
            # Get placement recommendation
            if target_location:
                placement = {
                    'location': target_location,
                    'score': 1.0,
                    'reasoning': 'Manual placement'
                }
            else:
                placement = await self.placement_engine.recommend_placement(
                    decoy_type=decoy_type,
                    metadata=metadata or {}
                )
            
            # Deploy using rotator (which handles atomic provisioning)
            result = await self.rotator.deploy(
                decoy_type=decoy_type,
                location=placement['location'],
                metadata={
                    **(metadata or {}),
                    'placement_score': placement['score'],
                    'placement_reasoning': placement['reasoning']
                }
            )
            
            logger.info(f"Decoy deployed: {result['decoy_id']}")
            return result
            
        except Exception as e:
            logger.error(f"Error deploying decoy: {e}")
            raise
    
    async def rotate_decoy(self, decoy_id: str) -> Dict[str, Any]:
        """
        Rotate an existing decoy.
        
        Args:
            decoy_id: ID of decoy to rotate
            
        Returns:
            Rotation result dictionary
        """
        try:
            logger.info(f"Rotating decoy {decoy_id}")
            
            # Get current decoy config
            decoy = await self.config_store.get_decoy(decoy_id)
            if not decoy:
                raise ValueError(f"Decoy {decoy_id} not found")
            
            # Get new placement recommendation
            placement = await self.placement_engine.recommend_placement(
                decoy_type=decoy['type'],
                metadata=decoy.get('metadata', {})
            )
            
            # Rotate using rotator (atomic operation)
            result = await self.rotator.rotate(
                decoy_id=decoy_id,
                new_location=placement['location'],
                metadata={
                    **(decoy.get('metadata', {})),
                    'placement_score': placement['score'],
                    'placement_reasoning': placement['reasoning']
                }
            )
            
            logger.info(f"Decoy rotated: {decoy_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error rotating decoy: {e}")
            raise
    
    async def get_deployment_status(self) -> Dict[str, Any]:
        """
        Get current deployment status.
        
        Returns:
            Status dictionary
        """
        active_decoys = await self.config_store.get_active_decoys()
        
            return {
                'total_decoys': len(active_decoys),
                'by_type': {
                    decoy['type']: sum(1 for d in active_decoys if d['type'] == decoy['type'])
                    for decoy in active_decoys
                },
                'decoys': active_decoys
            }
    
    async def _on_decoy_interaction(self, decoy_id: str, event_type: str, event_data: Dict[str, Any]):
        """
        Handle decoy interaction event.
        
        Args:
            decoy_id: Decoy ID
            event_type: Type of event
            event_data: Event data
        """
        # Send alert
        await self.alert_engine.send_decoy_alert(decoy_id, event_type, event_data)
    
    async def _on_service_connection(self, decoy_id: str, client_ip: str, port: int):
        """
        Handle service connection event.
        
        Args:
            decoy_id: Decoy ID
            client_ip: Client IP address
            port: Port number
        """
        # Record connection in monitor
        await self.monitor.record_connection(decoy_id, client_ip, port)

