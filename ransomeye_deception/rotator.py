# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/rotator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages lifecycle with atomic Provision -> Verify -> Deprovision loop

import os
import sys
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .deployers.file_decoy import FileDecoy
from .deployers.service_decoy import ServiceDecoy
from .deployers.process_decoy import ProcessDecoy
from .deployers.host_decoy import HostDecoy
from .storage.config_store import ConfigStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Rotator:
    """
    Manages decoy lifecycle with atomic rotation.
    Implements: Setup New -> Verify -> Tear Down Old
    """
    
    def __init__(self):
        """Initialize rotator."""
        self.config_store = ConfigStore()
        
        # Initialize deployers
        self.deployers = {
            'file': FileDecoy(),
            'service': ServiceDecoy(),
            'process': ProcessDecoy(),
            'host': HostDecoy()
        }
        
        logger.info("Rotator initialized")
    
    async def deploy(self, decoy_type: str, location: str,
                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Deploy a new decoy atomically.
        
        Args:
            decoy_type: Type of decoy
            location: Target location
            metadata: Optional metadata
            
        Returns:
            Deployment result
        """
        decoy_id = str(uuid.uuid4())
        
        try:
            # Get appropriate deployer
            deployer = self.deployers.get(decoy_type)
            if not deployer:
                raise ValueError(f"Unknown decoy type: {decoy_type}")
            
            # Step 1: Provision new decoy
            logger.info(f"Provisioning {decoy_type} decoy at {location}")
            provision_result = await deployer.provision(
                decoy_id=decoy_id,
                location=location,
                metadata=metadata or {}
            )
            
            # Step 2: Verify deployment
            logger.info(f"Verifying {decoy_type} decoy {decoy_id}")
            verification = await deployer.verify(decoy_id, provision_result)
            
            if not verification['verified']:
                # Cleanup failed deployment
                await deployer.deprovision(decoy_id, provision_result)
                raise RuntimeError(f"Verification failed: {verification.get('error')}")
            
            # Step 3: Store configuration
            await self.config_store.create_decoy({
                'id': decoy_id,
                'type': decoy_type,
                'location': location,
                'metadata': metadata or {},
                'provision_result': provision_result,
                'created_at': datetime.utcnow().isoformat(),
                'last_rotated_at': None,
                'status': 'active'
            })
            
            logger.info(f"Decoy {decoy_id} deployed successfully")
            
            return {
                'decoy_id': decoy_id,
                'type': decoy_type,
                'location': location,
                'status': 'active',
                'provision_result': provision_result
            }
            
        except Exception as e:
            logger.error(f"Error deploying decoy: {e}")
            # Attempt cleanup
            try:
                deployer = self.deployers.get(decoy_type)
                if deployer:
                    await deployer.deprovision(decoy_id, {})
            except:
                pass
            raise
    
    async def rotate(self, decoy_id: str, new_location: str,
                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Rotate an existing decoy atomically.
        Setup New -> Verify -> Tear Down Old
        
        Args:
            decoy_id: ID of existing decoy
            new_location: New location for rotation
            metadata: Optional metadata
            
        Returns:
            Rotation result
        """
        try:
            # Get existing decoy config
            old_decoy = await self.config_store.get_decoy(decoy_id)
            if not old_decoy:
                raise ValueError(f"Decoy {decoy_id} not found")
            
            decoy_type = old_decoy['type']
            old_location = old_decoy['location']
            old_provision_result = old_decoy.get('provision_result', {})
            
            deployer = self.deployers.get(decoy_type)
            if not deployer:
                raise ValueError(f"Unknown decoy type: {decoy_type}")
            
            # Step 1: Provision new decoy at new location
            logger.info(f"Provisioning new {decoy_type} decoy at {new_location}")
            new_provision_result = await deployer.provision(
                decoy_id=decoy_id,  # Reuse same ID
                location=new_location,
                metadata=metadata or {}
            )
            
            # Step 2: Verify new deployment
            logger.info(f"Verifying new decoy at {new_location}")
            verification = await deployer.verify(decoy_id, new_provision_result)
            
            if not verification['verified']:
                # Cleanup failed new deployment
                await deployer.deprovision(decoy_id, new_provision_result)
                raise RuntimeError(f"Verification failed: {verification.get('error')}")
            
            # Step 3: Deprovision old decoy (atomic step - if this fails, new one is still active)
            logger.info(f"Deprovisioning old decoy at {old_location}")
            try:
                await deployer.deprovision(decoy_id, old_provision_result)
            except Exception as e:
                logger.warning(f"Error deprovisioning old decoy (new one is active): {e}")
            
            # Step 4: Update configuration
            await self.config_store.update_decoy(decoy_id, {
                'location': new_location,
                'metadata': metadata or {},
                'provision_result': new_provision_result,
                'last_rotated_at': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Decoy {decoy_id} rotated from {old_location} to {new_location}")
            
            return {
                'decoy_id': decoy_id,
                'type': decoy_type,
                'old_location': old_location,
                'new_location': new_location,
                'status': 'rotated'
            }
            
        except Exception as e:
            logger.error(f"Error rotating decoy: {e}")
            raise
    
    async def remove(self, decoy_id: str) -> Dict[str, Any]:
        """
        Remove a decoy completely.
        
        Args:
            decoy_id: ID of decoy to remove
            
        Returns:
            Removal result
        """
        try:
            decoy = await self.config_store.get_decoy(decoy_id)
            if not decoy:
                raise ValueError(f"Decoy {decoy_id} not found")
            
            decoy_type = decoy['type']
            deployer = self.deployers.get(decoy_type)
            
            if deployer:
                provision_result = decoy.get('provision_result', {})
                await deployer.deprovision(decoy_id, provision_result)
            
            await self.config_store.remove_decoy(decoy_id)
            
            logger.info(f"Decoy {decoy_id} removed")
            
            return {
                'decoy_id': decoy_id,
                'status': 'removed'
            }
            
        except Exception as e:
            logger.error(f"Error removing decoy: {e}")
            raise

