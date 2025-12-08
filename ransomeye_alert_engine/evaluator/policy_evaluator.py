# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/evaluator/policy_evaluator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Core policy evaluation logic that matches alerts against active rules

import threading
from typing import Dict, Any, List, Optional
import logging

from ..loader.policy_loader import get_policy_loader
from .rule_compiler import CompiledRule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolicyEvaluator:
    """
    Core policy evaluator that matches alerts against active rules.
    Thread-safe as policy_loader may swap rules in the background.
    """
    
    def __init__(self):
        """Initialize evaluator."""
        self.policy_loader = get_policy_loader()
        self._evaluation_lock = threading.RLock()
    
    def evaluate_alert(self, source: str, alert_type: str, target: str,
                      severity: str = "medium", metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Evaluate an alert against active rules.
        
        Args:
            source: Alert source
            alert_type: Type of alert
            target: Alert target
            severity: Alert severity
            metadata: Additional metadata
            
        Returns:
            List of matching rules with actions
        """
        metadata = metadata or {}
        
        # Get compiled rules (thread-safe copy)
        compiled_rules = self.policy_loader.get_compiled_rules()
        
        if not compiled_rules:
            logger.debug("No active rules to evaluate against")
            return []
        
        matches = []
        
        # Evaluate against each rule
        for compiled_rule in compiled_rules:
            try:
                if self._match_rule(compiled_rule, source, alert_type, target, severity, metadata):
                    matches.append({
                        'rule_name': compiled_rule.rule_name,
                        'severity': compiled_rule.severity,
                        'action': compiled_rule.action,
                        'description': compiled_rule.description
                    })
            except Exception as e:
                logger.warning(f"Error evaluating rule {compiled_rule.rule_name}: {e}")
        
        return matches
    
    def _match_rule(self, rule: CompiledRule, source: str, alert_type: str,
                   target: str, severity: str, metadata: Dict[str, Any]) -> bool:
        """
        Check if an alert matches a rule's condition.
        
        Args:
            rule: Compiled rule
            source: Alert source
            alert_type: Alert type
            target: Alert target
            severity: Alert severity
            metadata: Alert metadata
            
        Returns:
            True if rule matches, False otherwise
        """
        condition_type = rule.condition_type
        field = rule.field
        
        # Build field value map
        field_values = {
            'source': source,
            'alert_type': alert_type,
            'type': alert_type,  # Alias
            'target': target,
            'severity': severity
        }
        field_values.update(metadata)
        
        # Get field value
        field_value = field_values.get(field, '')
        
        # Evaluate based on condition type
        if condition_type == 'match':
            return str(field_value) == str(rule.value)
        
        elif condition_type == 'regex':
            if rule.compiled_pattern:
                return bool(rule.compiled_pattern.search(str(field_value)))
            return False
        
        elif condition_type == 'contains':
            return str(rule.value).lower() in str(field_value).lower()
        
        elif condition_type == 'equals':
            return str(field_value).lower() == str(rule.value).lower()
        
        elif condition_type == 'range':
            try:
                numeric_value = float(field_value)
                if rule.min_value is not None and numeric_value < rule.min_value:
                    return False
                if rule.max_value is not None and numeric_value > rule.max_value:
                    return False
                return True
            except (ValueError, TypeError):
                return False
        
        return False

