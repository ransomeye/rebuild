# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/transport/signed_receipt_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Local store for verified cryptographic receipts from server

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)


class SignedReceiptStore:
    """Store and verify signed receipts from server."""
    
    def __init__(self, store_dir: str, server_public_key_path: str):
        """
        Initialize receipt store.
        
        Args:
            store_dir: Directory to store receipts
            server_public_key_path: Path to server's public key for verification
        """
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        self.server_public_key_path = Path(server_public_key_path)
        self.server_public_key = None
        
        if self.server_public_key_path.exists():
            try:
                with open(self.server_public_key_path, 'rb') as f:
                    self.server_public_key = serialization.load_pem_public_key(f.read())
                logger.info(f"Loaded server public key from {self.server_public_key_path}")
            except Exception as e:
                logger.error(f"Error loading server public key: {e}")
        else:
            logger.warning(f"Server public key not found: {self.server_public_key_path}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of SHA256 hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def verify_receipt(self, receipt: Dict[str, Any], file_path: str) -> bool:
        """
        Verify signed receipt matches uploaded file.
        
        Args:
            receipt: Receipt dictionary from server
            file_path: Path to uploaded file
            
        Returns:
            True if receipt is valid, False otherwise
        """
        if self.server_public_key is None:
            logger.error("Server public key not available, cannot verify receipt")
            return False
        
        try:
            # Extract receipt components
            file_hash = receipt.get('file_hash')
            file_size = receipt.get('file_size')
            upload_id = receipt.get('upload_id')
            timestamp = receipt.get('timestamp')
            signature = receipt.get('signature')
            
            if not all([file_hash, file_size, upload_id, timestamp, signature]):
                logger.error("Receipt missing required fields")
                return False
            
            # Verify file hash matches
            actual_hash = self._calculate_file_hash(file_path)
            if actual_hash != file_hash:
                logger.error(f"File hash mismatch: expected {file_hash}, got {actual_hash}")
                return False
            
            # Verify file size
            actual_size = Path(file_path).stat().st_size
            if actual_size != file_size:
                logger.error(f"File size mismatch: expected {file_size}, got {actual_size}")
                return False
            
            # Verify signature
            # Create message to verify: hash|size|upload_id|timestamp
            message = f"{file_hash}|{file_size}|{upload_id}|{timestamp}".encode('utf-8')
            signature_bytes = bytes.fromhex(signature)
            
            try:
                self.server_public_key.verify(
                    signature_bytes,
                    message,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                logger.info(f"Receipt verified successfully for upload {upload_id}")
                return True
            except InvalidSignature:
                logger.error(f"Invalid signature in receipt for upload {upload_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error verifying receipt: {e}")
            return False
    
    def store_receipt(self, receipt: Dict[str, Any], file_path: str) -> bool:
        """
        Verify and store receipt.
        
        Args:
            receipt: Receipt dictionary
            file_path: Path to uploaded file
            
        Returns:
            True if receipt was verified and stored, False otherwise
        """
        if not self.verify_receipt(receipt, file_path):
            return False
        
        try:
            upload_id = receipt.get('upload_id')
            receipt_file = self.store_dir / f"receipt_{upload_id}.json"
            
            receipt_data = {
                'receipt': receipt,
                'file_path': str(file_path),
                'file_hash': receipt.get('file_hash'),
                'verified_at': datetime.now().isoformat(),
                'verified': True
            }
            
            with open(receipt_file, 'w') as f:
                json.dump(receipt_data, f, indent=2)
            
            logger.info(f"Stored verified receipt: {receipt_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error storing receipt: {e}")
            return False
    
    def get_receipt(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stored receipt by upload ID.
        
        Args:
            upload_id: Upload identifier
            
        Returns:
            Receipt data or None
        """
        receipt_file = self.store_dir / f"receipt_{upload_id}.json"
        
        if not receipt_file.exists():
            return None
        
        try:
            with open(receipt_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading receipt: {e}")
            return None
    
    def list_receipts(self) -> list:
        """
        List all stored receipts.
        
        Returns:
            List of receipt data dictionaries
        """
        receipts = []
        
        for receipt_file in self.store_dir.glob('receipt_*.json'):
            try:
                with open(receipt_file, 'r') as f:
                    receipt_data = json.load(f)
                    receipts.append(receipt_data)
            except Exception as e:
                logger.error(f"Error reading receipt file {receipt_file}: {e}")
        
        return receipts

