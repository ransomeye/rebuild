# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/capture/chunker.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Streaming chunker that splits input into 256MB chunks and calculates SHA256 for each chunk and total stream

import hashlib
from typing import Iterator, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StreamChunker:
    """
    Streams input data, splits into chunks, and calculates SHA256
    for each chunk and the total stream on-the-fly.
    """
    
    def __init__(self, chunk_size: int = 256 * 1024 * 1024):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Size of each chunk in bytes (default: 256MB)
        """
        self.chunk_size = chunk_size
    
    def chunk_stream(self, input_stream: Iterator[bytes]) -> Iterator[Tuple[int, bytes, str]]:
        """
        Chunk a stream and yield (chunk_index, chunk_data, chunk_hash).
        
        Args:
            input_stream: Iterator yielding bytes
            
        Yields:
            Tuple of (chunk_index, chunk_data, chunk_hash)
        """
        chunk_index = 0
        current_chunk = b''
        
        for data in input_stream:
            current_chunk += data
            
            # Yield chunk when it reaches chunk_size
            while len(current_chunk) >= self.chunk_size:
                chunk_data = current_chunk[:self.chunk_size]
                current_chunk = current_chunk[self.chunk_size:]
                
                # Calculate SHA256 for this chunk
                chunk_hash = hashlib.sha256(chunk_data).hexdigest()
                
                yield (chunk_index, chunk_data, chunk_hash)
                chunk_index += 1
        
        # Yield remaining data as final chunk
        if current_chunk:
            chunk_hash = hashlib.sha256(current_chunk).hexdigest()
            yield (chunk_index, current_chunk, chunk_hash)
    
    def chunk_file(self, file_path, chunk_size: Optional[int] = None) -> Iterator[Tuple[int, bytes, str]]:
        """
        Chunk a file and yield (chunk_index, chunk_data, chunk_hash).
        Uses generator to avoid loading entire file into memory.
        
        Args:
            file_path: Path to file
            chunk_size: Optional override for chunk size
            
        Yields:
            Tuple of (chunk_index, chunk_data, chunk_hash)
        """
        chunk_size = chunk_size or self.chunk_size
        
        def file_stream():
            """Generator that reads file in chunks."""
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(8192)  # Read in 8KB blocks
                    if not data:
                        break
                    yield data
        
        yield from self.chunk_stream(file_stream())
    
    def calculate_total_hash(self, input_stream: Iterator[bytes]) -> str:
        """
        Calculate SHA256 hash of entire stream.
        
        Args:
            input_stream: Iterator yielding bytes
            
        Returns:
            SHA256 hash as hex string
        """
        total_hash = hashlib.sha256()
        
        for data in input_stream:
            total_hash.update(data)
        
        return total_hash.hexdigest()
    
    def chunk_and_hash(self, input_stream: Iterator[bytes]) -> Tuple[list, str]:
        """
        Chunk stream and calculate both chunk hashes and total hash.
        
        Args:
            input_stream: Iterator yielding bytes
            
        Returns:
            Tuple of (chunk_info_list, total_hash)
            chunk_info_list contains dicts with: index, hash, size
        """
        chunks = []
        total_hash = hashlib.sha256()
        chunk_index = 0
        current_chunk = b''
        
        for data in input_stream:
            current_chunk += data
            total_hash.update(data)
            
            # Process chunk when it reaches chunk_size
            while len(current_chunk) >= self.chunk_size:
                chunk_data = current_chunk[:self.chunk_size]
                current_chunk = current_chunk[self.chunk_size:]
                
                # Calculate SHA256 for this chunk
                chunk_hash = hashlib.sha256(chunk_data).hexdigest()
                
                chunks.append({
                    'index': chunk_index,
                    'hash': chunk_hash,
                    'size': len(chunk_data)
                })
                chunk_index += 1
        
        # Process remaining data as final chunk
        if current_chunk:
            chunk_hash = hashlib.sha256(current_chunk).hexdigest()
            chunks.append({
                'index': chunk_index,
                'hash': chunk_hash,
                'size': len(current_chunk)
            })
        
        return chunks, total_hash.hexdigest()

