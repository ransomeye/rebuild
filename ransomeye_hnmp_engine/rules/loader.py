# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/rules/loader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Loads YAML compliance policies from directory with hot-reload support

import os
import yaml
import hashlib
from pathlib import Path
from typing import Dict, List, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolicyFileHandler(FileSystemEventHandler):
    """File system event handler for policy file changes."""
    
    def __init__(self, loader):
        self.loader = loader
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and (event.src_path.endswith('.yaml') or event.src_path.endswith('.yml')):
            logger.info(f"Policy file changed: {event.src_path}")
            self.loader.reload_policies()

class RulesLoader:
    """
    Loads and hot-reloads compliance policies from YAML files.
    """
    
    def __init__(self, policy_dir: str = None):
        """
        Initialize rules loader.
        
        Args:
            policy_dir: Directory containing policy YAML files
        """
        self.policy_dir = policy_dir or os.environ.get('COMPLIANCE_CONFIG', '/home/ransomeye/rebuild/ransomeye_hnmp_engine/policies')
        self.rules: Dict[str, List[Dict[str, Any]]] = {}
        self.rule_file_hashes: Dict[str, str] = {}
        self.lock = threading.Lock()
        self.observer = None
        
        # Create policy directory if it doesn't exist
        Path(self.policy_dir).mkdir(parents=True, exist_ok=True)
        
        # Load initial policies
        self.load_policies()
        
        # Start file watcher for hot-reload
        self._start_watcher()
    
    def _calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA256 hash of file content."""
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def load_policies(self):
        """Load all policy YAML files from directory."""
        with self.lock:
            logger.info(f"Loading policies from: {self.policy_dir}")
            
            policy_path = Path(self.policy_dir)
            if not policy_path.exists():
                logger.warning(f"Policy directory does not exist: {self.policy_dir}")
                return
            
            new_rules = {}
            new_hashes = {}
            
            for yaml_file in policy_path.glob('*.yaml'):
                try:
                    file_hash = self._calculate_file_hash(str(yaml_file))
                    new_hashes[str(yaml_file)] = file_hash
                    
                    # Only reload if file changed
                    if str(yaml_file) in self.rule_file_hashes and self.rule_file_hashes[str(yaml_file)] == file_hash:
                        continue
                    
                    with open(yaml_file, 'r') as f:
                        policy_data = yaml.safe_load(f)
                    
                    if policy_data and 'rules' in policy_data:
                        policy_name = policy_data.get('name', yaml_file.stem)
                        rules = policy_data.get('rules', [])
                        new_rules[policy_name] = rules
                        logger.info(f"Loaded {len(rules)} rules from {yaml_file.name}")
                    
                except Exception as e:
                    logger.error(f"Error loading policy file {yaml_file}: {e}")
            
            # Also check .yml files
            for yaml_file in policy_path.glob('*.yml'):
                try:
                    file_hash = self._calculate_file_hash(str(yaml_file))
                    new_hashes[str(yaml_file)] = file_hash
                    
                    if str(yaml_file) in self.rule_file_hashes and self.rule_file_hashes[str(yaml_file)] == file_hash:
                        continue
                    
                    with open(yaml_file, 'r') as f:
                        policy_data = yaml.safe_load(f)
                    
                    if policy_data and 'rules' in policy_data:
                        policy_name = policy_data.get('name', yaml_file.stem)
                        rules = policy_data.get('rules', [])
                        new_rules[policy_name] = rules
                        logger.info(f"Loaded {len(rules)} rules from {yaml_file.name}")
                    
                except Exception as e:
                    logger.error(f"Error loading policy file {yaml_file}: {e}")
            
            # Update rules and hashes
            if new_rules:
                self.rules.update(new_rules)
                self.rule_file_hashes.update(new_hashes)
                logger.info(f"Total policies loaded: {len(self.rules)}")
    
    def reload_policies(self):
        """Reload policies (called by file watcher)."""
        logger.info("Reloading policies...")
        self.load_policies()
    
    def get_rules(self, policy_name: str = None) -> List[Dict[str, Any]]:
        """
        Get rules for a specific policy or all rules.
        
        Args:
            policy_name: Name of policy, or None for all rules
            
        Returns:
            List of rule dictionaries
        """
        with self.lock:
            if policy_name:
                return self.rules.get(policy_name, [])
            else:
                # Flatten all rules from all policies
                all_rules = []
                for rules in self.rules.values():
                    all_rules.extend(rules)
                return all_rules
    
    def get_all_policies(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all policies.
        
        Returns:
            Dictionary mapping policy names to rule lists
        """
        with self.lock:
            return self.rules.copy()
    
    def _start_watcher(self):
        """Start file system watcher for hot-reload."""
        try:
            policy_path = Path(self.policy_dir)
            if not policy_path.exists():
                return
            
            self.observer = Observer()
            event_handler = PolicyFileHandler(self)
            self.observer.schedule(event_handler, str(policy_path), recursive=False)
            self.observer.start()
            logger.info(f"Started file watcher for policy directory: {self.policy_dir}")
        except Exception as e:
            logger.warning(f"Could not start file watcher: {e}")
    
    def stop_watcher(self):
        """Stop file system watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped file watcher")

