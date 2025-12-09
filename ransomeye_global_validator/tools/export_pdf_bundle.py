# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/tools/export_pdf_bundle.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Exports signed PDF report with proofs and manifest

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def export_bundle(run_id: str, output_dir: str = None):
    """
    Export validation run bundle (PDF + signature + manifest).
    
    Args:
        run_id: Run identifier
        output_dir: Output directory (default: current directory)
    """
    if output_dir is None:
        output_dir = os.getcwd()
    
    run_store_path = os.environ.get(
        'VALIDATOR_RUN_STORE_PATH',
        '/home/ransomeye/rebuild/ransomeye_global_validator/storage/runs'
    )
    
    run_store = Path(run_store_path)
    
    # Find files
    pdf_path = run_store / f"{run_id}_report.pdf"
    pdf_sig_path = run_store / f"{run_id}_report.pdf.sig"
    manifest_path = run_store / f"{run_id}_manifest.signed.json"
    
    if not pdf_path.exists():
        print(f"Error: PDF not found for run {run_id}")
        return
    
    # Create bundle
    bundle_name = f"validation_bundle_{run_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    bundle_path = Path(output_dir) / bundle_name
    
    with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add PDF
        zipf.write(pdf_path, f"{run_id}_report.pdf")
        
        # Add signature if exists
        if pdf_sig_path.exists():
            zipf.write(pdf_sig_path, f"{run_id}_report.pdf.sig")
        
        # Add manifest if exists
        if manifest_path.exists():
            zipf.write(manifest_path, f"{run_id}_manifest.signed.json")
    
    print(f"Bundle exported to: {bundle_path}")
    print(f"Bundle size: {bundle_path.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python export_pdf_bundle.py <run_id> [output_dir]")
        sys.exit(1)
    
    run_id = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    export_bundle(run_id, output_dir)

