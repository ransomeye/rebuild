# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/topology/topology_exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Exports NetworkX graph to JSON format ({nodes: [], links: []})

import networkx as nx
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopologyExporter:
    """
    Exports topology graph to JSON format.
    """
    
    def __init__(self):
        """Initialize topology exporter."""
        pass
    
    def export_graph(self, graph: nx.Graph) -> Dict[str, Any]:
        """
        Export graph to JSON format.
        
        Args:
            graph: NetworkX graph
            
        Returns:
            Dictionary with nodes and links
        """
        nodes = []
        links = []
        
        # Export nodes
        for node_id, node_data in graph.nodes(data=True):
            nodes.append({
                'id': node_id,
                'type': node_data.get('type', 'Unknown'),
                'ip': node_data.get('ip', ''),
                'hostname': node_data.get('hostname', ''),
                'mac': node_data.get('mac', ''),
                'vendor': node_data.get('vendor', ''),
                'services': node_data.get('services', 0),
                'vulnerabilities': node_data.get('vulnerabilities', 0)
            })
        
        # Export links (edges)
        for source, target, edge_data in graph.edges(data=True):
            links.append({
                'source': source,
                'target': target,
                'type': edge_data.get('type', 'unknown'),
                'subnet': edge_data.get('subnet', '')
            })
        
        return {
            'nodes': nodes,
            'links': links
        }

