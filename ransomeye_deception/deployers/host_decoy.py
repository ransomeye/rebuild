# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/deployers/host_decoy.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Manages virtual IP aliases (requires sudo/capabilities, safe fallback if permission denied)

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HostDecoy:
    """
    Host decoy deployer.
    Manages virtual IP aliases for host decoys.
    """
    
    def __init__(self):
        """Initialize host decoy deployer."""
        self.active_hosts = {}  # decoy_id -> {ip, interface, alias}
        self.capabilities_available = self._check_capabilities()
        
        logger.info(f"Host decoy deployer initialized (capabilities: {self.capabilities_available})")
    
    def _check_capabilities(self) -> bool:
        """Check if we have capabilities to manage IP aliases."""
        try:
            # Try to list interfaces (non-destructive check)
            result = subprocess.run(
                ['ip', 'addr', 'show'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            return False
    
    async def provision(self, decoy_id: str, location: str,
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Provision a host decoy.
        
        Args:
            decoy_id: Unique decoy ID
            location: IP address or IP range
            metadata: Optional metadata
            
        Returns:
            Provision result
        """
        try:
            if not self.capabilities_available:
                logger.warning("IP alias capabilities not available, logging warning only")
                return {
                    'decoy_id': decoy_id,
                    'type': 'host',
                    'ip': location,
                    'status': 'simulated',
                    'warning': 'IP alias creation requires root privileges'
                }
            
            # Parse IP address
            ip_address = location.split('/')[0] if '/' in location else location
            
            # Get primary network interface
            try:
                result = subprocess.run(
                    ['ip', 'route', 'get', '8.8.8.8'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Extract interface name
                    interface = None
                    for line in result.stdout.split('\n'):
                        if 'dev' in line:
                            parts = line.split()
                            if 'dev' in parts:
                                idx = parts.index('dev')
                                if idx + 1 < len(parts):
                                    interface = parts[idx + 1]
                                    break
                    
                    if not interface:
                        interface = 'eth0'  # Default
                else:
                    interface = 'eth0'
            except:
                interface = 'eth0'
            
            # Create IP alias (requires root)
            alias_name = f"{interface}:{decoy_id[:8]}"
            
            try:
                # Add IP alias
                result = subprocess.run(
                    ['sudo', 'ip', 'addr', 'add', f'{ip_address}/24', 'dev', interface, 'label', alias_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    logger.warning(f"Failed to add IP alias: {result.stderr}")
                    return {
                        'decoy_id': decoy_id,
                        'type': 'host',
                        'ip': ip_address,
                        'status': 'failed',
                        'error': result.stderr
                    }
                
                # Store host info
                self.active_hosts[decoy_id] = {
                    'ip': ip_address,
                    'interface': interface,
                    'alias': alias_name
                }
                
                logger.info(f"Host decoy provisioned: {ip_address} on {interface}")
                
                return {
                    'decoy_id': decoy_id,
                    'type': 'host',
                    'ip': ip_address,
                    'interface': interface,
                    'alias': alias_name,
                    'status': 'active'
                }
                
            except subprocess.TimeoutExpired:
                raise RuntimeError("Timeout adding IP alias")
            except FileNotFoundError:
                logger.warning("ip command not found, cannot manage IP aliases")
                return {
                    'decoy_id': decoy_id,
                    'type': 'host',
                    'ip': ip_address,
                    'status': 'simulated',
                    'warning': 'ip command not available'
                }
            
        except Exception as e:
            logger.error(f"Error provisioning host decoy: {e}")
            raise
    
    async def verify(self, decoy_id: str, provision_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify host decoy is active.
        
        Args:
            decoy_id: Decoy ID
            provision_result: Provision result
            
        Returns:
            Verification result
        """
        try:
            if provision_result.get('status') in ['simulated', 'failed']:
                return {
                    'verified': False,
                    'error': provision_result.get('error', 'Host decoy not actually provisioned')
                }
            
            if decoy_id not in self.active_hosts:
                return {
                    'verified': False,
                    'error': 'Decoy not found in active hosts'
                }
            
            ip_address = provision_result['ip']
            interface = provision_result.get('interface', 'eth0')
            
            # Check if IP alias exists
            try:
                result = subprocess.run(
                    ['ip', 'addr', 'show', interface],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if ip_address in result.stdout:
                    return {
                        'verified': True,
                        'ip': ip_address,
                        'interface': interface
                    }
                else:
                    return {
                        'verified': False,
                        'error': 'IP alias not found on interface'
                    }
            except:
                return {
                    'verified': False,
                    'error': 'Could not verify IP alias'
                }
            
        except Exception as e:
            return {
                'verified': False,
                'error': str(e)
            }
    
    async def deprovision(self, decoy_id: str, provision_result: Dict[str, Any]):
        """
        Deprovision host decoy.
        
        Args:
            decoy_id: Decoy ID
            provision_result: Provision result
        """
        try:
            if decoy_id not in self.active_hosts:
                return
            
            host_info = self.active_hosts[decoy_id]
            ip_address = host_info['ip']
            interface = host_info['interface']
            
            try:
                # Remove IP alias
                result = subprocess.run(
                    ['sudo', 'ip', 'addr', 'del', f'{ip_address}/24', 'dev', interface],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    logger.warning(f"Failed to remove IP alias: {result.stderr}")
                
                logger.info(f"Host decoy deprovisioned: {ip_address}")
                
            except Exception as e:
                logger.warning(f"Error removing IP alias: {e}")
            
            del self.active_hosts[decoy_id]
            
        except Exception as e:
            logger.error(f"Error deprovisioning host decoy: {e}")
            raise

