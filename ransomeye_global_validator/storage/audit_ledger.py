# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/storage/audit_ledger.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Signed append-only log of validation runs for audit trail

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditLedger:
    """Signed append-only audit log for validation runs."""
    
    def __init__(self):
        """Initialize audit ledger."""
        self.ledger_path = Path(os.environ.get(
            'VALIDATOR_AUDIT_LEDGER_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/storage/audit_ledger.jsonl'
        ))
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.sign_key_path = os.environ.get(
            'VALIDATOR_SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/keys/sign_key.pem'
        )
        self.private_key = None
        self._load_private_key()
        logger.info("Audit ledger initialized")
    
    def _load_private_key(self):
        """Load RSA private key for signing."""
        try:
            key_path = Path(self.sign_key_path)
            if key_path.exists():
                with open(key_path, 'rb') as f:
                    self.private_key = RSA.import_key(f.read())
                logger.info(f"Private key loaded for audit ledger")
            else:
                logger.warning(f"Signing key not found, audit entries will not be signed")
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
    
    def log_validation_run(self, run_id: str, passed: bool, run_data: Dict[str, Any]):
        """
        Log validation run to audit ledger.
        
        Args:
            run_id: Run identifier
            passed: Whether validation passed
            run_data: Run data dictionary
        """
        entry = {
            "entry_type": "validation_run",
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "passed": passed,
            "summary": run_data.get("summary", {}),
            "scenario_type": run_data.get("scenario_type"),
            "error": run_data.get("error")
        }
        
        # Create hash of entry
        entry_json = json.dumps(entry, sort_keys=True)
        entry_hash = SHA256.new(entry_json.encode()).hexdigest()
        entry["entry_hash_sha256"] = entry_hash
        
        # Sign entry if key available
        if self.private_key:
            try:
                entry_hash_obj = SHA256.new(entry_json.encode())
                signature = pkcs1_15.new(self.private_key).sign(entry_hash_obj)
                entry["signature_hex"] = signature.hex()
            except Exception as e:
                logger.error(f"Failed to sign audit entry: {e}")
        
        # Append to ledger (append-only)
        with open(self.ledger_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        logger.info(f"Audit entry logged: {run_id} (passed: {passed})")
    
    def get_ledger_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve ledger entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of ledger entries
        """
        entries = []
        
        if not self.ledger_path.exists():
            return entries
        
        try:
            with open(self.ledger_path, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines[-limit:]):
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error reading audit ledger: {e}")
        
        return entries
    
    def verify_ledger_integrity(self) -> Dict[str, Any]:
        """
        Verify integrity of audit ledger.
        
        Returns:
            Integrity verification result
        """
        if not self.ledger_path.exists():
            return {
                "verified": False,
                "error": "Ledger file does not exist"
            }
        
        try:
            entries = []
            with open(self.ledger_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        entry = json.loads(line)
                        entries.append((line_num, entry))
            
            # Verify hashes
            verified_count = 0
            for line_num, entry in entries:
                entry_copy = {k: v for k, v in entry.items() 
                            if k not in ['entry_hash_sha256', 'signature_hex']}
                entry_json = json.dumps(entry_copy, sort_keys=True)
                expected_hash = SHA256.new(entry_json.encode()).hexdigest()
                
                if entry.get('entry_hash_sha256') == expected_hash:
                    verified_count += 1
                else:
                    logger.warning(f"Hash mismatch at line {line_num}")
            
            return {
                "verified": verified_count == len(entries),
                "total_entries": len(entries),
                "verified_entries": verified_count
            }
        
        except Exception as e:
            logger.error(f"Ledger integrity check error: {e}")
            return {
                "verified": False,
                "error": str(e)
            }

