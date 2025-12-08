# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/ledger/evidence_ledger.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Blockchain-lite append-only ledger where every entry contains prev_hash + curr_hash

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvidenceLedger:
    """
    Append-only ledger with Merkle-chain style hashing.
    Each entry contains prev_hash + curr_hash for integrity.
    """
    
    def __init__(self, ledger_path: str = None):
        """
        Initialize evidence ledger.
        
        Args:
            ledger_path: Path to ledger JSONL file
        """
        self.ledger_path = Path(ledger_path or os.environ.get(
            'EVIDENCE_LEDGER_PATH',
            '/home/ransomeye/rebuild/ransomeye_forensic/storage/evidence_ledger.jsonl'
        ))
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get last hash if ledger exists
        self.last_hash = self._get_last_hash()
    
    def _get_last_hash(self) -> Optional[str]:
        """
        Get hash of last entry in ledger.
        
        Returns:
            Last entry hash or None if ledger is empty
        """
        if not self.ledger_path.exists():
            return None
        
        try:
            with open(self.ledger_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    # Get last non-empty line
                    for line in reversed(lines):
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            return entry.get('curr_hash')
        except Exception as e:
            logger.warning(f"Error reading last hash: {e}")
        
        return None
    
    def _calculate_entry_hash(self, entry_data: Dict[str, Any], prev_hash: Optional[str]) -> str:
        """
        Calculate hash for ledger entry (Merkle-chain style).
        
        Args:
            entry_data: Entry data dictionary
            prev_hash: Hash of previous entry
            
        Returns:
            SHA256 hash of entry
        """
        # Create hash input: previous hash + entry content
        entry_content = json.dumps(entry_data, sort_keys=True).encode()
        combined = (prev_hash or b'').encode() + entry_content
        return hashlib.sha256(combined).hexdigest()
    
    def append_entry(self, artifact_id: str, artifact_type: str,
                    artifact_path: str, chunk_hashes: List[str],
                    total_hash: str, metadata: Dict[str, Any] = None) -> str:
        """
        Append a new entry to the ledger.
        
        Args:
            artifact_id: Unique artifact identifier
            artifact_type: Type of artifact (memory, disk, file)
            artifact_path: Path to artifact
            chunk_hashes: List of SHA256 hashes for each chunk
            total_hash: SHA256 hash of entire artifact
            metadata: Optional metadata
            
        Returns:
            Entry hash (curr_hash)
        """
        metadata = metadata or {}
        
        # Create entry data
        entry_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'artifact_id': artifact_id,
            'artifact_type': artifact_type,
            'artifact_path': artifact_path,
            'chunk_hashes': chunk_hashes,
            'total_hash': total_hash,
            'metadata': metadata
        }
        
        # Calculate hashes
        prev_hash = self.last_hash
        curr_hash = self._calculate_entry_hash(entry_data, prev_hash)
        
        # Add hash fields to entry
        entry = {
            'prev_hash': prev_hash,
            'curr_hash': curr_hash,
            **entry_data
        }
        
        # Append to ledger (append-only)
        with open(self.ledger_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Update last hash
        self.last_hash = curr_hash
        
        logger.info(f"Ledger entry appended: {artifact_id} -> {curr_hash[:16]}...")
        return curr_hash
    
    def verify_chain(self) -> bool:
        """
        Verify the integrity of the ledger chain.
        
        Returns:
            True if chain is valid, False otherwise
        """
        if not self.ledger_path.exists():
            return True  # Empty ledger is valid
        
        try:
            prev_hash = None
            
            with open(self.ledger_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    entry = json.loads(line)
                    
                    # Verify prev_hash matches
                    entry_prev_hash = entry.get('prev_hash')
                    if entry_prev_hash != prev_hash:
                        logger.error(f"Chain broken at line {line_num}: prev_hash mismatch")
                        return False
                    
                    # Verify curr_hash
                    entry_data = {k: v for k, v in entry.items() if k not in ['prev_hash', 'curr_hash']}
                    calculated_hash = self._calculate_entry_hash(entry_data, prev_hash)
                    entry_curr_hash = entry.get('curr_hash')
                    
                    if calculated_hash != entry_curr_hash:
                        logger.error(f"Chain broken at line {line_num}: curr_hash mismatch")
                        return False
                    
                    prev_hash = entry_curr_hash
            
            logger.info("Ledger chain verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying ledger chain: {e}")
            return False
    
    def get_entries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get ledger entries.
        
        Args:
            limit: Optional limit on number of entries
            
        Returns:
            List of entry dictionaries
        """
        if not self.ledger_path.exists():
            return []
        
        entries = []
        
        try:
            with open(self.ledger_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
            
            # Return most recent entries first
            entries.reverse()
            
            if limit:
                entries = entries[:limit]
            
            return entries
            
        except Exception as e:
            logger.error(f"Error reading ledger entries: {e}")
            return []
    
    def get_entry_by_artifact_id(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get ledger entry by artifact ID.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            Entry dictionary or None
        """
        if not self.ledger_path.exists():
            return None
        
        try:
            with open(self.ledger_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        if entry.get('artifact_id') == artifact_id:
                            return entry
        except Exception as e:
            logger.error(f"Error searching ledger: {e}")
        
        return None

