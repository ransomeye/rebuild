# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/tools/build_graph_snapshot.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to force snapshot creation for Neo4j

import argparse
import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_correlation.engine.neo4j_exporter import Neo4jExporter
from ransomeye_correlation.storage.incident_store import IncidentStore
from ransomeye_correlation.storage.manifest_signer import ManifestSigner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_snapshot(incident_id: str, output_path: Path):
    """
    Build graph snapshot for Neo4j.
    
    Args:
        incident_id: Incident identifier
        output_path: Output bundle path
    """
    # Initialize components
    incident_store = IncidentStore()
    neo4j_exporter = Neo4jExporter()
    manifest_signer = ManifestSigner()
    
    # Verify incident exists
    incident = incident_store.get_incident(incident_id)
    if not incident:
        logger.error(f"Incident not found: {incident_id}")
        return False
    
    # Export to Neo4j format
    export_dir = neo4j_exporter.export_incident(incident_id)
    
    # Sign the export
    signed_bundle = manifest_signer.sign_export(export_dir, incident_id)
    
    # Move to output path if specified
    if output_path and output_path != signed_bundle:
        import shutil
        shutil.move(str(signed_bundle), str(output_path))
        logger.info(f"Snapshot saved to: {output_path}")
    else:
        logger.info(f"Snapshot saved to: {signed_bundle}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Build graph snapshot for Neo4j')
    parser.add_argument('--incident-id', type=str, required=True,
                       help='Incident identifier')
    parser.add_argument('--output', type=str,
                       help='Output bundle path (optional)')
    
    args = parser.parse_args()
    
    try:
        output_path = Path(args.output) if args.output else None
        success = build_snapshot(args.incident_id, output_path)
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Error building snapshot: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())

