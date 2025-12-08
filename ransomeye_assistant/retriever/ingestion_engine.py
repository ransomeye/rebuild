# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/retriever/ingestion_engine.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Text cleaner and chunker with 500 token chunks and overlap

import os
import re
from pathlib import Path
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestionEngine:
    """
    Processes documents: cleans text and chunks into 500-token segments with overlap.
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize ingestion engine.
        
        Args:
            chunk_size: Target chunk size in tokens (default: 500)
            chunk_overlap: Overlap between chunks in tokens (default: 50)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_document(self, file_path: Path, doc_id: str) -> List[Dict[str, Any]]:
        """
        Process a document: clean and chunk.
        
        Args:
            file_path: Path to document file
            doc_id: Document identifier
            
        Returns:
            List of chunk dictionaries
        """
        # Read file content
        content = self._read_file(file_path)
        
        # Clean text
        cleaned_content = self._clean_text(content)
        
        # Chunk text
        chunks = self._chunk_text(cleaned_content, doc_id, file_path)
        
        logger.info(f"Processed document {doc_id}: {len(chunks)} chunks")
        return chunks
    
    def _read_file(self, file_path: Path) -> str:
        """
        Read file content based on file type.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content as string
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return self._read_pdf(file_path)
        elif suffix in ['.txt', '.log', '.json']:
            return self._read_text(file_path)
        else:
            # Try to read as text
            return self._read_text(file_path)
    
    def _read_pdf(self, file_path: Path) -> str:
        """
        Read PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            PDF text content
        """
        try:
            import PyPDF2
            text_parts = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text_parts.append(page.extract_text())
            return '\n'.join(text_parts)
        except ImportError:
            logger.warning("PyPDF2 not available, reading PDF as text")
            return self._read_text(file_path)
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return self._read_text(file_path)
    
    def _read_text(self, file_path: Path) -> str:
        """
        Read text file.
        
        Args:
            file_path: Path to text file
            
        Returns:
            File content
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text: remove extra whitespace, normalize.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()
    
    def _chunk_text(self, text: str, doc_id: str, file_path: Path) -> List[Dict[str, Any]]:
        """
        Chunk text into 500-token segments with overlap.
        
        Args:
            text: Text to chunk
            doc_id: Document identifier
            file_path: Original file path
            
        Returns:
            List of chunk dictionaries
        """
        # Simple tokenization (word-based, approximate)
        words = text.split()
        chunks = []
        
        chunk_index = 0
        start_idx = 0
        
        while start_idx < len(words):
            # Calculate end index
            end_idx = min(start_idx + self.chunk_size, len(words))
            
            # Extract chunk
            chunk_words = words[start_idx:end_idx]
            chunk_text = ' '.join(chunk_words)
            
            # Create chunk dict
            chunk = {
                'chunk_id': f"{doc_id}_{chunk_index}",
                'doc_id': doc_id,
                'chunk_index': chunk_index,
                'text': chunk_text,
                'token_count': len(chunk_words),
                'metadata': {
                    'source_file': str(file_path),
                    'chunk_start': start_idx,
                    'chunk_end': end_idx
                }
            }
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start_idx = end_idx - self.chunk_overlap
            chunk_index += 1
            
            # Prevent infinite loop
            if start_idx >= end_idx:
                break
        
        return chunks

