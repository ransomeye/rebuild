# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/dna/yara_wrapper.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper for yara-python to load and apply YARA rules for malware detection

import os
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import yara, but handle gracefully if not available
try:
    import yara
    YARA_AVAILABLE = True
except ImportError:
    YARA_AVAILABLE = False
    logger.warning("yara-python not available. YARA scanning will be disabled.")


class YARAWrapper:
    """
    Wrapper for yara-python library.
    Loads YARA rules and applies them to artifacts.
    """
    
    def __init__(self, rules_dir: Optional[str] = None):
        """
        Initialize YARA wrapper.
        
        Args:
            rules_dir: Directory containing YARA rule files (.yar)
        """
        if not YARA_AVAILABLE:
            logger.warning("YARA not available. Install yara-python: pip install yara-python")
            self.rules = None
            self.rules_dir = None
            return
        
        if rules_dir is None:
            rules_dir = os.environ.get(
                'YARA_RULES_DIR',
                '/home/ransomeye/rebuild/ransomeye_forensic/rules/yara'
            )
        
        self.rules_dir = Path(rules_dir)
        self.rules = self._load_rules()
    
    def _load_rules(self):
        """
        Load YARA rules from directory.
        
        Returns:
            Compiled YARA rules object, or None if unavailable
        """
        if not YARA_AVAILABLE:
            return None
        
        if not self.rules_dir.exists():
            logger.warning(f"YARA rules directory not found: {self.rules_dir}")
            # Create directory for future rule files
            self.rules_dir.mkdir(parents=True, exist_ok=True)
            return None
        
        # Find all .yar and .yara files
        rule_files = list(self.rules_dir.glob('*.yar')) + list(self.rules_dir.glob('*.yara'))
        
        if not rule_files:
            logger.warning(f"No YARA rule files found in {self.rules_dir}")
            return None
        
        try:
            # Compile rules
            rules_dict = {}
            for rule_file in rule_files:
                rules_dict[str(rule_file)] = str(rule_file)
            
            compiled_rules = yara.compile(filepaths=rules_dict)
            logger.info(f"Loaded {len(rule_files)} YARA rule files")
            return compiled_rules
        
        except yara.Error as e:
            logger.error(f"Error compiling YARA rules: {e}")
            return None
    
    def scan_file(self, file_path: str) -> List[Dict]:
        """
        Scan file with YARA rules.
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            List of match dictionaries
        """
        if not YARA_AVAILABLE or self.rules is None:
            return []
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.warning(f"File not found for YARA scan: {file_path}")
            return []
        
        try:
            matches = self.rules.match(str(file_path_obj))
            
            results = []
            for match in matches:
                results.append({
                    'rule': match.rule,
                    'tags': match.tags,
                    'meta': match.meta,
                    'strings': [
                        {
                            'identifier': s.identifier,
                            'offset': s.offset,
                            'data': s.strings[0] if s.strings else None
                        }
                        for s in match.strings
                    ],
                    'namespace': match.namespace
                })
            
            if results:
                logger.info(f"YARA scan found {len(results)} matches in {file_path}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error scanning file with YARA: {e}")
            return []
    
    def scan_data(self, data: bytes) -> List[Dict]:
        """
        Scan byte data with YARA rules.
        
        Args:
            data: Byte data to scan
            
        Returns:
            List of match dictionaries
        """
        if not YARA_AVAILABLE or self.rules is None:
            return []
        
        try:
            matches = self.rules.match(data=data)
            
            results = []
            for match in matches:
                results.append({
                    'rule': match.rule,
                    'tags': match.tags,
                    'meta': match.meta,
                    'strings': [
                        {
                            'identifier': s.identifier,
                            'offset': s.offset,
                            'data': s.strings[0] if s.strings else None
                        }
                        for s in match.strings
                    ],
                    'namespace': match.namespace
                })
            
            return results
        
        except Exception as e:
            logger.error(f"Error scanning data with YARA: {e}")
            return []
    
    def reload_rules(self) -> bool:
        """
        Reload YARA rules from directory.
        
        Returns:
            True if reload successful
        """
        self.rules = self._load_rules()
        return self.rules is not None
    
    def get_rule_count(self) -> int:
        """
        Get number of loaded rules.
        
        Returns:
            Number of rules, or 0 if unavailable
        """
        if not YARA_AVAILABLE or self.rules is None:
            return 0
        
        # YARA doesn't expose rule count directly, estimate from rules_dir
        if self.rules_dir and self.rules_dir.exists():
            rule_files = list(self.rules_dir.glob('*.yar')) + list(self.rules_dir.glob('*.yara'))
            return len(rule_files)
        
        return 0

