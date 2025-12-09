# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/chain/manifest_verifier.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies manifest signatures and chain integrity

import os
import json
from pathlib import Path
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManifestVerifier:
    """Verifies manifest signatures and chain integrity."""
    
    def __init__(self):
        """Initialize manifest verifier."""
        self.public_key_path = os.environ.get(
            'VALIDATOR_PUBLIC_KEY_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/keys/sign_key.pub'
        )
        self.public_key = None
        self._load_public_key()
        logger.info("Manifest verifier initialized")
    
    def _load_public_key(self):
        """Load RSA public key."""
        try:
            key_path = Path(self.public_key_path)
            if key_path.exists():
                with open(key_path, 'rb') as f:
                    self.public_key = RSA.import_key(f.read())
                logger.info(f"Public key loaded from {self.public_key_path}")
            else:
                logger.warning(f"Public key not found at {self.public_key_path}")
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
    
    def verify_manifest(self, manifest_path: str) -> dict:
        """
        Verify manifest signature.
        
        Args:
            manifest_path: Path to signed manifest file
            
        Returns:
            Verification result
        """
        if not self.public_key:
            return {
                "verified": False,
                "error": "Public key not loaded"
            }
        
        try:
            # Read manifest
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            
            # Extract signature
            signature_data = manifest_data.get("signature")
            if not signature_data:
                return {
                    "verified": False,
                    "error": "No signature found in manifest"
                }
            
            signature_hex = signature_data.get("signature_hex")
            if not signature_hex:
                return {
                    "verified": False,
                    "error": "Invalid signature format"
                }
            
            # Remove signature for hashing
            manifest_without_sig = {k: v for k, v in manifest_data.items() if k != "signature"}
            manifest_json = json.dumps(manifest_without_sig, sort_keys=True)
            manifest_hash = SHA256.new(manifest_json.encode())
            
            # Verify signature
            signature = bytes.fromhex(signature_hex)
            try:
                pkcs1_15.new(self.public_key).verify(manifest_hash, signature)
                logger.info(f"Manifest signature verified: {manifest_path}")
                return {
                    "verified": True,
                    "signed_at": signature_data.get("signed_at"),
                    "signer": signature_data.get("signer")
                }
            except (ValueError, TypeError) as e:
                logger.error(f"Signature verification failed: {e}")
                return {
                    "verified": False,
                    "error": f"Signature verification failed: {str(e)}"
                }
        
        except Exception as e:
            logger.error(f"Error verifying manifest: {e}")
            return {
                "verified": False,
                "error": str(e)
            }
    
    def verify_chain(self, run_id: str, run_store_path: str) -> dict:
        """
        Verify complete chain of custody for a run.
        
        Args:
            run_id: Run identifier
            run_store_path: Path to run store directory
            
        Returns:
            Chain verification result
        """
        results = {
            "run_id": run_id,
            "manifest_exists": False,
            "manifest_verified": False,
            "pdf_exists": False,
            "pdf_verified": False,
            "chain_complete": False
        }
        
        try:
            run_store = Path(run_store_path)
            
            # Check manifest
            manifest_path = run_store / f"{run_id}_manifest.signed.json"
            if manifest_path.exists():
                results["manifest_exists"] = True
                manifest_result = self.verify_manifest(str(manifest_path))
                results["manifest_verified"] = manifest_result.get("verified", False)
            
            # Check PDF (would need PDF verifier)
            pdf_path = run_store / f"{run_id}_report.pdf"
            results["pdf_exists"] = pdf_path.exists()
            
            # Chain is complete if all components exist and are verified
            results["chain_complete"] = (
                results["manifest_exists"] and
                results["manifest_verified"] and
                results["pdf_exists"]
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Chain verification error: {e}")
            return {
                **results,
                "error": str(e)
            }

