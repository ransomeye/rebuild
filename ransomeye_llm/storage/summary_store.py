# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/storage/summary_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Local file storage for generated reports

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummaryStore:
    """
    Manages storage of generated reports.
    """
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize summary store.
        
        Args:
            storage_dir: Base directory for report storage
        """
        self.storage_dir = Path(storage_dir or os.environ.get(
            'REPORT_STORAGE_DIR',
            '/home/ransomeye/rebuild/ransomeye_llm/storage/reports'
        ))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Summary store initialized at: {self.storage_dir}")
    
    def store_report(self, job_id: str, pdf_path: Path, html_path: Path = None,
                    csv_path: Path = None, manifest_path: Path = None,
                    signature_path: Path = None, metadata: Dict[str, Any] = None) -> Dict[str, Path]:
        """
        Store all report files.
        
        Args:
            job_id: Job identifier
            pdf_path: Path to PDF file
            html_path: Optional path to HTML file
            csv_path: Optional path to CSV file
            manifest_path: Optional path to manifest file
            signature_path: Optional path to signature file
            metadata: Optional metadata dictionary
            
        Returns:
            Dictionary of file types to stored paths
        """
        job_dir = self.storage_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        stored_paths = {}
        
        # Copy PDF
        stored_pdf = job_dir / "report.pdf"
        shutil.copy2(pdf_path, stored_pdf)
        stored_paths['pdf'] = stored_pdf
        
        # Copy HTML if provided
        if html_path and Path(html_path).exists():
            stored_html = job_dir / "report.html"
            shutil.copy2(html_path, stored_html)
            stored_paths['html'] = stored_html
        
        # Copy CSV if provided
        if csv_path and Path(csv_path).exists():
            stored_csv = job_dir / "report.csv"
            shutil.copy2(csv_path, stored_csv)
            stored_paths['csv'] = stored_csv
        
        # Copy manifest if provided
        if manifest_path and Path(manifest_path).exists():
            stored_manifest = job_dir / "manifest.json"
            shutil.copy2(manifest_path, stored_manifest)
            stored_paths['manifest'] = stored_manifest
        
        # Copy signature if provided
        if signature_path and Path(signature_path).exists():
            stored_sig = job_dir / "manifest.sig"
            shutil.copy2(signature_path, stored_sig)
            stored_paths['signature'] = stored_sig
        
        # Save metadata
        if metadata:
            metadata_path = job_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            stored_paths['metadata'] = metadata_path
        
        logger.info(f"Report stored for job {job_id} in {job_dir}")
        return stored_paths
    
    def save_html(self, job_id: str, html_content: str) -> Path:
        """
        Save HTML content to file.
        
        Args:
            job_id: Job identifier
            html_content: HTML content string
            
        Returns:
            Path to saved HTML file
        """
        job_dir = self.storage_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        html_path = job_dir / "report.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_path
    
    def get_report_paths(self, job_id: str) -> Optional[Dict[str, Path]]:
        """
        Get paths to stored report files.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary of file types to paths, or None if not found
        """
        job_dir = self.storage_dir / job_id
        
        if not job_dir.exists():
            return None
        
        paths = {}
        
        # Check for each file type
        if (job_dir / "report.pdf").exists():
            paths['pdf'] = job_dir / "report.pdf"
        if (job_dir / "report.html").exists():
            paths['html'] = job_dir / "report.html"
        if (job_dir / "report.csv").exists():
            paths['csv'] = job_dir / "report.csv"
        if (job_dir / "manifest.json").exists():
            paths['manifest'] = job_dir / "manifest.json"
        if (job_dir / "manifest.sig").exists():
            paths['signature'] = job_dir / "manifest.sig"
        if (job_dir / "metadata.json").exists():
            paths['metadata'] = job_dir / "metadata.json"
        
        return paths if paths else None
    
    def get_report_bundle_path(self, job_id: str) -> Optional[Path]:
        """
        Get path to report bundle (tar.gz) if it exists.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Path to bundle file, or None
        """
        bundle_path = self.storage_dir / f"{job_id}_bundle.tar.gz"
        return bundle_path if bundle_path.exists() else None

