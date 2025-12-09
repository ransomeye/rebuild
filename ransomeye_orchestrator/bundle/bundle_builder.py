# Path and File Name : /home/ransomeye/rebuild/ransomeye_orchestrator/bundle/bundle_builder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main bundle builder that fetches data and creates compressed bundles

import os
import sys
import json
import hashlib
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import tarfile

# Try to import zstandard, fallback to gzip
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    import gzip
    logging.warning("zstandard not available, using gzip compression")

import requests

from ransomeye_orchestrator.bundle.chunker import StreamingChunker
from ransomeye_orchestrator.bundle.manifest import ManifestGenerator
from ransomeye_orchestrator.bundle.signer import ManifestSigner

logger = logging.getLogger(__name__)


class BundleBuilder:
    """Main bundle builder that fetches data and creates compressed bundles."""
    
    def __init__(self):
        """Initialize bundle builder."""
        self.chunker = StreamingChunker()
        self.manifest_gen = ManifestGenerator()
        self.signer = None  # Initialize only if key available
        
        # Try to initialize signer
        sign_key_path = os.environ.get('ORCH_SIGN_KEY_PATH', '')
        if sign_key_path and os.path.exists(sign_key_path):
            try:
                self.signer = ManifestSigner(sign_key_path)
            except Exception as e:
                logger.warning(f"Signer initialization failed: {e}")
    
    def _get_api_url(self, service: str) -> str:
        """Get API URL for a service."""
        base_url = os.environ.get('CORE_API_URL', 'http://localhost:8080')
        
        service_ports = {
            'killchain': os.environ.get('KILLCHAIN_API_PORT', '8005'),
            'forensic': os.environ.get('FORENSIC_API_PORT', '8006'),
            'db': os.environ.get('DB_API_PORT', '8009')
        }
        
        if service in service_ports:
            return f"http://localhost:{service_ports[service]}"
        
        return base_url
    
    def _fetch_timeline(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Fetch timeline from KillChain API."""
        try:
            url = f"{self._get_api_url('killchain')}/api/v1/timeline/{incident_id}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch timeline: {e}")
            return None
    
    def _fetch_alerts(self, incident_id: str) -> list:
        """Fetch alerts from DB API."""
        try:
            url = f"{self._get_api_url('db')}/query/alerts"
            payload = {
                "correlation_id": incident_id,
                "limit": 10000
            }
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('alerts', [])
        except Exception as e:
            logger.warning(f"Failed to fetch alerts: {e}")
            return []
    
    def _fetch_artifacts(self, incident_id: str) -> list:
        """Fetch artifacts from Forensic API."""
        try:
            url = f"{self._get_api_url('forensic')}/api/v1/artifacts"
            params = {"incident_id": incident_id}
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get('artifacts', [])
        except Exception as e:
            logger.warning(f"Failed to fetch artifacts: {e}")
            return []
    
    def _copy_artifact_file(self, artifact: Dict[str, Any], dest_dir: Path) -> Optional[Dict[str, Any]]:
        """Copy artifact file to bundle directory."""
        file_path = artifact.get('filepath') or artifact.get('stored_path')
        if not file_path:
            logger.warning(f"Artifact missing file path: {artifact.get('artifact_id')}")
            return None
        
        # Decrypt path if needed (from Phase 10 encryption)
        # For now, assume path is already decrypted or stored in plain text
        source_path = Path(file_path)
        if not source_path.exists():
            logger.warning(f"Artifact file not found: {source_path}")
            return None
        
        # Create relative path in bundle
        artifact_id = artifact.get('artifact_id', 'unknown')
        rel_path = f"artifacts/{artifact_id}/{source_path.name}"
        dest_path = dest_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file and calculate hash
        sha256 = hashlib.sha256()
        with open(source_path, 'rb') as src, open(dest_path, 'wb') as dst:
            while True:
                chunk = src.read(64 * 1024)
                if not chunk:
                    break
                sha256.update(chunk)
                dst.write(chunk)
        
        file_hash = sha256.hexdigest()
        
        return {
            'path': rel_path,
            'size': dest_path.stat().st_size,
            'sha256': file_hash,
            'artifact_id': artifact_id
        }
    
    def create_bundle(
        self,
        incident_id: str,
        output_path: Optional[str] = None,
        chunk_size_mb: int = 256
    ) -> Dict[str, Any]:
        """
        Create bundle for an incident.
        
        Args:
            incident_id: Incident identifier
            output_path: Output path for bundle (default: auto-generated)
            chunk_size_mb: Chunk size in MB for large files
        
        Returns:
            Bundle information dictionary
        """
        logger.info(f"Creating bundle for incident: {incident_id}")
        
        # Create temp directory for bundle
        with tempfile.TemporaryDirectory(prefix=f"bundle_{incident_id}_") as temp_dir:
            temp_path = Path(temp_dir)
            bundle_dir = temp_path / "bundle"
            bundle_dir.mkdir()
            
            files_info = []
            
            # Fetch timeline
            logger.info("Fetching timeline...")
            timeline = self._fetch_timeline(incident_id)
            if timeline:
                timeline_path = bundle_dir / "timeline.json"
                with open(timeline_path, 'w') as f:
                    json.dump(timeline, f, indent=2)
                
                # Calculate hash
                with open(timeline_path, 'rb') as f:
                    timeline_hash = hashlib.sha256(f.read()).hexdigest()
                
                files_info.append({
                    'path': 'timeline.json',
                    'size': timeline_path.stat().st_size,
                    'sha256': timeline_hash
                })
            
            # Fetch alerts
            logger.info("Fetching alerts...")
            alerts = self._fetch_alerts(incident_id)
            if alerts:
                alerts_path = bundle_dir / "alerts.json"
                with open(alerts_path, 'w') as f:
                    json.dump(alerts, f, indent=2)
                
                with open(alerts_path, 'rb') as f:
                    alerts_hash = hashlib.sha256(f.read()).hexdigest()
                
                files_info.append({
                    'path': 'alerts.json',
                    'size': alerts_path.stat().st_size,
                    'sha256': alerts_hash
                })
            
            # Fetch and copy artifacts
            logger.info("Fetching artifacts...")
            artifacts = self._fetch_artifacts(incident_id)
            for artifact in artifacts:
                file_info = self._copy_artifact_file(artifact, bundle_dir)
                if file_info:
                    files_info.append(file_info)
            
            # Generate manifest
            logger.info("Generating manifest...")
            manifest = self.manifest_gen.generate_manifest(
                incident_id=incident_id,
                files=files_info,
                metadata={
                    'created_at': datetime.utcnow().isoformat() + "Z",
                    'file_count': len(files_info),
                    'compression': 'zstd' if ZSTD_AVAILABLE else 'gzip'
                }
            )
            
            manifest_path = bundle_dir / "manifest.json"
            self.manifest_gen.save_manifest(manifest, manifest_path)
            
            # Sign manifest
            if self.signer:
                logger.info("Signing manifest...")
                signature_path = bundle_dir / "manifest.sig"
                self.signer.save_signature(manifest, signature_path)
            else:
                logger.warning("Signer not available, skipping signature")
            
            # Create compressed archive
            logger.info("Creating compressed archive...")
            if output_path is None:
                output_dir = Path(os.environ.get('OUTPUT_DIR', '/home/ransomeye/rebuild/data'))
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"bundle_{incident_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            output_path = Path(output_path)
            
            if ZSTD_AVAILABLE:
                # Use zstandard compression
                archive_path = Path(str(output_path) + ".tar.zst")
                self._create_zstd_archive(bundle_dir, archive_path)
            else:
                # Use gzip compression
                archive_path = Path(str(output_path) + ".tar.gz")
                self._create_gzip_archive(bundle_dir, archive_path)
            
            # Calculate final bundle hash
            with open(archive_path, 'rb') as f:
                bundle_hash = hashlib.sha256(f.read()).hexdigest()
            
            bundle_size = archive_path.stat().st_size
            
            result = {
                'bundle_path': str(archive_path),
                'bundle_size': bundle_size,
                'bundle_hash': bundle_hash,
                'file_count': len(files_info),
                'compression': 'zstd' if ZSTD_AVAILABLE else 'gzip',
                'incident_id': incident_id
            }
            
            logger.info(f"Bundle created: {archive_path} ({bundle_size} bytes)")
            return result
    
    def _create_zstd_archive(self, source_dir: Path, output_path: Path):
        """Create zstandard compressed tar archive."""
        cctx = zstd.ZstdCompressor(level=3)
        
        with open(output_path, 'wb') as out_file:
            with cctx.stream_writer(out_file) as compressor:
                with tarfile.open(fileobj=compressor, mode='w|') as tar:
                    # Add all files in source_dir
                    for file_path in source_dir.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(source_dir)
                            tar.add(file_path, arcname=str(arcname))
    
    def _create_gzip_archive(self, source_dir: Path, output_path: Path):
        """Create gzip compressed tar archive."""
        with tarfile.open(output_path, 'w:gz') as tar:
            # Add all files in source_dir
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    tar.add(file_path, arcname=str(arcname))

