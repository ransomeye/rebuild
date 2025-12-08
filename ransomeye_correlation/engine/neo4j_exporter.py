# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/engine/neo4j_exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Exports graph to Neo4j-compatible CSV format (nodes.csv and relationships.csv)

import csv
import tarfile
from pathlib import Path
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jExporter:
    """
    Exports graph to Neo4j-compatible CSV format.
    """
    
    def __init__(self):
        """Initialize Neo4j exporter."""
        pass
    
    def export_incident(self, incident_id: str) -> Path:
        """
        Export incident graph to Neo4j format.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Path to export directory
        """
        from ..engine.graph_store import GraphStore
        
        graph_store = GraphStore()
        graph_data = graph_store.get_incident_graph(incident_id)
        
        # Create export directory
        export_dir = Path(f"/tmp/neo4j_export_{incident_id}")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Export nodes.csv
        nodes_file = export_dir / "nodes.csv"
        with open(nodes_file, 'w', newline='') as f:
            writer = csv.writer(f)
            # Neo4j header format: id:ID, type, label
            writer.writerow(['id:ID', 'type', 'label'])
            
            for node in graph_data.get('nodes', []):
                writer.writerow([
                    node['id'],
                    node['type'],
                    node['label']
                ])
        
        # Export relationships.csv
        relationships_file = export_dir / "relationships.csv"
        with open(relationships_file, 'w', newline='') as f:
            writer = csv.writer(f)
            # Neo4j header format: :START_ID, :END_ID, type
            writer.writerow([':START_ID', ':END_ID', 'type'])
            
            for edge in graph_data.get('edges', []):
                writer.writerow([
                    edge['start_id'],
                    edge['end_id'],
                    'RELATED_TO'
                ])
        
        # Create manifest
        manifest = {
            'incident_id': incident_id,
            'node_count': len(graph_data.get('nodes', [])),
            'edge_count': len(graph_data.get('edges', [])),
            'export_format': 'neo4j_bulk_import'
        }
        
        import json
        manifest_file = export_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Exported incident {incident_id} to Neo4j format: {export_dir}")
        return export_dir

