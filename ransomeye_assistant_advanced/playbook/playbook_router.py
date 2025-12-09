# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/playbook/playbook_router.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main playbook router that fetches playbooks from Phase 6 registry and uses ML matcher

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from ransomeye_response.registry.playbook_registry import PlaybookRegistry
    PLAYBOOK_REGISTRY_AVAILABLE = True
except ImportError:
    PLAYBOOK_REGISTRY_AVAILABLE = False
    logging.warning("Playbook registry not available - using fallback")

from .playbook_matcher import PlaybookMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaybookRouter:
    """Main playbook router that suggests playbooks based on incident summaries."""
    
    def __init__(self):
        """Initialize playbook router."""
        if PLAYBOOK_REGISTRY_AVAILABLE:
            self.registry = PlaybookRegistry()
        else:
            self.registry = None
        
        self.matcher = PlaybookMatcher()
        self._load_playbooks()
    
    def _load_playbooks(self):
        """Load available playbooks from registry."""
        if self.registry:
            try:
                playbooks = self.registry.list_playbooks(active_only=True)
                logger.info(f"Loaded {len(playbooks)} active playbooks from registry")
                self.matcher.update_playbooks(playbooks)
            except Exception as e:
                logger.error(f"Error loading playbooks: {e}")
        else:
            logger.warning("Playbook registry not available - using default playbooks")
            # Use default playbooks
            default_playbooks = [
                {'id': 1, 'name': 'Isolate Host', 'risk_level': 'high'},
                {'id': 2, 'name': 'Contain Network', 'risk_level': 'critical'},
                {'id': 3, 'name': 'Collect Evidence', 'risk_level': 'medium'},
                {'id': 4, 'name': 'Notify Stakeholders', 'risk_level': 'low'}
            ]
            self.matcher.update_playbooks(default_playbooks)
    
    def suggest_playbook(self, summary: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Suggest a playbook based on incident summary.
        
        Args:
            summary: Incident summary text
            context: Optional context (OCR text, detected objects, etc.)
            
        Returns:
            Dictionary with playbook_id, playbook_name, confidence, and reasoning
        """
        # Combine summary and context
        full_text = summary
        if context:
            if context.get('ocr_text'):
                full_text += " " + context['ocr_text']
            if context.get('detected_objects'):
                full_text += " " + " ".join(context['detected_objects'])
        
        # Match playbook
        match_result = self.matcher.match(full_text, context)
        
        # Get playbook details from registry
        playbook_id = match_result['playbook_id']
        playbook_name = match_result['playbook_name']
        
        if self.registry:
            try:
                playbook = self.registry.get_playbook(playbook_id)
                if playbook:
                    playbook_name = playbook.get('name', playbook_name)
            except Exception as e:
                logger.warning(f"Error fetching playbook details: {e}")
        
        return {
            'playbook_id': playbook_id,
            'playbook_name': playbook_name,
            'confidence': match_result['confidence'],
            'reasoning': match_result['reasoning']
        }
    
    def is_ready(self) -> bool:
        """Check if router is ready."""
        return self.matcher.is_ready()

