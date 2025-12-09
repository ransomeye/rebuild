# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/diff/snapshot_reader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Parsers for raw memory dumps (simulated Linux/Win structures)

import os
import struct
from pathlib import Path
from typing import Dict, List, Optional, Iterator, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SnapshotReader:
    """
    Reader for memory snapshot files.
    Supports both raw dumps and structured formats (simulated).
    """
    
    # Memory page size constants
    PAGE_SIZE_LINUX = 4096
    PAGE_SIZE_WINDOWS = 4096
    
    def __init__(self, snapshot_path: str):
        """
        Initialize snapshot reader.
        
        Args:
            snapshot_path: Path to memory snapshot file
        """
        self.snapshot_path = Path(snapshot_path)
        if not self.snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")
        
        self.file_size = self.snapshot_path.stat().st_size
        self.platform = self._detect_platform()
    
    def _detect_platform(self) -> str:
        """
        Detect platform from snapshot metadata or file structure.
        
        Returns:
            Platform identifier ('linux', 'windows', or 'unknown')
        """
        # In production, this would analyze file headers or metadata
        # For now, use heuristic based on file naming or size patterns
        filename_lower = self.snapshot_path.name.lower()
        
        if 'linux' in filename_lower or 'memdump' in filename_lower:
            return 'linux'
        elif 'windows' in filename_lower or 'win' in filename_lower:
            return 'windows'
        else:
            # Default to linux for raw dumps
            return 'linux'
    
    def read_chunks(self, chunk_size: int = 4096) -> Iterator[bytes]:
        """
        Read snapshot in chunks for streaming processing.
        
        Args:
            chunk_size: Size of chunks to read
            
        Yields:
            Chunks of bytes
        """
        with open(self.snapshot_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    def read_pages(self, page_size: int = None) -> Iterator[Tuple[int, bytes]]:
        """
        Read snapshot as memory pages.
        
        Args:
            page_size: Page size (defaults to platform-specific)
            
        Yields:
            Tuples of (page_number, page_data)
        """
        if page_size is None:
            page_size = self.PAGE_SIZE_LINUX if self.platform == 'linux' else self.PAGE_SIZE_WINDOWS
        
        page_num = 0
        with open(self.snapshot_path, 'rb') as f:
            while True:
                page_data = f.read(page_size)
                if not page_data:
                    break
                
                # Pad to page size if needed
                if len(page_data) < page_size:
                    page_data += b'\x00' * (page_size - len(page_data))
                
                yield (page_num, page_data)
                page_num += 1
    
    def get_metadata(self) -> Dict:
        """
        Extract metadata from snapshot.
        
        Returns:
            Dictionary with metadata
        """
        return {
            'path': str(self.snapshot_path),
            'size': self.file_size,
            'platform': self.platform,
            'page_size': self.PAGE_SIZE_LINUX if self.platform == 'linux' else self.PAGE_SIZE_WINDOWS,
            'total_pages': (self.file_size + 4095) // 4096
        }
    
    def extract_process_regions(self) -> List[Dict]:
        """
        Extract process memory regions (simulated for raw dumps).
        In production, this would parse ELF/PE structures or /proc/[pid]/maps.
        
        Returns:
            List of region dictionaries with start, end, permissions, etc.
        """
        # For raw dumps, simulate process regions
        # In production, integrate with Volatility or similar tools
        regions = []
        
        # Simulate: scan for potential process boundaries
        # This is a placeholder - real implementation would parse ELF/PE headers
        page_size = self.PAGE_SIZE_LINUX if self.platform == 'linux' else self.PAGE_SIZE_WINDOWS
        total_pages = (self.file_size + page_size - 1) // page_size
        
        # Simulate some regions
        if total_pages > 0:
            regions.append({
                'start': 0,
                'end': min(1024 * page_size, self.file_size),
                'permissions': 'r-x',  # Code region
                'type': 'code'
            })
        
        if total_pages > 1024:
            regions.append({
                'start': 1024 * page_size,
                'end': min(2048 * page_size, self.file_size),
                'permissions': 'rw-',  # Data region
                'type': 'data'
            })
        
        return regions
    
    def compute_checksum(self, algorithm: str = 'sha256') -> str:
        """
        Compute checksum of entire snapshot.
        
        Args:
            algorithm: Hash algorithm ('md5', 'sha1', 'sha256')
            
        Returns:
            Hexadecimal hash string
        """
        import hashlib
        
        hash_obj = hashlib.new(algorithm)
        
        with open(self.snapshot_path, 'rb') as f:
            while True:
                chunk = f.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()

