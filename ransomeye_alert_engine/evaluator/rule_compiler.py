# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/evaluator/rule_compiler.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Pre-compiles regex patterns from YAML rules for performance optimization

import re
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompiledRule:
    """Container for compiled rule with pre-compiled regex patterns."""
    
    def __init__(self, rule: Dict[str, Any]):
        """
        Initialize compiled rule.
        
        Args:
            rule: Original rule dictionary
        """
        self.rule_name = rule.get('rule_name', 'unknown')
        self.severity = rule.get('severity', 'medium')
        self.action = rule.get('action', 'log_only')
        self.condition = rule.get('condition', {})
        self.description = rule.get('description', '')
        self.metadata = rule.get('metadata', {})
        
        # Pre-compile regex patterns
        self.compiled_pattern = None
        self.condition_type = self.condition.get('type', 'match')
        self.field = self.condition.get('field', '')
        self.value = self.condition.get('value')
        self.pattern = self.condition.get('pattern', '')
        self.min_value = self.condition.get('min')
        self.max_value = self.condition.get('max')
        
        # Compile regex if pattern is provided
        if self.condition_type == 'regex' and self.pattern:
            try:
                self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
                logger.debug(f"Compiled regex pattern for rule: {self.rule_name}")
            except re.error as e:
                logger.error(f"Invalid regex pattern in rule {self.rule_name}: {e}")
                self.compiled_pattern = None

class RuleCompiler:
    """Compiles rules by pre-compiling regex patterns for performance."""
    
    def compile_rule(self, rule: Dict[str, Any]) -> CompiledRule:
        """
        Compile a rule by pre-compiling regex patterns.
        
        Args:
            rule: Rule dictionary from YAML
            
        Returns:
            CompiledRule object
        """
        return CompiledRule(rule)
    
    def compile_rules(self, rules: list) -> list:
        """
        Compile multiple rules.
        
        Args:
            rules: List of rule dictionaries
            
        Returns:
            List of CompiledRule objects
        """
        compiled = []
        for rule in rules:
            try:
                compiled_rule = self.compile_rule(rule)
                compiled.append(compiled_rule)
            except Exception as e:
                logger.error(f"Failed to compile rule {rule.get('rule_name', 'unknown')}: {e}")
        return compiled

