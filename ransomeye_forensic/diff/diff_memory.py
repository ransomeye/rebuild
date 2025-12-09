# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/diff/diff_memory.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Compare two memory snapshots using rolling hashes and identify changed pages

import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator
from datetime import datetime
import logging

from .snapshot_reader import SnapshotReader
from .diff_algorithms import RollingHash, EntropyCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryDiffer:
    """
    Compare two memory snapshots and identify differences.
    Uses streaming rolling hash algorithm to handle large snapshots efficiently.
    """
    
    def __init__(self, window_size: int = 4096, chunk_size: int = 1024 * 1024):
        """
        Initialize memory differ.
        
        Args:
            window_size: Size of rolling hash window (default: 4KB page size)
            chunk_size: Size of chunks to read from files (default: 1MB)
        """
        self.window_size = window_size
        self.chunk_size = chunk_size
        self.rolling_hash = RollingHash(window_size=window_size)
        self.entropy_calc = EntropyCalculator()
    
    def diff_snapshots(
        self,
        snapshot_a_path: str,
        snapshot_b_path: str,
        snapshot_a_id: Optional[str] = None,
        snapshot_b_id: Optional[str] = None
    ) -> Dict:
        """
        Compare two memory snapshots and return diff results.
        
        Args:
            snapshot_a_path: Path to first snapshot
            snapshot_b_path: Path to second snapshot
            snapshot_a_id: Optional ID for snapshot A
            snapshot_b_id: Optional ID for snapshot B
            
        Returns:
            Dictionary with diff results including changed pages, entropy deltas, etc.
        """
        logger.info(f"Starting memory diff: {snapshot_a_path} vs {snapshot_b_path}")
        
        reader_a = SnapshotReader(snapshot_a_path)
        reader_b = SnapshotReader(snapshot_b_path)
        
        # Generate diff ID
        diff_id = str(uuid.uuid4())
        
        # Compare snapshots using streaming approach
        changed_pages = []
        added_pages = []
        removed_pages = []
        unchanged_pages = []
        
        # Build hash maps for both snapshots
        hash_map_a = {}
        hash_map_b = {}
        
        # Process snapshot A - use page-based approach for efficiency
        logger.info("Processing snapshot A...")
        for page_num, page_data in reader_a.read_pages():
            if len(page_data) >= self.window_size:
                hash_val = self.rolling_hash.compute_hash(page_data[:self.window_size])
                hash_map_a[page_num * 4096] = (hash_val, page_data[:self.window_size])
        
        # Process snapshot B
        logger.info("Processing snapshot B...")
        for page_num, page_data in reader_b.read_pages():
            if len(page_data) >= self.window_size:
                hash_val = self.rolling_hash.compute_hash(page_data[:self.window_size])
                hash_map_b[page_num * 4096] = (hash_val, page_data[:self.window_size])
        
        # Compare hash maps
        all_positions = set(hash_map_a.keys()) | set(hash_map_b.keys())
        
        for pos in sorted(all_positions):
            hash_a = hash_map_a.get(pos)
            hash_b = hash_map_b.get(pos)
            
            if hash_a is None:
                # Page exists only in B (added)
                added_pages.append({
                    'position': pos,
                    'hash': hash_b[0],
                    'size': len(hash_b[1])
                })
            elif hash_b is None:
                # Page exists only in A (removed)
                removed_pages.append({
                    'position': pos,
                    'hash': hash_a[0],
                    'size': len(hash_a[1])
                })
            elif hash_a[0] != hash_b[0]:
                # Page changed
                # Calculate entropy delta for changed pages
                entropy_a = self.entropy_calc.calculate_entropy(hash_a[1])
                entropy_b = self.entropy_calc.calculate_entropy(hash_b[1])
                
                changed_pages.append({
                    'position': pos,
                    'hash_a': hash_a[0],
                    'hash_b': hash_b[0],
                    'entropy_a': entropy_a,
                    'entropy_b': entropy_b,
                    'entropy_delta': abs(entropy_a - entropy_b),
                    'size': len(hash_a[1])
                })
            else:
                # Page unchanged
                unchanged_pages.append({
                    'position': pos,
                    'hash': hash_a[0],
                    'size': len(hash_a[1])
                })
        
        # Calculate overall statistics
        total_pages_a = len(hash_map_a)
        total_pages_b = len(hash_map_b)
        total_changed = len(changed_pages)
        total_added = len(added_pages)
        total_removed = len(removed_pages)
        total_unchanged = len(unchanged_pages)
        
        # Calculate entropy maps for overall comparison (streaming)
        logger.info("Calculating entropy maps...")
        entropy_map_a = self._calculate_entropy_map_streaming(reader_a, window_size=4096, step=1024)
        entropy_map_b = self._calculate_entropy_map_streaming(reader_b, window_size=4096, step=1024)
        avg_entropy_delta = self.entropy_calc.calculate_entropy_delta(entropy_map_a, entropy_map_b)
        
        # Build result
        result = {
            'diff_id': diff_id,
            'snapshot_a_id': snapshot_a_id or 'unknown',
            'snapshot_b_id': snapshot_b_id or 'unknown',
            'snapshot_a_path': snapshot_a_path,
            'snapshot_b_path': snapshot_b_path,
            'timestamp': datetime.utcnow().isoformat(),
            'statistics': {
                'total_pages_a': total_pages_a,
                'total_pages_b': total_pages_b,
                'changed_pages': total_changed,
                'added_pages': total_added,
                'removed_pages': total_removed,
                'unchanged_pages': total_unchanged,
                'change_percentage': (total_changed / max(total_pages_a, total_pages_b) * 100) if max(total_pages_a, total_pages_b) > 0 else 0,
                'avg_entropy_delta': avg_entropy_delta
            },
            'changed_pages': changed_pages[:1000],  # Limit to first 1000 for response size
            'added_pages': added_pages[:1000],
            'removed_pages': removed_pages[:1000],
            'metadata': {
                'window_size': self.window_size,
                'chunk_size': self.chunk_size,
                'platform_a': reader_a.platform,
                'platform_b': reader_b.platform
            }
        }
        
        logger.info(f"Diff completed: {total_changed} changed, {total_added} added, {total_removed} removed")
        
        return result
    
    def _calculate_entropy_map_streaming(
        self,
        reader: SnapshotReader,
        window_size: int = 4096,
        step: int = 1024
    ) -> list:
        """
        Calculate entropy map using streaming (does not load full file).
        
        Args:
            reader: SnapshotReader instance
            window_size: Size of sliding window
            step: Step size between windows
            
        Returns:
            List of (position, entropy) tuples
        """
        entropy_map = []
        position = 0
        buffer = b''
        
        # Read in chunks and process windows
        for chunk in reader.read_chunks(chunk_size=step * 4):  # Read larger chunks for efficiency
            buffer += chunk
            
            # Process complete windows
            while len(buffer) >= window_size:
                window = buffer[:window_size]
                entropy = self.entropy_calc.calculate_entropy(window)
                entropy_map.append((position, entropy))
                
                # Slide window by step
                buffer = buffer[step:]
                position += step
                
                # Limit to prevent excessive memory usage
                if len(entropy_map) > 10000:  # Limit to 10k samples
                    logger.warning("Entropy map truncated to prevent excessive memory usage")
                    break
            
            if len(entropy_map) > 10000:
                break
        
        return entropy_map
    
    def diff_by_snapshot_ids(
        self,
        snapshot_a_id: str,
        snapshot_b_id: str,
        artifact_store_path: Optional[str] = None
    ) -> Dict:
        """
        Diff snapshots by their artifact IDs (retrieves from storage).
        
        Args:
            snapshot_a_id: Artifact ID of first snapshot
            snapshot_b_id: Artifact ID of second snapshot
            artifact_store_path: Path to artifact storage (from env if None)
            
        Returns:
            Diff results dictionary
        """
        if artifact_store_path is None:
            artifact_store_path = os.environ.get(
                'ARTIFACT_STORAGE_DIR',
                '/home/ransomeye/rebuild/ransomeye_forensic/storage/artifacts'
            )
        
        # In production, retrieve snapshot paths from artifact store
        # For now, assume snapshots are stored with their artifact_id
        snapshot_a_path = Path(artifact_store_path) / snapshot_a_id / "snapshot.raw"
        snapshot_b_path = Path(artifact_store_path) / snapshot_b_id / "snapshot.raw"
        
        if not snapshot_a_path.exists():
            raise FileNotFoundError(f"Snapshot A not found: {snapshot_a_path}")
        if not snapshot_b_path.exists():
            raise FileNotFoundError(f"Snapshot B not found: {snapshot_b_path}")
        
        return self.diff_snapshots(
            str(snapshot_a_path),
            str(snapshot_b_path),
            snapshot_a_id=snapshot_a_id,
            snapshot_b_id=snapshot_b_id
        )

