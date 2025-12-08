# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/capture/compressor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Zstd streaming compression wrapper

import zstandard as zstd
from typing import Iterator, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StreamCompressor:
    """Zstd streaming compression wrapper."""
    
    def __init__(self, compression_level: int = 3):
        """
        Initialize compressor.
        
        Args:
            compression_level: Zstd compression level (1-22, default 3)
        """
        self.compression_level = compression_level
        self.cctx = zstd.ZstdCompressor(level=compression_level)
    
    def compress_stream(self, input_stream: Iterator[bytes]) -> Iterator[bytes]:
        """
        Compress a stream using Zstd.
        
        Args:
            input_stream: Iterator yielding bytes
            
        Yields:
            Compressed bytes
        """
        compressor = self.cctx.stream_writer()
        
        for data in input_stream:
            compressed = compressor.compress(data)
            if compressed:
                yield compressed
        
        # Flush remaining data
        remaining = compressor.flush(zstd.FLUSH_FRAME)
        if remaining:
            yield remaining
    
    def compress_file(self, input_path: str, output_path: str):
        """
        Compress a file using Zstd.
        
        Args:
            input_path: Path to input file
            output_path: Path to output compressed file
        """
        with open(input_path, 'rb') as infile:
            with open(output_path, 'wb') as outfile:
                compressor = self.cctx.stream_writer(outfile)
                
                while True:
                    chunk = infile.read(8192)
                    if not chunk:
                        break
                    compressor.write(chunk)
                
                compressor.flush(zstd.FLUSH_FRAME)
        
        logger.info(f"Compressed {input_path} -> {output_path}")

class StreamDecompressor:
    """Zstd streaming decompression wrapper."""
    
    def __init__(self):
        """Initialize decompressor."""
        self.dctx = zstd.ZstdDecompressor()
    
    def decompress_stream(self, input_stream: Iterator[bytes]) -> Iterator[bytes]:
        """
        Decompress a stream using Zstd.
        
        Args:
            input_stream: Iterator yielding compressed bytes
            
        Yields:
            Decompressed bytes
        """
        decompressor = self.dctx.stream_reader(b''.join(input_stream))
        
        while True:
            chunk = decompressor.read(8192)
            if not chunk:
                break
            yield chunk
    
    def decompress_file(self, input_path: str, output_path: str):
        """
        Decompress a file using Zstd.
        
        Args:
            input_path: Path to compressed file
            output_path: Path to output decompressed file
        """
        with open(input_path, 'rb') as infile:
            with open(output_path, 'wb') as outfile:
                decompressor = self.dctx.stream_reader(infile)
                
                while True:
                    chunk = decompressor.read(8192)
                    if not chunk:
                        break
                    outfile.write(chunk)
        
        logger.info(f"Decompressed {input_path} -> {output_path}")

