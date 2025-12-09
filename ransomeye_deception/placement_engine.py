# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/placement_engine.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: AI Logic that queries ML model to calculate Attractiveness Score for potential deployment slots

import os
import sys
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .ml.placement_model import PlacementModel
from .ml.shap_support import SHAPSupport
from .storage.config_store import ConfigStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlacementEngine:
    """
    AI-driven placement engine for decoy deployment.
    Uses ML model to calculate attractiveness scores for potential locations.
    """
    
    def __init__(self):
        """Initialize placement engine."""
        self.placement_model = PlacementModel()
        self.shap_support = SHAPSupport()
        self.config_store = ConfigStore()
        
        logger.info("Placement engine initialized")
    
    async def recommend_placement(self, decoy_type: str,
                                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Recommend optimal placement location for a decoy.
        
        Args:
            decoy_type: Type of decoy (file, service, process, host)
            metadata: Optional metadata (host_criticality, segment, etc.)
            
        Returns:
            Placement recommendation with location, score, and reasoning
        """
        try:
            # Get candidate locations
            candidates = await self._get_candidate_locations(decoy_type)
            
            if not candidates:
                # Fallback to default location
                default_location = self._get_default_location(decoy_type)
                return {
                    'location': default_location,
                    'score': 0.5,
                    'reasoning': 'Default placement (no candidates available)'
                }
            
            # Evaluate each candidate
            scores = []
            for candidate in candidates:
                features = self._extract_features(candidate, decoy_type, metadata or {})
                score = self.placement_model.predict_attractiveness(features)
                scores.append((candidate, score, features))
            
            # Select best candidate
            best_candidate, best_score, best_features = max(scores, key=lambda x: x[1])
            
            # Generate SHAP explanation
            shap_explanation = await self.shap_support.explain_placement(
                features=best_features,
                score=best_score,
                decoy_type=decoy_type
            )
            
            # Build reasoning from SHAP values
            reasoning = self._build_reasoning(shap_explanation, best_candidate, decoy_type)
            
            return {
                'location': best_candidate,
                'score': float(best_score),
                'reasoning': reasoning,
                'shap_explanation': shap_explanation,
                'alternatives': [
                    {'location': loc, 'score': float(score)}
                    for loc, score, _ in sorted(scores, key=lambda x: x[1], reverse=True)[:3]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in placement recommendation: {e}")
            # Fallback to default
            default_location = self._get_default_location(decoy_type)
            return {
                'location': default_location,
                'score': 0.5,
                'reasoning': f'Fallback placement due to error: {str(e)}'
            }
    
    async def _get_candidate_locations(self, decoy_type: str) -> List[Dict[str, Any]]:
        """
        Get candidate locations for deployment.
        
        Args:
            decoy_type: Type of decoy
            
        Returns:
            List of candidate location dictionaries
        """
        candidates = []
        
        if decoy_type == 'file':
            # File decoy candidates: common sensitive directories
            base_paths = [
                '/home', '/var/www', '/opt', '/tmp', '/var/log',
                '/etc', '/root', '/usr/local'
            ]
            file_names = [
                'passwords.txt', 'credentials.txt', 'secret.key',
                'budget.xlsx', 'employee_data.csv', 'config.ini',
                'backup.tar.gz', 'database_dump.sql'
            ]
            
            for base in base_paths:
                for name in file_names:
                    candidates.append({
                        'type': 'file',
                        'path': f"{base}/{name}",
                        'host_criticality': 0.8 if base in ['/root', '/etc'] else 0.5,
                        'segment': base.split('/')[-1] if base.split('/')[-1] else 'root'
                    })
        
        elif decoy_type == 'service':
            # Service decoy candidates: common ports
            ports = [22, 80, 443, 3306, 5432, 8080, 8443, 3389, 5900]
            for port in ports:
                candidates.append({
                    'type': 'service',
                    'port': port,
                    'host': '0.0.0.0',
                    'host_criticality': 0.7,
                    'segment': 'network'
                })
        
        elif decoy_type == 'process':
            # Process decoy candidates: common process names
            process_names = [
                'backup_admin', 'db_maintenance', 'cron_job',
                'system_monitor', 'backup_service'
            ]
            for name in process_names:
                candidates.append({
                    'type': 'process',
                    'name': name,
                    'host_criticality': 0.6,
                    'segment': 'system'
                })
        
        elif decoy_type == 'host':
            # Host decoy candidates: network segments
            ip_ranges = [
                '10.0.0.0/24', '192.168.1.0/24', '172.16.0.0/24'
            ]
            for ip_range in ip_ranges:
                candidates.append({
                    'type': 'host',
                    'ip_range': ip_range,
                    'host_criticality': 0.8,
                    'segment': 'internal'
                })
        
        # Filter out locations already used by active decoys
        active_decoys = await self.config_store.get_active_decoys()
        active_locations = {d['location'] for d in active_decoys}
        
        filtered_candidates = [
            c for c in candidates
            if self._location_key(c) not in active_locations
        ]
        
        return filtered_candidates[:20]  # Limit to top 20 candidates
    
    def _location_key(self, candidate: Dict[str, Any]) -> str:
        """Generate unique key for location."""
        if candidate['type'] == 'file':
            return f"file:{candidate['path']}"
        elif candidate['type'] == 'service':
            return f"service:{candidate['port']}"
        elif candidate['type'] == 'process':
            return f"process:{candidate['name']}"
        elif candidate['type'] == 'host':
            return f"host:{candidate['ip_range']}"
        return str(candidate)
    
    def _extract_features(self, candidate: Dict[str, Any], decoy_type: str,
                         metadata: Dict[str, Any]) -> np.ndarray:
        """
        Extract feature vector for ML model.
        
        Args:
            candidate: Candidate location dictionary
            decoy_type: Type of decoy
            metadata: Additional metadata
            
        Returns:
            Feature vector numpy array
        """
        # Get existing decoy density in same segment
        existing_density = metadata.get('existing_density', 0.0)
        
        # Base features
        features = [
            candidate.get('host_criticality', 0.5),
            float(hash(candidate.get('segment', 'default')) % 100) / 100.0,  # Segment hash normalized
            existing_density,
            float(hash(decoy_type) % 10) / 10.0,  # Decoy type hash normalized
        ]
        
        # Add type-specific features
        if decoy_type == 'file':
            path_depth = len(candidate.get('path', '').split('/'))
            features.append(float(path_depth) / 10.0)
        elif decoy_type == 'service':
            port = candidate.get('port', 0)
            features.append(float(port) / 65535.0)
        elif decoy_type == 'process':
            name_len = len(candidate.get('name', ''))
            features.append(float(name_len) / 50.0)
        elif decoy_type == 'host':
            ip_class = hash(candidate.get('ip_range', '')) % 3
            features.append(float(ip_class) / 3.0)
        
        return np.array(features).reshape(1, -1)
    
    def _get_default_location(self, decoy_type: str) -> str:
        """Get default location for decoy type."""
        defaults = {
            'file': '/tmp/honeyfile.txt',
            'service': '0.0.0.0:2222',
            'process': 'backup_admin',
            'host': '10.0.0.100'
        }
        return defaults.get(decoy_type, '/tmp/default')
    
    def _build_reasoning(self, shap_explanation: Optional[Dict[str, Any]],
                        candidate: Dict[str, Any], decoy_type: str) -> str:
        """
        Build human-readable reasoning from SHAP explanation.
        
        Args:
            shap_explanation: SHAP explanation dictionary
            candidate: Candidate location
            decoy_type: Type of decoy
            
        Returns:
            Reasoning string
        """
        if not shap_explanation or 'shap_values' not in shap_explanation:
            return f"Placed based on {decoy_type} placement model"
        
        shap_values = shap_explanation['shap_values']
        
        # Find top contributing features
        top_features = sorted(
            shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:3]
        
        reasons = []
        for feature, value in top_features:
            if abs(value) > 0.1:  # Only mention significant contributions
                direction = "increased" if value > 0 else "decreased"
                reasons.append(f"{feature} {direction} attractiveness by {abs(value):.2f}")
        
        base_reason = f"High-value asset proximity"
        if reasons:
            return f"{base_reason}. Top factors: {', '.join(reasons)}"
        return base_reason

