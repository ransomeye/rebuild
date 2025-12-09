# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/bundle/chunker.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Streaming chunker that calculates SHA256 on-the-fly while writing

import os
import hashlib
import logging
from pathlib import Path
from typing import BinaryIO, Tuple

logger = logging.getLogger(__name__)


class StreamingChunker:
    """Streaming chunker that calculates SHA256 while writing."""
    
    def __init__(self, chunk_size_mb: int = 256):
        """
        Initialize chunker.
        
        Args:
            chunk_size_mb: Chunk size in megabytes (default: 256MB)
        """
        self.chunk_size = chunk_size_mb * 1024 * 1024  # Convert to bytes
        self.buffer_size = 64 * 1024  # 64KB buffer for reads
    
    def chunk_stream(
        self,
        input_stream: BinaryIO,
        output_dir: Path,
        base_name: str
    ) -> Tuple[list, str]:
        """
        Chunk a stream into files while calculating SHA256.
        
        Args:
            input_stream: Input stream to chunk
            output_dir: Directory to write chunks
            base_name: Base name for chunk files
        
        Returns:
            Tuple of (chunk_info_list, overall_sha256)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_info = []
        overall_hash = hashlib.sha256()
        chunk_index = 0
        current_chunk_size = 0
        current_chunk_hash = hashlib.sha256()
        current_chunk_file = None
        
        try:
            while True:
                # Read buffer
                data = input_stream.read(self.buffer_size)
                if not data:
                    break
                
                # Update overall hash
                overall_hash.update(data)
                
                # Write to current chunk
                if current_chunk_file is None:
                    chunk_path = output_dir / f"{base_name}.chunk.{chunk_index:04d}"
                    current_chunk_file = open(chunk_path, 'wb')
                    current_chunk_size = 0
                    current_chunk_hash = hashlib.sha256()
                
                current_chunk_file.write(data)
                current_chunk_hash.update(data)
                current_chunk_size += len(data)
                
                # If chunk is full, finalize it
                if current_chunk_size >= self.chunk_size:
                    current_chunk_file.close()
                    chunk_hash = current_chunk_hash.hexdigest()
                    
                    chunk_info.append({
                        'index': chunk_index,
                        'path': str(chunk_path),
                        'size': current_chunk_size,
                        'sha256': chunk_hash
                    })
                    
                    logger.debug(f"Chunk {chunk_index} written: {current_chunk_size} bytes, hash: {chunk_hash[:16]}...")
                    
                    chunk_index += 1
                    current_chunk_file = None
                    current_chunk_size = 0
                    current_chunk_hash = hashlib.sha256()
            
            # Finalize last chunk if exists
            if current_chunk_file is not None:
                current_chunk_file.close()
                chunk_path = output_dir / f"{base_name}.chunk.{chunk_index:04d}"
                chunk_hash = current_chunk_hash.hexdigest()
                
                chunk_info.append({
                    'index': chunk_index,
                    'path': str(chunk_path),
                    'size': current_chunk_size,
                    'sha256': chunk_hash
                })
                
                logger.debug(f"Final chunk {chunk_index} written: {current_chunk_size} bytes, hash: {chunk_hash[:16]}...")
            
            overall_sha256 = overall_hash.hexdigest()
            logger.info(f"Stream chunked into {len(chunk_info)} chunks, overall SHA256: {overall_sha256[:16]}...")
            
            return chunk_info, overall_sha256
            
        except Exception as e:
            if current_chunk_file:
                current_chunk_file.close()
            logger.error(f"Error during chunking: {e}")
            raise
    
    def chunk_file(
        self,
        input_path: Path,
        output_dir: Path,
        base_name: str = None
    ) -> Tuple[list, str]:
        """
        Chunk a file into chunks while calculating SHA256.
        
        Args:
            input_path: Path to input file
            output_dir: Directory to write chunks
            base_name: Base name for chunks (default: input filename)
        
        Returns:
            Tuple of (chunk_info_list, overall_sha256)
        """
        if base_name is None:
            base_name = input_path.stem
        
        with open(input_path, 'rb') as f:
            return self.chunk_stream(f, output_dir, base_name)

