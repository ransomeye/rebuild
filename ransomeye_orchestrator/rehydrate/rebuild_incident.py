# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/rehydrate/rebuild_incident.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main rehydration logic with verification and unpacking

import os
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import tarfile

# Try to import zstandard
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    import gzip

from ransomeye_orchestrator.bundle.verifier import BundleVerifier
from ransomeye_orchestrator.bundle.manifest import ManifestGenerator
from ransomeye_orchestrator.rehydrate.state_reconciler import StateReconciler
from ransomeye_orchestrator.rehydrate.artifact_ingestor import ArtifactIngestor

logger = logging.getLogger(__name__)


class RebuildIncident:
    """Main rehydration logic: Verify -> Unpack -> Restore."""
    
    def __init__(self):
        """Initialize rehydrator."""
        self.verifier = None
        self.reconciler = StateReconciler()
        self.ingestor = ArtifactIngestor()
        
        # Try to initialize verifier
        verify_key_path = os.environ.get('ORCH_VERIFY_KEY_PATH', '')
        if verify_key_path and os.path.exists(verify_key_path):
            try:
                self.verifier = BundleVerifier(verify_key_path)
            except Exception as e:
                logger.warning(f"Verifier initialization failed: {e}")
    
    def rehydrate(
        self,
        bundle_path: str,
        verify_signature: bool = True,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rehydrate incident from bundle.
        
        Args:
            bundle_path: Path to bundle archive
            verify_signature: Whether to verify signature (fail-closed)
            idempotency_key: Optional idempotency key to prevent duplicates
        
        Returns:
            Rehydration result dictionary
        
        Raises:
            ValueError: If verification fails (fail-closed)
        """
        bundle_path = Path(bundle_path)
        
        if not bundle_path.exists():
            raise ValueError(f"Bundle not found: {bundle_path}")
        
        logger.info(f"Rehydrating incident from bundle: {bundle_path}")
        
        # Check idempotency
        if idempotency_key:
            if self.reconciler.check_idempotency(idempotency_key):
                logger.info(f"Rehydration already completed for idempotency key: {idempotency_key}")
                return {
                    'status': 'skipped',
                    'reason': 'idempotency_key_already_processed',
                    'idempotency_key': idempotency_key
                }
        
        # Extract bundle to temp directory
        with tempfile.TemporaryDirectory(prefix="rehydrate_") as temp_dir:
            temp_path = Path(temp_dir)
            bundle_dir = temp_path / "bundle"
            bundle_dir.mkdir()
            
            # Extract archive
            logger.info("Extracting bundle...")
            self._extract_bundle(bundle_path, bundle_dir)
            
            # Verify bundle
            if verify_signature:
                if not self.verifier:
                    raise ValueError("Signature verification requested but verifier not available")
                
                logger.info("Verifying bundle signature and integrity...")
                manifest_path = bundle_dir / "manifest.json"
                signature_path = bundle_dir / "manifest.sig"
                
                verification_result = self.verifier.verify_bundle(
                    bundle_dir,
                    manifest_path,
                    signature_path
                )
                logger.info(f"Bundle verification successful: {verification_result}")
            else:
                logger.warning("Signature verification skipped")
            
            # Load manifest
            manifest_path = bundle_dir / "manifest.json"
            if not manifest_path.exists():
                raise ValueError("Manifest not found in bundle")
            
            manifest = ManifestGenerator.load_manifest(manifest_path)
            incident_id = manifest.get('incident_id')
            
            # Restore timeline
            timeline_path = bundle_dir / "timeline.json"
            if timeline_path.exists():
                logger.info("Restoring timeline...")
                self.reconciler.restore_timeline(timeline_path, incident_id, idempotency_key)
            
            # Restore alerts
            alerts_path = bundle_dir / "alerts.json"
            if alerts_path.exists():
                logger.info("Restoring alerts...")
                self.reconciler.restore_alerts(alerts_path, incident_id, idempotency_key)
            
            # Restore artifacts
            artifacts_dir = bundle_dir / "artifacts"
            if artifacts_dir.exists():
                logger.info("Restoring artifacts...")
                self.ingestor.restore_artifacts(artifacts_dir, manifest, idempotency_key)
            
            # Record idempotency
            if idempotency_key:
                self.reconciler.record_idempotency(idempotency_key, incident_id)
            
            result = {
                'status': 'completed',
                'incident_id': incident_id,
                'files_restored': len(manifest.get('files', [])),
                'idempotency_key': idempotency_key
            }
            
            logger.info(f"Rehydration completed: {result}")
            return result
    
    def _extract_bundle(self, bundle_path: Path, output_dir: Path):
        """Extract bundle archive."""
        if bundle_path.suffix == '.zst' or bundle_path.suffixes[-2:] == ['.tar', '.zst']:
            if not ZSTD_AVAILABLE:
                raise ValueError("zstandard required for .zst bundles but not available")
            
            # Extract zstandard archive
            dctx = zstd.ZstdDecompressor()
            with open(bundle_path, 'rb') as in_file:
                with dctx.stream_reader(in_file) as reader:
                    with tarfile.open(fileobj=reader, mode='r|') as tar:
                        tar.extractall(output_dir)
        
        elif bundle_path.suffix == '.gz' or bundle_path.suffixes[-2:] == ['.tar', '.gz']:
            # Extract gzip archive
            with tarfile.open(bundle_path, 'r:gz') as tar:
                tar.extractall(output_dir)
        
        else:
            raise ValueError(f"Unsupported bundle format: {bundle_path.suffix}")

