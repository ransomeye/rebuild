# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/rules/validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Validates compliance rule schema using jsonschema

import json
import jsonschema
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JSON schema for compliance rules
RULE_SCHEMA = {
    "type": "object",
    "required": ["rule_id", "rule_name", "severity", "check"],
    "properties": {
        "rule_id": {
            "type": "string"
        },
        "rule_name": {
            "type": "string"
        },
        "severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low"]
        },
        "check": {
            "type": "object",
            "required": ["field", "operator", "value"],
            "properties": {
                "field": {
                    "type": "string"
                },
                "operator": {
                    "type": "string",
                    "enum": ["eq", "neq", "gt", "lt", "gte", "lte", "contains", "not_contains", "in", "not_in"]
                },
                "value": {}
            }
        },
        "remediation": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "command": {"type": "string"},
                "script": {"type": "string"}
            }
        },
        "weight": {
            "type": "number",
            "minimum": 0,
            "maximum": 100
        }
    }
}

POLICY_SCHEMA = {
    "type": "object",
    "required": ["name", "rules"],
    "properties": {
        "name": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "rules": {
            "type": "array",
            "items": RULE_SCHEMA
        }
    }
}

class RulesValidator:
    """
    Validates compliance rule schemas using JSON Schema.
    """
    
    def __init__(self):
        """Initialize rules validator."""
        self.rule_schema = RULE_SCHEMA
        self.policy_schema = POLICY_SCHEMA
    
    def validate_rule(self, rule: Dict[str, Any]):
        """
        Validate a single rule.
        
        Args:
            rule: Rule dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            jsonschema.validate(instance=rule, schema=self.rule_schema)
            return True, ""
        except jsonschema.ValidationError as e:
            return False, f"Validation error: {e.message}"
        except Exception as e:
            return False, f"Error validating rule: {str(e)}"
    
    def validate_policy(self, policy: Dict[str, Any]):
        """
        Validate a policy document.
        
        Args:
            policy: Policy dictionary with 'name' and 'rules'
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Validate policy structure
            jsonschema.validate(instance=policy, schema=self.policy_schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Policy structure error: {e.message}")
            return False, errors
        
        # Validate each rule
        rules = policy.get('rules', [])
        for i, rule in enumerate(rules):
            is_valid, error = self.validate_rule(rule)
            if not is_valid:
                errors.append(f"Rule {i} ({rule.get('rule_id', 'unknown')}): {error}")
        
        return len(errors) == 0, errors
    
    def validate_rules_batch(self, rules: List[Dict[str, Any]]):
        """
        Validate a batch of rules.
        
        Args:
            rules: List of rule dictionaries
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for i, rule in enumerate(rules):
            is_valid, error = self.validate_rule(rule)
            if not is_valid:
                errors.append(f"Rule {i} ({rule.get('rule_id', 'unknown')}): {error}")
        
        return len(errors) == 0, errors

