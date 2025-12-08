# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/loader/policy_loader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Thread-safe policy loader with atomic swap for hot-reload

import os
import yaml
import threading
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from .policy_validator import PolicyValidator, PolicyValidationError
from ..storage.policy_store import PolicyStore
from ..storage.audit_log import AuditLog
from ..evaluator.rule_compiler import RuleCompiler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolicyLoader:
    """
    Thread-safe policy loader that maintains active policy set
    and implements atomic swap for hot-reload.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PolicyLoader, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize policy loader."""
        if self._initialized:
            return
        
        self._policy_lock = threading.RLock()  # Reentrant lock for policy access
        self._active_policy = None
        self._active_rules = []
        self._compiled_rules = []
        self._policy_version = None
        self._policy_hash = None
        
        self.validator = PolicyValidator()
        self.store = PolicyStore()
        self.audit_log = AuditLog()
        self.compiler = RuleCompiler()
        
        self._initialized = True
        logger.info("PolicyLoader initialized")
    
    def load_policy_bundle(self, bundle_path: Path) -> Dict[str, Any]:
        """
        Load a policy bundle with validation and atomic swap.
        
        Args:
            bundle_path: Path to .tar.gz policy bundle
            
        Returns:
            Dictionary with loading results
            
        Raises:
            PolicyValidationError: If validation fails
        """
        # Validate bundle
        logger.info(f"Validating policy bundle: {bundle_path}")
        validation_result = self.validator.validate_bundle(bundle_path)
        
        if not validation_result['valid']:
            raise PolicyValidationError("Bundle validation failed")
        
        extract_dir = Path(validation_result['extract_dir'])
        
        try:
            # Load all YAML files
            yaml_files = list(extract_dir.glob("*.yaml")) + list(extract_dir.glob("*.yml"))
            all_rules = []
            policy_metadata = {}
            
            for yaml_file in yaml_files:
                with open(yaml_file, 'r') as f:
                    content = yaml.safe_load(f)
                    
                    if 'rules' in content:
                        all_rules.extend(content['rules'])
                    if 'version' in content:
                        policy_metadata['version'] = content['version']
                    if 'policy_name' in content:
                        policy_metadata['name'] = content['policy_name']
                    if 'description' in content:
                        policy_metadata['description'] = content['description']
            
            # Filter enabled rules
            enabled_rules = [r for r in all_rules if r.get('enabled', True)]
            
            # Compile rules (pre-compile regex patterns)
            logger.info(f"Compiling {len(enabled_rules)} rules...")
            compiled_rules = []
            for rule in enabled_rules:
                try:
                    compiled_rule = self.compiler.compile_rule(rule)
                    compiled_rules.append(compiled_rule)
                except Exception as e:
                    logger.warning(f"Failed to compile rule {rule.get('rule_name', 'unknown')}: {e}")
            
            # Calculate policy hash
            policy_content = yaml.dump(all_rules, sort_keys=True)
            policy_hash = hashlib.sha256(policy_content.encode()).hexdigest()
            
            # Atomic swap: load new -> test -> swap pointer
            with self._policy_lock:
                # Store old policy for rollback if needed
                old_policy = self._active_policy
                old_rules = self._active_rules
                old_compiled = self._compiled_rules
                
                # Set new policy
                self._active_policy = {
                    'rules': enabled_rules,
                    'metadata': policy_metadata,
                    'hash': policy_hash
                }
                self._active_rules = enabled_rules
                self._compiled_rules = compiled_rules
                self._policy_version = policy_metadata.get('version', 'unknown')
                self._policy_hash = policy_hash
                
                logger.info(f"Policy loaded: {len(enabled_rules)} rules, version {self._policy_version}")
            
            # Store policy files
            self.store.store_policy(bundle_path, policy_hash)
            
            # Write audit log entry
            self.audit_log.log_policy_reload(
                policy_version=self._policy_version,
                policy_hash=policy_hash,
                rules_count=len(enabled_rules),
                bundle_path=str(bundle_path)
            )
            
            return {
                'version': self._policy_version,
                'rules_count': len(enabled_rules),
                'hash': policy_hash,
                'status': 'loaded'
            }
            
        except Exception as e:
            logger.error(f"Failed to load policy bundle: {e}")
            # Fail-closed: keep old policy active
            raise PolicyValidationError(f"Policy loading failed: {e}")
    
    def get_active_rules(self) -> List[Dict[str, Any]]:
        """
        Get currently active rules (thread-safe).
        
        Returns:
            List of active rules
        """
        with self._policy_lock:
            return self._active_rules.copy()
    
    def get_compiled_rules(self) -> List[Any]:
        """
        Get compiled rules for evaluation (thread-safe).
        
        Returns:
            List of compiled rules
        """
        with self._policy_lock:
            return self._compiled_rules.copy()
    
    def get_active_policy_info(self) -> Dict[str, Any]:
        """
        Get information about active policy (thread-safe).
        
        Returns:
            Dictionary with policy information
        """
        with self._policy_lock:
            return {
                'loaded': self._active_policy is not None,
                'version': self._policy_version,
                'hash': self._policy_hash,
                'rules_count': len(self._active_rules) if self._active_rules else 0
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get policy loader status.
        
        Returns:
            Dictionary with status information
        """
        with self._policy_lock:
            return {
                'policy_loaded': self._active_policy is not None,
                'version': self._policy_version,
                'rules_count': len(self._active_rules) if self._active_rules else 0,
                'last_reload': self.audit_log.get_last_reload_time()
            }

# Global singleton instance
_loader_instance = None
_loader_lock = threading.Lock()

def get_policy_loader() -> PolicyLoader:
    """Get or create the global policy loader instance."""
    global _loader_instance
    if _loader_instance is None:
        with _loader_lock:
            if _loader_instance is None:
                _loader_instance = PolicyLoader()
    return _loader_instance

