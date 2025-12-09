# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/transport/uploader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Resumable chunk uploader with receipt verification

import os
import hashlib
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from queue import Queue
import time

from .probe_client import ProbeClient
from .signed_receipt_store import SignedReceiptStore

logger = logging.getLogger(__name__)


class ChunkUploader:
    """Resumable chunk uploader with receipt verification."""
    
    def __init__(self, buffer_dir: str, receipt_store: SignedReceiptStore):
        """
        Initialize uploader.
        
        Args:
            buffer_dir: Buffer directory containing chunks
            receipt_store: SignedReceiptStore instance
        """
        self.buffer_dir = Path(buffer_dir)
        self.receipt_store = receipt_store
        self.client = ProbeClient()
        
        self.pending_dir = self.buffer_dir / 'pending'
        self.inflight_dir = self.buffer_dir / 'inflight'
        self.archived_dir = self.buffer_dir / 'archived'
        
        for d in [self.pending_dir, self.inflight_dir, self.archived_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.upload_queue: Queue = Queue()
        self.running = False
        self.upload_thread: Optional[threading.Thread] = None
        
        self.chunk_size_mb = int(os.environ.get('PROBE_CHUNK_SIZE_MB', '100'))
        self.max_retries = int(os.environ.get('PROBE_UPLOAD_MAX_RETRIES', '3'))
        self.retry_delay = int(os.environ.get('PROBE_UPLOAD_RETRY_DELAY_SEC', '60'))
        
        self.upload_stats = {
            'successful': 0,
            'failed': 0,
            'retries': 0,
            'bytes_uploaded': 0
        }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _upload_chunk(self, chunk_path: Path) -> bool:
        """
        Upload a single chunk.
        
        Args:
            chunk_path: Path to chunk file
            
        Returns:
            True if successful, False otherwise
        """
        chunk_hash = self._calculate_file_hash(chunk_path)
        chunk_size = chunk_path.stat().st_size
        
        # Move to inflight
        inflight_path = self.inflight_dir / chunk_path.name
        try:
            chunk_path.rename(inflight_path)
        except Exception as e:
            logger.error(f"Error moving chunk to inflight: {e}")
            return False
        
        retries = 0
        while retries < self.max_retries:
            try:
                # Prepare metadata
                metadata = {
                    'chunk_hash': chunk_hash,
                    'chunk_size': chunk_size,
                    'filename': chunk_path.name,
                    'probe_id': os.environ.get('PROBE_ID', 'unknown')
                }
                
                # Upload to Core API
                response = self.client.upload_file(
                    endpoint='/api/v1/probe/upload',
                    file_path=str(inflight_path),
                    metadata=metadata,
                    timeout=300
                )
                
                if response is None:
                    raise Exception("Upload request failed")
                
                # Verify receipt
                receipt = response.get('receipt')
                if not receipt:
                    raise Exception("No receipt in server response")
                
                if not self.receipt_store.verify_receipt(receipt, str(inflight_path)):
                    raise Exception("Receipt verification failed")
                
                # Store receipt
                if not self.receipt_store.store_receipt(receipt, str(inflight_path)):
                    raise Exception("Failed to store receipt")
                
                # Move to archived
                archived_path = self.archived_dir / chunk_path.name
                inflight_path.rename(archived_path)
                
                self.upload_stats['successful'] += 1
                self.upload_stats['bytes_uploaded'] += chunk_size
                
                logger.info(f"Successfully uploaded chunk: {chunk_path.name} "
                          f"({chunk_size / 1024 / 1024:.2f} MB)")
                
                return True
                
            except Exception as e:
                retries += 1
                self.upload_stats['retries'] += 1
                logger.warning(f"Upload failed (attempt {retries}/{self.max_retries}): {e}")
                
                if retries < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    # Move back to pending on final failure
                    try:
                        pending_path = self.pending_dir / chunk_path.name
                        inflight_path.rename(pending_path)
                    except Exception as e2:
                        logger.error(f"Error moving chunk back to pending: {e2}")
                    
                    self.upload_stats['failed'] += 1
                    logger.error(f"Failed to upload chunk after {self.max_retries} attempts: {chunk_path.name}")
                    return False
        
        return False
    
    def _upload_worker(self):
        """Background upload worker thread."""
        logger.info("Upload worker thread started")
        
        while self.running:
            try:
                # Check for pending chunks
                pending_chunks = list(self.pending_dir.glob('*.pcap'))
                pending_chunks.extend(self.pending_dir.glob('*.json'))  # Also upload manifests
                
                if not pending_chunks:
                    time.sleep(10)  # Wait before checking again
                    continue
                
                # Process chunks
                for chunk_path in pending_chunks:
                    if not self.running:
                        break
                    
                    self._upload_chunk(chunk_path)
                
                time.sleep(5)  # Brief pause between batches
                
            except Exception as e:
                logger.error(f"Error in upload worker: {e}")
                time.sleep(10)
        
        logger.info("Upload worker thread stopped")
    
    def queue_upload(self, chunk_path: Path):
        """
        Queue a chunk for upload.
        
        Args:
            chunk_path: Path to chunk file
        """
        if chunk_path.exists():
            self.upload_queue.put(chunk_path)
    
    def upload_pending(self):
        """Upload all pending chunks."""
        pending_chunks = list(self.pending_dir.glob('*'))
        
        logger.info(f"Found {len(pending_chunks)} pending chunks to upload")
        
        for chunk_path in pending_chunks:
            if chunk_path.is_file():
                self._upload_chunk(chunk_path)
    
    def start(self):
        """Start upload worker."""
        if self.running:
            logger.warning("Uploader already running")
            return
        
        logger.info("Starting uploader...")
        self.running = True
        
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.upload_thread.start()
    
    def stop(self):
        """Stop upload worker."""
        if not self.running:
            return
        
        logger.info("Stopping uploader...")
        self.running = False
        
        if self.upload_thread:
            self.upload_thread.join(timeout=10)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get upload statistics."""
        pending_count = len(list(self.pending_dir.glob('*')))
        inflight_count = len(list(self.inflight_dir.glob('*')))
        archived_count = len(list(self.archived_dir.glob('*')))
        
        return {
            **self.upload_stats,
            'pending_chunks': pending_count,
            'inflight_chunks': inflight_count,
            'archived_chunks': archived_count,
            'queue_size': self.upload_queue.qsize()
        }

