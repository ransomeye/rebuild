# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/engine/graph_builder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Maintains active graph state, merges duplicate nodes, updates timestamps, groups connected components into incidents

import networkx as nx
from datetime import datetime
from typing import List, Dict, Any, Set
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphBuilder:
    """
    Builds and maintains threat correlation graph.
    """
    
    def __init__(self):
        """Initialize graph builder."""
        self.graph = nx.Graph()
        self.node_metadata = {}  # node_id -> metadata
        self.edge_metadata = {}  # (node1, node2) -> metadata
    
    def add_entities(self, entities: List[Dict[str, Any]], alert: Dict[str, Any]):
        """
        Add entities to graph.
        
        Args:
            entities: List of entity dictionaries
            alert: Alert dictionary
        """
        if not entities:
            return
        
        # Add nodes
        for entity in entities:
            node_id = entity['id']
            
            # Add or update node
            if node_id not in self.graph:
                self.graph.add_node(node_id, **entity)
                self.node_metadata[node_id] = {
                    'first_seen': alert.get('timestamp', datetime.utcnow().isoformat()),
                    'last_seen': alert.get('timestamp', datetime.utcnow().isoformat()),
                    'alert_count': 1
                }
            else:
                # Update existing node
                self.node_metadata[node_id]['last_seen'] = alert.get('timestamp', datetime.utcnow().isoformat())
                self.node_metadata[node_id]['alert_count'] += 1
        
        # Add edges between entities (fully connected within alert)
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                edge_key = (entity1['id'], entity2['id'])
                
                if not self.graph.has_edge(entity1['id'], entity2['id']):
                    # Create new edge
                    self.graph.add_edge(entity1['id'], entity2['id'])
                    self.edge_metadata[edge_key] = {
                        'first_seen': alert.get('timestamp', datetime.utcnow().isoformat()),
                        'last_seen': alert.get('timestamp', datetime.utcnow().isoformat()),
                        'alert_count': 1,
                        'alert_ids': [alert.get('id', 'unknown')]
                    }
                else:
                    # Update existing edge
                    self.edge_metadata[edge_key]['last_seen'] = alert.get('timestamp', datetime.utcnow().isoformat())
                    self.edge_metadata[edge_key]['alert_count'] += 1
                    if alert.get('id') not in self.edge_metadata[edge_key]['alert_ids']:
                        self.edge_metadata[edge_key]['alert_ids'].append(alert.get('id', 'unknown'))
        
        logger.debug(f"Added {len(entities)} entities to graph")
    
    def correlate_incidents(self) -> List[Dict[str, Any]]:
        """
        Group connected components into incidents.
        
        Returns:
            List of incident dictionaries
        """
        incidents = []
        
        # Find connected components
        components = list(nx.connected_components(self.graph))
        
        for component_id, component_nodes in enumerate(components):
            if not component_nodes:
                continue
            
            # Calculate incident metadata
            first_seen = None
            last_seen = None
            total_alerts = 0
            entity_types = set()
            
            for node_id in component_nodes:
                node_meta = self.node_metadata.get(node_id, {})
                if node_meta:
                    node_first = node_meta.get('first_seen')
                    node_last = node_meta.get('last_seen')
                    total_alerts += node_meta.get('alert_count', 0)
                    
                    if node_first:
                        if first_seen is None or node_first < first_seen:
                            first_seen = node_first
                    if node_last:
                        if last_seen is None or node_last > last_seen:
                            last_seen = node_last
                
                # Get entity type
                if node_id in self.graph.nodes:
                    node_data = self.graph.nodes[node_id]
                    entity_types.add(node_data.get('type', 'Unknown'))
            
            incident = {
                'id': f"incident_{component_id}_{len(component_nodes)}",
                'node_count': len(component_nodes),
                'edge_count': self.graph.subgraph(component_nodes).number_of_edges(),
                'first_seen': first_seen or datetime.utcnow().isoformat(),
                'last_seen': last_seen or datetime.utcnow().isoformat(),
                'total_alerts': total_alerts,
                'entity_types': list(entity_types),
                'node_ids': list(component_nodes)
            }
            
            incidents.append(incident)
        
        logger.info(f"Correlated {len(incidents)} incidents from graph")
        return incidents
    
    def get_graph_state(self) -> Dict[str, Any]:
        """
        Get current graph state.
        
        Returns:
            Graph state dictionary
        """
        return {
            'nodes': list(self.graph.nodes(data=True)),
            'edges': list(self.graph.edges(data=True)),
            'node_metadata': self.node_metadata,
            'edge_metadata': self.edge_metadata
        }
    
    def load_graph_state(self, state: Dict[str, Any]):
        """
        Load graph state.
        
        Args:
            state: Graph state dictionary
        """
        self.graph = nx.Graph()
        
        # Load nodes
        for node_id, node_data in state.get('nodes', []):
            self.graph.add_node(node_id, **node_data)
        
        # Load edges
        for edge in state.get('edges', []):
            if len(edge) >= 2:
                self.graph.add_edge(edge[0], edge[1], **edge[2] if len(edge) > 2 else {})
        
        # Load metadata
        self.node_metadata = state.get('node_metadata', {})
        self.edge_metadata = state.get('edge_metadata', {})

