# Path and File Name : /home/ransomeye/rebuild/ransomeye_killchain/engine/mitre_mapper.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Maps alert types to MITRE ATT&CK TTP IDs using local JSON data

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MitreMapper:
    """Maps alert types to MITRE ATT&CK TTPs using local data."""
    
    def __init__(self, mitre_data_path: str = None):
        """
        Initialize MITRE mapper.
        
        Args:
            mitre_data_path: Path to MITRE ATT&CK JSON file
        """
        self.mitre_data_path = Path(mitre_data_path or Path(__file__).parent.parent / "data" / "mitre_attack.json")
        self.mitre_data = self._load_mitre_data()
        self.alert_to_ttp = self._build_mapping()
    
    def _load_mitre_data(self) -> Dict[str, Any]:
        """Load MITRE ATT&CK data from local JSON file."""
        if not self.mitre_data_path.exists():
            logger.warning(f"MITRE data file not found: {self.mitre_data_path}")
            return {}
        
        try:
            with open(self.mitre_data_path, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded MITRE ATT&CK data from {self.mitre_data_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load MITRE data: {e}")
            return {}
    
    def _build_mapping(self) -> Dict[str, str]:
        """
        Build mapping from alert types to TTP IDs.
        
        Returns:
            Dictionary mapping alert types to TTP IDs
        """
        mapping = {}
        
        if not self.mitre_data:
            return mapping
        
        # Extract techniques from MITRE data
        techniques = self.mitre_data.get('techniques', [])
        
        for technique in techniques:
            ttp_id = technique.get('id')
            name = technique.get('name', '').lower()
            description = technique.get('description', '').lower()
            
            # Map common alert types to TTPs
            if 'brute force' in name or 'brute force' in description:
                mapping['brute_force'] = ttp_id
                mapping['authentication_failure'] = ttp_id
            
            if 'lateral movement' in name or 'lateral' in description:
                mapping['lateral_movement'] = ttp_id
            
            if 'privilege escalation' in name or 'privilege' in description:
                mapping['privilege_escalation'] = ttp_id
                mapping['sudo'] = ttp_id
            
            if 'persistence' in name or 'persistence' in description:
                mapping['persistence'] = ttp_id
                mapping['backdoor'] = ttp_id
            
            if 'exfiltration' in name or 'exfiltration' in description:
                mapping['data_exfiltration'] = ttp_id
                mapping['exfiltration'] = ttp_id
            
            if 'command and control' in name or 'c2' in description.lower():
                mapping['c2'] = ttp_id
                mapping['command_control'] = ttp_id
            
            if 'defense evasion' in name or 'evasion' in description:
                mapping['defense_evasion'] = ttp_id
            
            if 'execution' in name:
                mapping['execution'] = ttp_id
                mapping['code_execution'] = ttp_id
        
        logger.info(f"Built MITRE mapping with {len(mapping)} entries")
        return mapping
    
    def map_alert(self, alert_type: str) -> Optional[str]:
        """
        Map alert type to MITRE TTP ID.
        
        Args:
            alert_type: Alert type string
            
        Returns:
            MITRE TTP ID or None if not found
        """
        # Try exact match
        if alert_type in self.alert_to_ttp:
            return self.alert_to_ttp[alert_type]
        
        # Try case-insensitive match
        alert_lower = alert_type.lower()
        for key, ttp_id in self.alert_to_ttp.items():
            if key.lower() == alert_lower:
                return ttp_id
        
        # Try partial match
        for key, ttp_id in self.alert_to_ttp.items():
            if key.lower() in alert_lower or alert_lower in key.lower():
                return ttp_id
        
        return None
    
    def map_timeline(self, timeline: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map all events in timeline to MITRE TTPs.
        
        Args:
            timeline: Timeline dictionary
            
        Returns:
            Timeline with MITRE mappings added
        """
        events = timeline.get('events', [])
        
        for event in events:
            alert_type = event.get('alert_type', '')
            ttp_id = self.map_alert(alert_type)
            
            if ttp_id:
                event['mitre_ttp'] = ttp_id
                event['mitre_mapped'] = True
            else:
                event['mitre_mapped'] = False
        
        timeline['mitre_mapped'] = any(e.get('mitre_mapped', False) for e in events)
        return timeline
    
    def get_ttp_info(self, ttp_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a MITRE TTP.
        
        Args:
            ttp_id: MITRE TTP ID (e.g., "T1110")
            
        Returns:
            TTP information dictionary or None
        """
        if not self.mitre_data:
            return None
        
        techniques = self.mitre_data.get('techniques', [])
        for technique in techniques:
            if technique.get('id') == ttp_id:
                return technique
        
        return None

