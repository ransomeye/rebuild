# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/validator/simulator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates execution plan for dry-run mode

import yaml
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaybookSimulator:
    """
    Simulates playbook execution to generate execution plan (dry-run).
    """
    
    def __init__(self):
        """Initialize simulator."""
        pass
    
    def generate_execution_plan(self, playbook_path: Path, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate execution plan for a playbook (dry-run).
        
        Args:
            playbook_path: Path to playbook YAML file
            context: Optional execution context
            
        Returns:
            Execution plan dictionary
        """
        context = context or {}
        
        try:
            # Load playbook
            with open(playbook_path, 'r') as f:
                playbook_data = yaml.safe_load(f)
            
            plan = {
                'playbook_name': playbook_data.get('name', 'unknown'),
                'playbook_version': playbook_data.get('version', 'unknown'),
                'risk_level': playbook_data.get('risk_level', 'unknown'),
                'steps': [],
                'estimated_duration': 0,
                'targets': set(),
                'actions': []
            }
            
            # Process each step
            steps = playbook_data.get('steps', [])
            for step in steps:
                step_plan = {
                    'step_id': step.get('id'),
                    'step_name': step.get('name'),
                    'action': step.get('action'),
                    'target': step.get('target', {}),
                    'parameters': step.get('parameters', {}),
                    'has_rollback': 'rollback' in step,
                    'timeout': step.get('timeout', 300),
                    'estimated_duration': step.get('timeout', 300)
                }
                
                # Extract target information
                target = step.get('target', {})
                if 'agent_id' in target:
                    plan['targets'].add(f"agent:{target['agent_id']}")
                elif 'tags' in target:
                    plan['targets'].add(f"tags:{', '.join(f'{k}={v}' for k, v in target['tags'].items())}")
                
                # Track action
                action = step.get('action')
                if action:
                    plan['actions'].append(action)
                
                plan['steps'].append(step_plan)
                plan['estimated_duration'] += step_plan['estimated_duration']
            
            # Convert targets set to list
            plan['targets'] = list(plan['targets'])
            
            # Add summary
            plan['summary'] = {
                'total_steps': len(plan['steps']),
                'unique_targets': len(plan['targets']),
                'unique_actions': len(set(plan['actions'])),
                'has_rollback': all(s['has_rollback'] for s in plan['steps'])
            }
            
            logger.info(f"Generated execution plan: {len(plan['steps'])} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Error generating execution plan: {e}", exc_info=True)
            return {
                'error': str(e),
                'steps': [],
                'summary': {}
            }

