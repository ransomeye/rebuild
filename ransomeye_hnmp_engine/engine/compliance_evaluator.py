# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/engine/compliance_evaluator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Evaluates host profiles against YAML compliance rules with operators (eq, neq, gt, lt, contains)

import os
from typing import Dict, Any, List
from ..rules.loader import RulesLoader
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceEvaluator:
    """
    Evaluates host profiles against compliance rules.
    Supports operators: eq, neq, gt, lt, gte, lte, contains, not_contains, in, not_in
    """
    
    def __init__(self, rules_loader: RulesLoader = None):
        """
        Initialize compliance evaluator.
        
        Args:
            rules_loader: Rules loader instance
        """
        self.rules_loader = rules_loader or RulesLoader()
    
    def _get_field_value(self, profile: Dict[str, Any], field_path: str) -> Any:
        """
        Get field value from profile using dot notation (e.g., 'sysctl.net.ipv4.ip_forward').
        
        Args:
            profile: Host profile dictionary
            field_path: Dot-separated field path
            
        Returns:
            Field value or None
        """
        parts = field_path.split('.')
        value = profile
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list):
                try:
                    index = int(part)
                    value = value[index] if index < len(value) else None
                except ValueError:
                    value = None
            else:
                return None
            
            if value is None:
                return None
        
        return value
    
    def _evaluate_operator(self, actual_value: Any, operator: str, expected_value: Any) -> bool:
        """
        Evaluate operator comparison.
        
        Args:
            actual_value: Actual value from profile
            operator: Operator string (eq, neq, gt, lt, etc.)
            expected_value: Expected value from rule
            
        Returns:
            True if condition passes, False otherwise
        """
        try:
            if operator == 'eq':
                return actual_value == expected_value
            elif operator == 'neq':
                return actual_value != expected_value
            elif operator == 'gt':
                return float(actual_value) > float(expected_value)
            elif operator == 'lt':
                return float(actual_value) < float(expected_value)
            elif operator == 'gte':
                return float(actual_value) >= float(expected_value)
            elif operator == 'lte':
                return float(actual_value) <= float(expected_value)
            elif operator == 'contains':
                if isinstance(actual_value, list):
                    return expected_value in actual_value
                elif isinstance(actual_value, str):
                    return expected_value in actual_value
                else:
                    return False
            elif operator == 'not_contains':
                if isinstance(actual_value, list):
                    return expected_value not in actual_value
                elif isinstance(actual_value, str):
                    return expected_value not in actual_value
                else:
                    return True
            elif operator == 'in':
                if isinstance(expected_value, list):
                    return actual_value in expected_value
                else:
                    return False
            elif operator == 'not_in':
                if isinstance(expected_value, list):
                    return actual_value not in expected_value
                else:
                    return True
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        except Exception as e:
            logger.error(f"Error evaluating operator {operator}: {e}")
            return False
    
    def evaluate_rule(self, rule: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single compliance rule against host profile.
        
        Args:
            rule: Rule dictionary
            profile: Host profile dictionary
            
        Returns:
            Evaluation result dictionary
        """
        rule_id = rule.get('rule_id', 'unknown')
        rule_name = rule.get('rule_name', 'Unknown Rule')
        severity = rule.get('severity', 'low')
        check = rule.get('check', {})
        
        field_path = check.get('field', '')
        operator = check.get('operator', 'eq')
        expected_value = check.get('value')
        
        # Get actual value from profile
        actual_value = self._get_field_value(profile, field_path)
        
        # Evaluate condition
        passed = self._evaluate_operator(actual_value, operator, expected_value)
        
        # Build message
        if passed:
            message = f"Rule '{rule_name}' passed"
        else:
            message = f"Rule '{rule_name}' failed: {field_path} = {actual_value}, expected {operator} {expected_value}"
        
        return {
            'rule_id': rule_id,
            'rule_name': rule_name,
            'severity': severity,
            'passed': passed,
            'actual_value': str(actual_value) if actual_value is not None else None,
            'expected_value': str(expected_value) if expected_value is not None else None,
            'message': message
        }
    
    def evaluate_all_rules(self, profile: Dict[str, Any], policy_name: str = None) -> List[Dict[str, Any]]:
        """
        Evaluate all rules against host profile.
        
        Args:
            profile: Host profile dictionary
            policy_name: Specific policy name, or None for all policies
            
        Returns:
            List of evaluation result dictionaries
        """
        rules = self.rules_loader.get_rules(policy_name)
        
        results = []
        for rule in rules:
            result = self.evaluate_rule(rule, profile)
            results.append(result)
        
        logger.debug(f"Evaluated {len(rules)} rules, {sum(1 for r in results if r['passed'])} passed")
        
        return results
    
    def get_failed_rules_by_severity(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Count failed rules by severity.
        
        Args:
            results: List of evaluation results
            
        Returns:
            Dictionary mapping severity to count of failed rules
        """
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for result in results:
            if not result['passed']:
                severity = result['severity']
                if severity in counts:
                    counts[severity] += 1
        
        return counts

