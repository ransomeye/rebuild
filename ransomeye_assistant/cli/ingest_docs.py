# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/cli/ingest_docs.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to recursively ingest a folder of documents

import argparse
import sys
import uuid
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_assistant.retriever.ingestion_engine import IngestionEngine
from ransomeye_assistant.retriever.embedder import Embedder
from ransomeye_assistant.retriever.vector_store import VectorStore
from ransomeye_assistant.storage.kv_store import KVStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_folder(folder_path: Path, recursive: bool = True):
    """
    Recursively ingest documents from folder.
    
    Args:
        folder_path: Path to folder containing documents
        recursive: Whether to search recursively
    """
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        logger.error(f"Folder not found: {folder_path}")
        return
    
    # Initialize components
    ingestion_engine = IngestionEngine()
    embedder = Embedder()
    vector_store = VectorStore()
    kv_store = KVStore()
    
    # Find documents
    extensions = ['.pdf', '.txt', '.log', '.json', '.md']
    documents = []
    
    if recursive:
        for ext in extensions:
            documents.extend(folder_path.rglob(f"*{ext}"))
    else:
        for ext in extensions:
            documents.extend(folder_path.glob(f"*{ext}"))
    
    logger.info(f"Found {len(documents)} documents to ingest")
    
    total_chunks = 0
    
    for doc_path in documents:
        try:
            doc_id = str(uuid.uuid4())
            logger.info(f"Processing: {doc_path}")
            
            # Process document
            chunks = ingestion_engine.process_document(doc_path, doc_id)
            
            if not chunks:
                logger.warning(f"No chunks extracted from: {doc_path}")
                continue
            
            # Embed chunks
            embeddings = []
            chunk_ids = []
            for chunk in chunks:
                embedding = embedder.embed(chunk['text'])
                embeddings.append(embedding)
                chunk_id = chunk['chunk_id']
                chunk_ids.append(chunk_id)
                
                # Store chunk text
                kv_store.store(chunk_id, {
                    'text': chunk['text'],
                    'doc_id': doc_id,
                    'chunk_index': chunk['chunk_index'],
                    'metadata': chunk.get('metadata', {})
                })
            
            # Add to vector store
            vector_store.add_vectors(chunk_ids, embeddings)
            total_chunks += len(chunks)
            
            logger.info(f"Ingested {doc_path}: {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing {doc_path}: {e}")
    
    # Save index
    vector_store.save_index()
    
    logger.info(f"Ingestion complete: {total_chunks} total chunks from {len(documents)} documents")

def main():
    parser = argparse.ArgumentParser(description='Ingest documents from folder')
    parser.add_argument('--folder', type=str, required=True,
                       help='Path to folder containing documents')
    parser.add_argument('--recursive', action='store_true', default=True,
                       help='Search recursively (default: True)')
    
    args = parser.parse_args()
    
    try:
        ingest_folder(Path(args.folder), recursive=args.recursive)
        return 0
    except Exception as e:
        logger.error(f"Error ingesting documents: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())

