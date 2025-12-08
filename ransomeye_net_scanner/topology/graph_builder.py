# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/topology/graph_builder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Builds NetworkX graph with Nodes (Assets) and Edges (Subnet membership or Observed Traffic)

import networkx as nx
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopologyGraphBuilder:
    """
    Builds network topology graph.
    """
    
    def __init__(self):
        """Initialize graph builder."""
        pass
    
    def build_graph(self) -> nx.Graph:
        """
        Build NetworkX graph from assets.
        
        Returns:
            NetworkX graph
        """
        from ..storage.asset_db import AssetDB
        
        asset_db = AssetDB()
        assets = asset_db.list_assets()
        
        graph = nx.Graph()
        
        # Add nodes (assets)
        for asset in assets:
            node_id = asset.get('id') or asset.get('mac') or asset.get('ip', 'unknown')
            
            # Determine node type
            node_type = 'Unknown'
            if asset.get('hostname'):
                if 'server' in asset.get('hostname', '').lower():
                    node_type = 'Server'
                elif 'router' in asset.get('hostname', '').lower() or 'gateway' in asset.get('hostname', '').lower():
                    node_type = 'Router'
                else:
                    node_type = 'PC'
            elif asset.get('vendor'):
                if 'cisco' in asset.get('vendor', '').lower():
                    node_type = 'Router'
                else:
                    node_type = 'PC'
            
            graph.add_node(node_id, **{
                'type': node_type,
                'ip': asset.get('ip', ''),
                'hostname': asset.get('hostname', ''),
                'mac': asset.get('mac', ''),
                'vendor': asset.get('vendor', ''),
                'services': len(asset.get('services', [])),
                'vulnerabilities': len(asset.get('vulnerabilities', []))
            })
        
        # Add edges (subnet membership)
        # Group assets by subnet
        subnet_groups = {}
        for asset in assets:
            ip = asset.get('ip', '')
            if ip:
                # Extract subnet (assume /24)
                subnet = '.'.join(ip.split('.')[:3]) + '.0/24'
                if subnet not in subnet_groups:
                    subnet_groups[subnet] = []
                subnet_groups[subnet].append(asset.get('id') or asset.get('mac') or ip)
        
        # Connect nodes in same subnet
        for subnet, node_ids in subnet_groups.items():
            for i, node1 in enumerate(node_ids):
                for node2 in node_ids[i+1:]:
                    if not graph.has_edge(node1, node2):
                        graph.add_edge(node1, node2, type='subnet', subnet=subnet)
        
        logger.info(f"Built topology graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        return graph

