# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/context/chunker.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Deterministic text splitter with hash-stable chunking

import hashlib
from typing import List, Dict, Iterator
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    text: str
    chunk_id: str
    start_pos: int
    end_pos: int
    hash: str
    metadata: Dict = None


class DeterministicChunker:
    """
    Deterministic text chunker that produces hash-stable chunks.
    Same input always produces same chunks with same IDs.
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            separators: List of separator strings to split on (priority order)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if separators is None:
            # Default separators: paragraph breaks, sentence breaks, word breaks
            self.separators = ['\n\n', '\n', '. ', ' ', '']
        else:
            self.separators = separators
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """
        Chunk text deterministically.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of Chunk objects
        """
        if not text:
            return []
        
        chunks = []
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(text):
            # Determine chunk boundaries
            chunk_end = min(current_pos + self.chunk_size, len(text))
            
            # Try to find a good split point
            chunk_text = text[current_pos:chunk_end]
            
            # If not at end of text, try to split at separator
            if chunk_end < len(text):
                # Look for best separator in reverse order
                split_pos = None
                for sep in self.separators:
                    if sep:
                        # Find last occurrence of separator in chunk
                        pos = chunk_text.rfind(sep)
                        if pos > self.chunk_size * 0.5:  # Only split if not too early
                            split_pos = current_pos + pos + len(sep)
                            break
                
                if split_pos:
                    chunk_end = split_pos
                    chunk_text = text[current_pos:chunk_end]
            
            # Create chunk
            chunk_hash = self._compute_chunk_hash(chunk_text, current_pos)
            chunk_id = f"chunk_{chunk_index}_{chunk_hash[:8]}"
            
            chunk = Chunk(
                text=chunk_text,
                chunk_id=chunk_id,
                start_pos=current_pos,
                end_pos=chunk_end,
                hash=chunk_hash,
                metadata=metadata or {}
            )
            
            chunks.append(chunk)
            
            # Move to next position with overlap
            current_pos = max(current_pos + 1, chunk_end - self.chunk_overlap)
            chunk_index += 1
        
        logger.info(f"Chunked text into {len(chunks)} chunks")
        return chunks
    
    def _compute_chunk_hash(self, text: str, position: int) -> str:
        """
        Compute deterministic hash for chunk.
        
        Args:
            text: Chunk text
            position: Start position in original text
            
        Returns:
            SHA256 hash hex string
        """
        # Include position for uniqueness
        hash_input = f"{position}:{text}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    def chunk_documents(self, documents: List[Dict]) -> List[Chunk]:
        """
        Chunk multiple documents.
        
        Args:
            documents: List of dicts with 'text' and optional 'metadata'
            
        Returns:
            List of all chunks from all documents
        """
        all_chunks = []
        
        for doc_idx, doc in enumerate(documents):
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})
            metadata['doc_index'] = doc_idx
            metadata['doc_id'] = doc.get('id', f"doc_{doc_idx}")
            
            chunks = self.chunk_text(text, metadata=metadata)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def verify_chunk_integrity(self, chunk: Chunk) -> bool:
        """
        Verify chunk hash matches its content.
        
        Args:
            chunk: Chunk to verify
            
        Returns:
            True if hash is valid
        """
        expected_hash = self._compute_chunk_hash(chunk.text, chunk.start_pos)
        return expected_hash == chunk.hash

