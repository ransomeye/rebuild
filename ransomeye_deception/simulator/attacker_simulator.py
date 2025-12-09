# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/simulator/attacker_simulator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Automated probing tool that reads sim_policies and connects to own decoys to verify visibility

import os
import sys
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AttackerSimulator:
    """
    Safe attacker simulator for testing decoy visibility.
    Probes own decoys to verify they trigger alerts.
    """
    
    def __init__(self, policy_path: Optional[str] = None):
        """
        Initialize attacker simulator.
        
        Args:
            policy_path: Path to safety policy file
        """
        self.policy_path = policy_path or str(
            Path(__file__).parent / 'sim_policies' / 'safety.json'
        )
        self.policy = self._load_policy()
        
        logger.info("Attacker simulator initialized")
    
    def _load_policy(self) -> Dict[str, Any]:
        """Load safety policy."""
        try:
            policy_file = Path(self.policy_path)
            if policy_file.exists():
                with open(policy_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load policy: {e}")
        
        # Default safe policy
        return {
            'enabled': True,
            'max_rate_per_second': 1,
            'allowed_targets': ['localhost', '127.0.0.1'],
            'probe_types': ['file', 'service'],
            'safe_mode': True
        }
    
    async def simulate_attack(self, decoy_type: str, target: str,
                             duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Simulate attack on decoy.
        
        Args:
            decoy_type: Type of decoy (file, service)
            target: Target location (file path or host:port)
            duration_seconds: Duration of simulation
            
        Returns:
            Simulation results
        """
        if not self.policy.get('enabled', True):
            return {
                'status': 'disabled',
                'reason': 'Simulation disabled by policy'
            }
        
        if self.policy.get('safe_mode', True):
            # Only probe localhost
            if 'localhost' not in target and '127.0.0.1' not in target:
                return {
                    'status': 'blocked',
                    'reason': 'Safe mode: only localhost allowed'
                }
        
        results = {
            'decoy_type': decoy_type,
            'target': target,
            'start_time': datetime.utcnow().isoformat(),
            'probes': [],
            'success_count': 0,
            'failure_count': 0
        }
        
        try:
            if decoy_type == 'file':
                await self._simulate_file_probe(target, results)
            elif decoy_type == 'service':
                await self._simulate_service_probe(target, results)
            
            results['end_time'] = datetime.utcnow().isoformat()
            results['status'] = 'completed'
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Simulation error: {e}")
        
        return results
    
    async def _simulate_file_probe(self, file_path: str, results: Dict[str, Any]):
        """
        Simulate file access probe.
        
        Args:
            file_path: Path to file
            results: Results dictionary to update
        """
        try:
            path = Path(file_path)
            
            # Rate limiting
            max_rate = self.policy.get('max_rate_per_second', 1)
            delay = 1.0 / max_rate
            
            # Probe file
            if path.exists():
                # Read file
                content = path.read_text()
                
                results['probes'].append({
                    'type': 'read',
                    'success': True,
                    'size': len(content),
                    'timestamp': datetime.utcnow().isoformat()
                })
                results['success_count'] += 1
                
                await asyncio.sleep(delay)
            else:
                results['probes'].append({
                    'type': 'read',
                    'success': False,
                    'error': 'File not found',
                    'timestamp': datetime.utcnow().isoformat()
                })
                results['failure_count'] += 1
                
        except Exception as e:
            results['probes'].append({
                'type': 'read',
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
            results['failure_count'] += 1
    
    async def _simulate_service_probe(self, target: str, results: Dict[str, Any]):
        """
        Simulate service connection probe.
        
        Args:
            target: Host:Port format
            results: Results dictionary to update
        """
        try:
            if ':' in target:
                host, port_str = target.rsplit(':', 1)
                port = int(port_str)
            else:
                host = target
                port = 22  # Default SSH
            
            # Rate limiting
            max_rate = self.policy.get('max_rate_per_second', 1)
            delay = 1.0 / max_rate
            
            # Try to connect
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5.0
                )
                
                # Read banner
                banner = await asyncio.wait_for(reader.read(1024), timeout=2.0)
                
                writer.close()
                await writer.wait_closed()
                
                results['probes'].append({
                    'type': 'connect',
                    'success': True,
                    'banner': banner[:100].decode('utf-8', errors='ignore'),
                    'timestamp': datetime.utcnow().isoformat()
                })
                results['success_count'] += 1
                
            except (ConnectionRefusedError, asyncio.TimeoutError) as e:
                results['probes'].append({
                    'type': 'connect',
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
                results['failure_count'] += 1
            
            await asyncio.sleep(delay)
            
        except Exception as e:
            results['probes'].append({
                'type': 'connect',
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
            results['failure_count'] += 1
    
    async def verify_all_decoys(self, decoy_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify all decoys in list are visible.
        
        Args:
            decoy_list: List of decoy configurations
            
        Returns:
            Verification results
        """
        results = {
            'total_decoys': len(decoy_list),
            'verified': 0,
            'failed': 0,
            'details': []
        }
        
        for decoy in decoy_list:
            decoy_type = decoy['type']
            location = decoy['location']
            
            sim_result = await self.simulate_attack(decoy_type, location)
            
            if sim_result.get('success_count', 0) > 0:
                results['verified'] += 1
                results['details'].append({
                    'decoy_id': decoy.get('id'),
                    'type': decoy_type,
                    'location': location,
                    'status': 'visible'
                })
            else:
                results['failed'] += 1
                results['details'].append({
                    'decoy_id': decoy.get('id'),
                    'type': decoy_type,
                    'location': location,
                    'status': 'not_visible'
                })
        
        return results

