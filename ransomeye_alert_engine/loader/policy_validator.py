# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/loader/policy_validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Policy bundle validation with RSA-4096 signature verification and YAML schema validation

import os
import json
import yaml
import hashlib
import shutil
import tempfile
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import jsonschema
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolicyValidationError(Exception):
    """Custom exception for policy validation errors."""
    pass

class PolicyValidator:
    """Validates policy bundles with signature and schema verification."""
    
    def __init__(self, verify_key_path: str = None, schema_path: str = None):
        """
        Initialize validator.
        
        Args:
            verify_key_path: Path to RSA public key for signature verification
            schema_path: Path to policy schema YAML file
        """
        self.verify_key_path = verify_key_path or os.environ.get(
            'POLICY_VERIFY_KEY_PATH',
            '/home/ransomeye/rebuild/certs/policy_verify_public.pem'
        )
        self.schema_path = schema_path or os.environ.get(
            'POLICY_SCHEMA_PATH',
            '/home/ransomeye/rebuild/ransomeye_alert_engine/config/policy_schema.yaml'
        )
        self.public_key = None
        self.schema = None
        self._load_public_key()
        self._load_schema()
    
    def _load_public_key(self):
        """Load RSA public key for signature verification."""
        if not os.path.exists(self.verify_key_path):
            logger.warning(f"Public key not found at {self.verify_key_path}, signature verification will fail")
            return
        
        try:
            with open(self.verify_key_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.info(f"Loaded public key from {self.verify_key_path}")
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
            raise PolicyValidationError(f"Failed to load public key: {e}")
    
    def _load_schema(self):
        """Load policy schema for validation."""
        if not os.path.exists(self.schema_path):
            logger.warning(f"Schema file not found at {self.schema_path}, schema validation will be skipped")
            return
        
        try:
            with open(self.schema_path, 'r') as f:
                self.schema = yaml.safe_load(f)
            logger.info(f"Loaded policy schema from {self.schema_path}")
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            raise PolicyValidationError(f"Failed to load schema: {e}")
    
    def verify_signature(self, manifest_path: Path, signature_path: Path) -> bool:
        """
        Verify RSA signature of manifest.json.
        
        Args:
            manifest_path: Path to manifest.json
            signature_path: Path to manifest.sig
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.public_key:
            raise PolicyValidationError("Public key not loaded, cannot verify signature")
        
        if not manifest_path.exists():
            raise PolicyValidationError(f"Manifest file not found: {manifest_path}")
        
        if not signature_path.exists():
            raise PolicyValidationError(f"Signature file not found: {signature_path}")
        
        try:
            # Read manifest content
            with open(manifest_path, 'rb') as f:
                manifest_content = f.read()
            
            # Read signature
            import base64
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
                logger.info("Signature verification successful")
                return True
            except Exception as e:
                logger.error(f"Signature verification failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error during signature verification: {e}")
            raise PolicyValidationError(f"Signature verification error: {e}")
    
    def validate_yaml_schema(self, yaml_path: Path) -> bool:
        """
        Validate YAML file against policy schema.
        
        Args:
            yaml_path: Path to YAML file
            
        Returns:
            True if valid, False otherwise
        """
        if not self.schema:
            logger.warning("Schema not loaded, skipping schema validation")
            return True
        
        try:
            with open(yaml_path, 'r') as f:
                yaml_content = yaml.safe_load(f)
            
            # Validate against schema
            jsonschema.validate(instance=yaml_content, schema=self.schema)
            logger.debug(f"Schema validation passed for {yaml_path}")
            return True
            
        except jsonschema.ValidationError as e:
            logger.error(f"Schema validation failed for {yaml_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating schema: {e}")
            return False
    
    def validate_bundle(self, bundle_path: Path, extract_to: Path = None) -> dict:
        """
        Validate a policy bundle: extract, verify signature, validate YAML files.
        
        Args:
            bundle_path: Path to .tar.gz bundle
            extract_to: Directory to extract to (creates temp dir if not provided)
            
        Returns:
            Dictionary with validation results and extracted path
            
        Raises:
            PolicyValidationError: If validation fails
        """
        import tarfile
        
        if not bundle_path.exists():
            raise PolicyValidationError(f"Bundle file not found: {bundle_path}")
        
        # Create temporary extraction directory if not provided
        temp_dir = None
        if extract_to is None:
            temp_dir = tempfile.mkdtemp(prefix='policy_validation_')
            extract_to = Path(temp_dir)
        else:
            extract_to = Path(extract_to)
            extract_to.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Validating policy bundle: {bundle_path}")
            
            # Extract bundle
            logger.info(f"Extracting bundle to {extract_to}")
            with tarfile.open(bundle_path, 'r:gz') as tar:
                tar.extractall(extract_to)
            
            # Find manifest.json and manifest.sig
            manifest_path = extract_to / "manifest.json"
            signature_path = extract_to / "manifest.sig"
            
            if not manifest_path.exists():
                raise PolicyValidationError("manifest.json not found in bundle")
            
            if not signature_path.exists():
                raise PolicyValidationError("manifest.sig not found in bundle - signature verification required")
            
            # Load manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Verify signature
            logger.info("Verifying signature...")
            if not self.verify_signature(manifest_path, signature_path):
                raise PolicyValidationError("Signature verification failed - bundle is not authentic")
            
            # Validate all YAML files
            logger.info("Validating YAML files against schema...")
            yaml_files = list(extract_to.glob("*.yaml")) + list(extract_to.glob("*.yml"))
            all_valid = True
            
            for yaml_file in yaml_files:
                if yaml_file.name in ['manifest.json', 'manifest.sig']:
                    continue
                if not self.validate_yaml_schema(yaml_file):
                    all_valid = False
            
            if not all_valid:
                raise PolicyValidationError("YAML schema validation failed - one or more files are invalid")
            
            logger.info("Policy bundle validation successful")
            
            return {
                'valid': True,
                'extract_dir': str(extract_to),
                'manifest': manifest,
                'yaml_files': [str(f) for f in yaml_files],
                'temp_dir': temp_dir is not None
            }
            
        except Exception as e:
            # Clean up on failure (fail-closed)
            if temp_dir and Path(temp_dir).exists():
                logger.info(f"Cleaning up temporary directory: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            if isinstance(e, PolicyValidationError):
                raise
            else:
                raise PolicyValidationError(f"Validation error: {e}")

