# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/executor/executor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main state machine executor with rollback logic

import os
import sys
import yaml
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .action_runners.runner_agent_call import AgentCallRunner
from .action_runners.runner_notification import NotificationRunner
from .sandbox import SandboxRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaybookExecutor:
    """
    Executes playbooks with rollback support.
    """
    
    def __init__(self):
        """Initialize executor."""
        self.agent_runner = AgentCallRunner()
        self.notification_runner = NotificationRunner()
        self.sandbox_runner = SandboxRunner()
    
    def execute(self, playbook_path: Path, context: Dict[str, Any] = None,
                dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute a playbook.
        
        Args:
            playbook_path: Path to playbook YAML file
            context: Execution context
            dry_run: If True, simulate execution without making changes
            
        Returns:
            Execution result dictionary
        """
        context = context or {}
        execution_id = str(uuid.uuid4())
        
        result = {
            'execution_id': execution_id,
            'playbook_path': str(playbook_path),
            'dry_run': dry_run,
            'started_at': datetime.utcnow().isoformat(),
            'status': 'running',
            'steps': [],
            'completed_steps': [],
            'failed_step': None,
            'rollback_performed': False
        }
        
        try:
            # Load playbook
            with open(playbook_path, 'r') as f:
                playbook_data = yaml.safe_load(f)
            
            steps = playbook_data.get('steps', [])
            completed_steps = []  # Stack for rollback
            
            # Execute each step
            for step in steps:
                step_id = step.get('id')
                step_name = step.get('name')
                
                logger.info(f"Executing step: {step_id} - {step_name}")
                
                step_result = {
                    'step_id': step_id,
                    'step_name': step_name,
                    'status': 'running',
                    'started_at': datetime.utcnow().isoformat(),
                    'output': None,
                    'error': None
                }
                
                try:
                    if dry_run:
                        # Simulate step execution
                        step_result['status'] = 'simulated'
                        step_result['output'] = f"Would execute: {step.get('action')}"
                    else:
                        # Execute step
                        step_output = self._execute_step(step, context)
                        step_result['status'] = 'completed'
                        step_result['output'] = step_output
                    
                    step_result['completed_at'] = datetime.utcnow().isoformat()
                    completed_steps.append({
                        'step': step,
                        'result': step_result
                    })
                    result['steps'].append(step_result)
                    
                except Exception as e:
                    # Step failed - trigger rollback
                    logger.error(f"Step {step_id} failed: {e}")
                    step_result['status'] = 'failed'
                    step_result['error'] = str(e)
                    step_result['completed_at'] = datetime.utcnow().isoformat()
                    result['steps'].append(step_result)
                    result['failed_step'] = step_id
                    
                    if not dry_run:
                        # Perform rollback
                        rollback_result = self._perform_rollback(completed_steps, context)
                        result['rollback_performed'] = True
                        result['rollback_result'] = rollback_result
                    
                    result['status'] = 'failed'
                    result['completed_at'] = datetime.utcnow().isoformat()
                    return result
            
            # All steps completed successfully
            result['status'] = 'completed'
            result['completed_steps'] = [s['step_id'] for s in completed_steps]
            result['completed_at'] = datetime.utcnow().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Playbook execution failed: {e}", exc_info=True)
            result['status'] = 'error'
            result['error'] = str(e)
            result['completed_at'] = datetime.utcnow().isoformat()
            
            # Rollback if we have completed steps
            if completed_steps and not dry_run:
                rollback_result = self._perform_rollback(completed_steps, context)
                result['rollback_performed'] = True
                result['rollback_result'] = rollback_result
            
            return result
    
    def _execute_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Execute a single step.
        
        Args:
            step: Step definition
            context: Execution context
            
        Returns:
            Step output
        """
        action = step.get('action')
        target = step.get('target', {})
        parameters = step.get('parameters', {})
        
        # Route to appropriate runner
        if action.startswith('agent:'):
            # Agent call (async, but executor is sync for now)
            import asyncio
            return asyncio.run(self.agent_runner.run(target, parameters, context))
        elif action.startswith('notify:') or action in ['send_email', 'send_webhook']:
            # Notification (async, but executor is sync for now)
            import asyncio
            return asyncio.run(self.notification_runner.run(target, parameters, context))
        elif action.startswith('script:') or action == 'run_script':
            # Local script (sandboxed)
            return self.sandbox_runner.run(target, parameters, context)
        else:
            raise ValueError(f"Unknown action type: {action}")
    
    def _perform_rollback(self, completed_steps: List[Dict[str, Any]], 
                         context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform rollback of completed steps.
        
        Args:
            completed_steps: List of completed steps (in execution order)
            context: Execution context
            
        Returns:
            Rollback result dictionary
        """
        rollback_result = {
            'started_at': datetime.utcnow().isoformat(),
            'steps_rolled_back': [],
            'errors': []
        }
        
        # Rollback in reverse order
        for step_info in reversed(completed_steps):
            step = step_info['step']
            step_id = step.get('id')
            
            if 'rollback' not in step:
                logger.warning(f"Step {step_id} has no rollback definition, skipping")
                continue
            
            rollback_def = step['rollback']
            rollback_action = rollback_def.get('action')
            rollback_params = rollback_def.get('parameters', {})
            
            try:
                logger.info(f"Rolling back step: {step_id}")
                
                # Execute rollback action
                if rollback_action.startswith('agent:'):
                    output = self.agent_runner.run(step.get('target', {}), rollback_params, context)
                elif rollback_action.startswith('notify:'):
                    output = self.notification_runner.run(step.get('target', {}), rollback_params, context)
                else:
                    output = f"Rollback action executed: {rollback_action}"
                
                rollback_result['steps_rolled_back'].append({
                    'step_id': step_id,
                    'status': 'rolled_back',
                    'output': output
                })
                
            except Exception as e:
                logger.error(f"Rollback failed for step {step_id}: {e}")
                rollback_result['errors'].append({
                    'step_id': step_id,
                    'error': str(e)
                })
        
        rollback_result['completed_at'] = datetime.utcnow().isoformat()
        logger.info(f"Rollback completed: {len(rollback_result['steps_rolled_back'])} steps")
        
        return rollback_result

