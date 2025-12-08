# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/validator/validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Validates playbook signatures, checks for IP literals, and validates schema

import os
import re
import json
import base64
import tarfile
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import jsonschema
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaybookValidator:
    """
    Validates playbooks for security and compliance.
    """
    
    def __init__(self, public_key_path: str = None):
        """
        Initialize validator.
        
        Args:
            public_key_path: Path to RSA public key for signature verification
        """
        self.public_key_path = Path(public_key_path or os.environ.get(
            'PLAYBOOK_VERIFY_KEY_PATH',
            '/home/ransomeye/rebuild/certs/playbook_verify_public.pem'
        ))
        self.public_key = self._load_public_key()
        
        # Load schema
        schema_path = Path(__file__).parent.parent / "registry" / "playbook_metadata_schema.json"
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
        
        # IP regex patterns (IPv4 and IPv6)
        self.ipv4_pattern = re.compile(
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        )
        self.ipv6_pattern = re.compile(
            r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|'
            r'\b::1\b|'
            r'\b::ffff:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        )
    
    def _load_public_key(self):
        """Load RSA public key."""
        if not self.public_key_path.exists():
            logger.warning(f"Public key not found: {self.public_key_path}")
            return None
        
        try:
            with open(self.public_key_path, 'rb') as f:
                return serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
            return None
    
    def validate_bundle(self, bundle_path: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate a playbook bundle.
        
        Args:
            bundle_path: Path to playbook bundle (.tar.gz)
            
        Returns:
            Tuple of (is_valid, errors, metadata)
        """
        errors = []
        metadata = {}
        
        try:
            # Extract bundle
            temp_dir = Path(f"/tmp/playbook_validate_{bundle_path.stem}")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                with tarfile.open(bundle_path, 'r:gz') as tar:
                    tar.extractall(temp_dir)
                
                # Check for manifest.json and manifest.sig
                manifest_path = temp_dir / "manifest.json"
                signature_path = temp_dir / "manifest.sig"
                
                if not manifest_path.exists():
                    errors.append("manifest.json not found in bundle")
                    return False, errors, metadata
                
                if not signature_path.exists():
                    errors.append("manifest.sig not found in bundle")
                    return False, errors, metadata
                
                # Verify signature
                if not self.verify_signature(manifest_path, signature_path):
                    errors.append("Playbook signature verification failed")
                    return False, errors, metadata
                
                # Load manifest
                with open(manifest_path, 'r') as f:
                    metadata = json.load(f)
                
                # Find playbook YAML
                playbook_yaml_path = None
                for yaml_file in temp_dir.glob("*.yaml"):
                    playbook_yaml_path = yaml_file
                    break
                for yaml_file in temp_dir.glob("*.yml"):
                    playbook_yaml_path = yaml_file
                    break
                
                if not playbook_yaml_path:
                    errors.append("Playbook YAML file not found in bundle")
                    return False, errors, metadata
                
                # Validate YAML content
                yaml_errors = self.validate_yaml_content(playbook_yaml_path)
                if yaml_errors:
                    errors.extend(yaml_errors)
                
                # Validate schema
                schema_errors = self.validate_schema(metadata)
                if schema_errors:
                    errors.extend(schema_errors)
                
                return len(errors) == 0, errors, metadata
                
            finally:
                # Cleanup
                if temp_dir.exists():
                    import shutil
                    shutil.rmtree(temp_dir)
                    
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            logger.error(f"Bundle validation failed: {e}", exc_info=True)
            return False, errors, metadata
    
    def verify_signature(self, manifest_path: Path, signature_path: Path) -> bool:
        """
        Verify playbook manifest signature.
        
        Args:
            manifest_path: Path to manifest.json
            signature_path: Path to manifest.sig
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.public_key:
            logger.error("Public key not loaded, cannot verify signature")
            return False
        
        try:
            # Read manifest content
            with open(manifest_path, 'rb') as f:
                manifest_content = f.read()
            
            # Read signature
            with open(signature_path, 'r') as f:
                signature_b64 = f.read().strip()
                signature = base64.b64decode(signature_b64)
            
            # Verify signature
            try:
                self.public_key.verify(
                    signature,
                    manifest_content,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                logger.info("✓ Playbook signature verified")
                return True
            except InvalidSignature:
                logger.error("✗ Playbook signature is invalid")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False
    
    def validate_yaml_content(self, yaml_path: Path) -> List[str]:
        """
        Validate YAML content for IP literals and other security issues.
        
        Args:
            yaml_path: Path to playbook YAML file
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        try:
            # Read YAML content as text to check for IPs
            with open(yaml_path, 'r') as f:
                yaml_content = f.read()
            
            # Check for IP addresses
            ipv4_matches = self.ipv4_pattern.findall(yaml_content)
            ipv6_matches = self.ipv6_pattern.findall(yaml_content)
            
            if ipv4_matches:
                errors.append(f"IP literal detected (IPv4): {ipv4_matches[0]}. Playbooks must use tags or agent_id, not IP addresses.")
            
            if ipv6_matches:
                errors.append(f"IP literal detected (IPv6): {ipv6_matches[0]}. Playbooks must use tags or agent_id, not IP addresses.")
            
            # Parse YAML to validate structure
            with open(yaml_path, 'r') as f:
                playbook_data = yaml.safe_load(f)
            
            # Validate that targets use tags or agent_id, not IPs
            if isinstance(playbook_data, dict) and 'steps' in playbook_data:
                for step in playbook_data['steps']:
                    if 'target' in step:
                        target = step['target']
                        if isinstance(target, dict):
                            # Check if target contains IP-like strings
                            target_str = json.dumps(target)
                            if self.ipv4_pattern.search(target_str) or self.ipv6_pattern.search(target_str):
                                errors.append(f"Step '{step.get('id', 'unknown')}' target contains IP literal. Use tags or agent_id instead.")
                            
                            # Validate target structure
                            if 'agent_id' not in target and 'tags' not in target:
                                errors.append(f"Step '{step.get('id', 'unknown')}' target must specify either 'agent_id' or 'tags'")
            
            return errors
            
        except Exception as e:
            errors.append(f"Error validating YAML content: {str(e)}")
            return errors
    
    def validate_schema(self, metadata: Dict[str, Any]) -> List[str]:
        """
        Validate metadata against JSON schema.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        try:
            jsonschema.validate(instance=metadata, schema=self.schema)
            logger.info("✓ Playbook metadata schema validation passed")
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")
        
        return errors

