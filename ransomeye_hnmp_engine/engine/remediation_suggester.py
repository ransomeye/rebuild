# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/engine/remediation_suggester.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Maps failed compliance rules to remediation scripts and commands

from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RemediationSuggester:
    """
    Maps failed compliance rules to remediation suggestions.
    """
    
    def __init__(self):
        """Initialize remediation suggester."""
        pass
    
    def get_remediation_for_rule(self, rule: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get remediation suggestion for a failed rule.
        
        Args:
            rule: Rule dictionary (may contain remediation field)
            result: Evaluation result dictionary
            
        Returns:
            Remediation dictionary with description, command, script
        """
        # Check if rule has remediation defined
        remediation = rule.get('remediation', {})
        
        if remediation:
            return {
                'rule_id': result['rule_id'],
                'rule_name': result['rule_name'],
                'description': remediation.get('description', ''),
                'command': remediation.get('command', ''),
                'script': remediation.get('script', ''),
                'severity': result['severity']
            }
        
        # Generate generic remediation based on rule
        return self._generate_generic_remediation(result)
    
    def _generate_generic_remediation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate generic remediation suggestion.
        
        Args:
            result: Evaluation result dictionary
            
        Returns:
            Generic remediation dictionary
        """
        rule_name = result['rule_name']
        field = result.get('actual_value')
        expected = result.get('expected_value')
        
        # Generic suggestions based on common patterns
        description = f"Review and fix compliance issue: {rule_name}"
        command = ""
        script = ""
        
        # Try to infer command based on field names
        if 'sysctl' in rule_name.lower():
            description = f"Update sysctl setting: {rule_name}"
            if field and expected:
                command = f"sysctl -w {field}={expected}"
        
        return {
            'rule_id': result['rule_id'],
            'rule_name': result['rule_name'],
            'description': description,
            'command': command,
            'script': script,
            'severity': result['severity'],
            'generic': True
        }
    
    def get_remediations_for_failures(self, rules: List[Dict[str, Any]], 
                                     results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get remediation suggestions for all failed rules.
        
        Args:
            rules: List of rule dictionaries
            results: List of evaluation result dictionaries
            
        Returns:
            List of remediation dictionaries
        """
        # Create rule lookup by ID
        rule_lookup = {rule['rule_id']: rule for rule in rules}
        
        remediations = []
        for result in results:
            if not result['passed']:
                rule = rule_lookup.get(result['rule_id'], {})
                remediation = self.get_remediation_for_rule(rule, result)
                remediations.append(remediation)
        
        return remediations
    
    def prioritize_remediations(self, remediations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort remediations by severity (critical first).
        
        Args:
            remediations: List of remediation dictionaries
            
        Returns:
            Sorted list of remediations
        """
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        
        return sorted(
            remediations,
            key=lambda r: severity_order.get(r.get('severity', 'low'), 3)
        )

