# Path and File Name : /home/ransomeye/rebuild/ransomeye_alert_engine/storage/audit_log.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signed audit logging with Merkle-chain style hashing for immutable policy change history

import os
import json
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditLog:
    """
    Signed audit log with Merkle-chain style hashing.
    Each entry includes hash of previous entry for immutability.
    """
    
    def __init__(self, log_path: str = None, private_key_path: str = None):
        """
        Initialize audit log.
        
        Args:
            log_path: Path to audit log file
            private_key_path: Path to RSA private key for signing
        """
        self.log_path = Path(log_path or os.environ.get(
            'AUDIT_LOG_PATH',
            '/home/ransomeye/rebuild/ransomeye_alert_engine/storage/audit.log'
        ))
        self.private_key_path = Path(private_key_path or os.environ.get(
            'AUDIT_SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/certs/audit_sign_private.pem'
        ))
        
        # Create log file if it doesn't exist
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or generate private key
        self.private_key = self._load_or_generate_key()
        
        # Get previous entry hash
        self.previous_hash = self._get_last_entry_hash()
    
    def _load_or_generate_key(self):
        """Load or generate RSA private key for signing."""
        if self.private_key_path.exists():
            try:
                with open(self.private_key_path, 'rb') as f:
                    return serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                        backend=default_backend()
                    )
            except Exception as e:
                logger.warning(f"Failed to load private key: {e}, generating new key")
        
        # Generate new key (RSA-4096 for consistency with policy signing)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        
        # Save private key
        self.private_key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        os.chmod(self.private_key_path, 0o600)
        
        logger.info(f"Generated new audit signing key: {self.private_key_path}")
        return private_key
    
    def _get_last_entry_hash(self) -> Optional[str]:
        """Get hash of last entry in audit log."""
        if not self.log_path.exists():
            return None
        
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    # Get last line
                    last_line = lines[-1].strip()
                    if last_line:
                        entry = json.loads(last_line)
                        return entry.get('entry_hash')
        except Exception as e:
            logger.warning(f"Error reading last entry hash: {e}")
        
        return None
    
    def _sign_entry(self, entry_content: bytes) -> str:
        """
        Sign audit log entry.
        
        Args:
            entry_content: Entry content to sign
            
        Returns:
            Base64-encoded signature
        """
        signature = self.private_key.sign(
            entry_content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    
    def log_policy_reload(self, policy_version: str, policy_hash: str,
                         rules_count: int, bundle_path: str,
                         changed_by: str = "system") -> str:
        """
        Log a policy reload event with signature.
        
        Args:
            policy_version: Policy version
            policy_hash: Policy hash
            rules_count: Number of rules
            bundle_path: Path to bundle
            changed_by: User who changed the policy
            
        Returns:
            Entry hash
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Create entry
        entry = {
            'timestamp': timestamp,
            'event_type': 'policy_reload',
            'policy_version': policy_version,
            'policy_hash': policy_hash,
            'rules_count': rules_count,
            'bundle_path': bundle_path,
            'changed_by': changed_by,
            'previous_hash': self.previous_hash
        }
        
        # Calculate entry hash (Merkle-chain: hash of entry + previous hash)
        entry_content = json.dumps(entry, sort_keys=True).encode()
        combined = (self.previous_hash or b'').encode() + entry_content
        entry_hash = hashlib.sha256(combined).hexdigest()
        entry['entry_hash'] = entry_hash
        
        # Sign entry
        entry_signature = self._sign_entry(entry_content)
        entry['signature'] = entry_signature
        
        # Append to log file
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Update previous hash
        self.previous_hash = entry_hash
        
        logger.info(f"Audit log entry written: {entry_hash[:16]}...")
        return entry_hash
    
    def get_last_reload_time(self) -> Optional[str]:
        """
        Get timestamp of last policy reload.
        
        Returns:
            Timestamp or None
        """
        if not self.log_path.exists():
            return None
        
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if line.strip():
                        entry = json.loads(line)
                        if entry.get('event_type') == 'policy_reload':
                            return entry.get('timestamp')
        except Exception as e:
            logger.warning(f"Error reading audit log: {e}")
        
        return None
    
    def verify_log_integrity(self) -> bool:
        """
        Verify integrity of audit log (check Merkle-chain).
        
        Returns:
            True if log is valid, False otherwise
        """
        if not self.log_path.exists():
            return True
        
        try:
            previous_hash = None
            with open(self.log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    entry_hash = entry.get('entry_hash')
                    entry_previous = entry.get('previous_hash')
                    
                    # Verify previous hash matches
                    if entry_previous != previous_hash:
                        logger.error(f"Audit log integrity check failed at line {line_num}: hash mismatch")
                        return False
                    
                    # Verify entry hash
                    entry_content = json.dumps({k: v for k, v in entry.items() if k not in ['entry_hash', 'signature']}, sort_keys=True).encode()
                    combined = (previous_hash or b'').encode() + entry_content
                    calculated_hash = hashlib.sha256(combined).hexdigest()
                    
                    if calculated_hash != entry_hash:
                        logger.error(f"Audit log integrity check failed at line {line_num}: hash mismatch")
                        return False
                    
                    previous_hash = entry_hash
            
            logger.info("Audit log integrity check passed")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying audit log: {e}")
            return False

