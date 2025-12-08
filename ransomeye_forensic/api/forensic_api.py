# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/api/forensic_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for forensic capture and ledger verification on port 8006

import os
import sys
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..capture.dumper import MemoryDumper
from ..capture.chunker import StreamChunker
from ..capture.compressor import StreamCompressor
from ..capture.pii_redactor import PIIRedactor
from ..ledger.evidence_ledger import EvidenceLedger
from ..ledger.manifest_signer import ManifestSigner
from ..storage.artifact_store import ArtifactStore
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
dumper = MemoryDumper()
chunker = StreamChunker()
compressor = StreamCompressor()
redactor = PIIRedactor()
ledger = EvidenceLedger()
signer = ManifestSigner()
store = ArtifactStore()

# Create FastAPI app
app = FastAPI(
    title="RansomEye Forensic Engine API",
    description="Forensic capture and evidence management API",
    version="1.0.0"
)

# Request/Response models
class CaptureRequest(BaseModel):
    """Memory capture request model."""
    capture_type: str = "memory"  # memory or disk
    device: Optional[str] = None  # For disk capture
    pii_redact: bool = False

class CaptureResponse(BaseModel):
    """Capture response model."""
    artifact_id: str
    status: str
    chunks: int
    total_hash: str
    ledger_hash: str

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye Forensic Engine API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    chain_valid = ledger.verify_chain()
    return {
        "status": "healthy",
        "ledger_valid": chain_valid
    }

@app.post("/capture/memory")
async def capture_memory(request: CaptureRequest):
    """
    Capture system memory.
    
    Args:
        request: Capture request
        
    Returns:
        Capture results with artifact ID
    """
    try:
        # Generate artifact ID
        artifact_id = str(uuid.uuid4())
        
        # Create temporary output path
        temp_dir = Path(f"/tmp/forensic_{artifact_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_output = temp_dir / "memory.raw"
        
        # Capture memory
        capture_result = dumper.capture_memory(temp_output)
        
        if not capture_result.get('success'):
            raise HTTPException(
                status_code=500,
                detail="Memory capture failed"
            )
        
        # Process artifact: chunk, compress, optionally redact
        chunk_hashes = []
        chunks_stored = []
        total_hash = hashlib.sha256()
        
        # Apply PII redaction if enabled (for text files, this is a simplified example)
        if request.pii_redact:
            # For binary memory dumps, PII redaction would need special handling
            logger.info("PII redaction requested (not applicable to raw memory dumps)")
        
        # Chunk file and process each chunk
        for chunk_idx, chunk_data, chunk_hash in chunker.chunk_file(temp_output):
            # Update total hash (hash of uncompressed data)
            total_hash.update(chunk_data)
            
            # Compress chunk
            compressed_chunks = list(compressor.compress_stream([chunk_data]))
            compressed_data = b''.join(compressed_chunks)
            
            # Store compressed chunk
            store.store_chunk(artifact_id, chunk_idx, compressed_data)
            chunk_hashes.append(chunk_hash)
            chunks_stored.append(chunk_idx)
        
        total_hash_str = total_hash.hexdigest()
        
        # Add to ledger
        ledger_hash = ledger.append_entry(
            artifact_id=artifact_id,
            artifact_type="memory",
            artifact_path=str(temp_output),
            chunk_hashes=chunk_hashes,
            total_hash=total_hash_str,
            metadata={
                'method': capture_result.get('method', 'unknown'),
                'size': capture_result.get('size', 0),
                'chunks': len(chunks_stored)
            }
        )
        
        # Sign ledger entry
        entry = ledger.get_entry_by_artifact_id(artifact_id)
        if entry:
            signature = signer.sign_entry(entry)
            # Store signature (in production, might append to ledger or separate file)
        
        # Clean up temp file
        temp_output.unlink()
        temp_dir.rmdir()
        
        logger.info(f"Memory capture completed: {artifact_id}")
        
        return {
            "artifact_id": artifact_id,
            "status": "captured",
            "chunks": len(chunks_stored),
            "total_hash": total_hash_str,
            "ledger_hash": ledger_hash
        }
        
    except Exception as e:
        logger.error(f"Error capturing memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/ledger/verify")
async def verify_ledger():
    """
    Verify the integrity of the evidence ledger.
    
    Returns:
        Verification results
    """
    try:
        is_valid = ledger.verify_chain()
        
        if is_valid:
            entries = ledger.get_entries(limit=10)
            return {
                "valid": True,
                "message": "Ledger chain is valid",
                "recent_entries": len(entries)
            }
        else:
            return {
                "valid": False,
                "message": "Ledger chain verification failed"
            }
        
    except Exception as e:
        logger.error(f"Error verifying ledger: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/ledger/entries")
async def get_ledger_entries(limit: Optional[int] = 10):
    """
    Get ledger entries.
    
    Args:
        limit: Maximum number of entries to return
        
    Returns:
        List of ledger entries
    """
    try:
        entries = ledger.get_entries(limit=limit)
        return {
            "entries": entries,
            "count": len(entries)
        }
    except Exception as e:
        logger.error(f"Error getting ledger entries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    import hashlib
    
    host = os.environ.get('FORENSIC_API_HOST', '0.0.0.0')
    port = int(os.environ.get('FORENSIC_PORT', 8006))
    
    uvicorn.run(app, host=host, port=port)

