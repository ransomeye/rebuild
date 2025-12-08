# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/audit/audit_log.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signed append-only log of playbook executions

import os
import json
import hashlib
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditLog:
    """
    Signed append-only audit log for playbook executions.
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
            '/home/ransomeye/rebuild/ransomeye_response/storage/audit_log.jsonl'
        ))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.private_key_path = Path(private_key_path or os.environ.get(
            'AUDIT_SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/certs/audit_sign_private.pem'
        ))
        self.private_key = self._load_or_generate_key()
        
        self.last_hash = self._get_last_hash()
    
    def _load_or_generate_key(self):
        """Load or generate RSA private key."""
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
        
        # Generate new key (RSA-4096)
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
    
    def _get_last_hash(self) -> Optional[str]:
        """Get hash of last entry in log."""
        if not self.log_path.exists():
            return None
        
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    for line in reversed(lines):
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            return entry.get('entry_hash')
        except Exception:
            pass
        
        return None
    
    def _calculate_entry_hash(self, entry_data: Dict[str, Any], prev_hash: Optional[str]) -> str:
        """Calculate hash for audit entry."""
        entry_content = json.dumps(entry_data, sort_keys=True).encode()
        combined = (prev_hash or b'').encode() + entry_content
        return hashlib.sha256(combined).hexdigest()
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (playbook_uploaded, playbook_executed, etc.)
            data: Event data
        """
        entry_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': event_type,
            'data': data
        }
        
        # Calculate hash
        prev_hash = self.last_hash
        entry_hash = self._calculate_entry_hash(entry_data, prev_hash)
        
        # Sign entry
        entry_content = json.dumps(entry_data, sort_keys=True).encode()
        signature = self.private_key.sign(
            entry_content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Create entry
        entry = {
            'prev_hash': prev_hash,
            'entry_hash': entry_hash,
            'signature': signature_b64,
            **entry_data
        }
        
        # Append to log
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        self.last_hash = entry_hash
        logger.info(f"Audit event logged: {event_type}")
    
    def get_entries(self, limit: Optional[int] = None, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get audit log entries.
        
        Args:
            limit: Maximum number of entries to return
            event_type: Filter by event type
            
        Returns:
            List of audit entries
        """
        if not self.log_path.exists():
            return []
        
        entries = []
        
        try:
            with open(self.log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        if not event_type or entry.get('event_type') == event_type:
                            entries.append(entry)
            
            # Return most recent first
            entries.reverse()
            
            if limit:
                entries = entries[:limit]
            
            return entries
            
        except Exception as e:
            logger.error(f"Error reading audit log: {e}")
            return []

