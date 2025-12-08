# Path and File Name : /home/ransomeye/rebuild/ransomeye_killchain/engine/graph_exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates JSON Node/Edge graph for UI visualization (Nodes: IPs, Files; Edges: Events)

from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphExporter:
    """Exports timeline as JSON Node/Edge graph for visualization."""
    
    def __init__(self):
        """Initialize graph exporter."""
        pass
    
    def export_graph(self, timeline: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export timeline as JSON graph with nodes and edges.
        
        Args:
            timeline: Timeline dictionary
            
        Returns:
            Graph dictionary with nodes and edges
        """
        nodes = []
        edges = []
        node_map = {}  # Map entity to node index
        
        events = timeline.get('events', [])
        entities = timeline.get('entities', {})
        
        # Create nodes from entities
        for entity_id, entity_data in entities.items():
            node_id = len(nodes)
            node_map[entity_id] = node_id
            
            node = {
                'id': node_id,
                'label': entity_id,
                'type': entity_data.get('type', 'ip'),
                'properties': {
                    'first_seen': entity_data.get('first_seen'),
                    'last_seen': entity_data.get('last_seen'),
                    'event_count': entity_data.get('event_count', 0),
                    'max_severity': max(entity_data.get('severities', ['medium']), 
                                       key=lambda x: ['low', 'medium', 'high', 'critical'].index(x) if x in ['low', 'medium', 'high', 'critical'] else 0)
                }
            }
            nodes.append(node)
        
        # Create edges from events
        for event_idx, event in enumerate(events):
            source = event.get('source')
            target = event.get('target')
            
            if source in node_map and target in node_map:
                edge = {
                    'id': event_idx,
                    'source': node_map[source],
                    'target': node_map[target],
                    'label': event.get('alert_type', 'event'),
                    'properties': {
                        'timestamp': event.get('timestamp'),
                        'severity': event.get('severity'),
                        'mitre_ttp': event.get('mitre_ttp'),
                        'matches': event.get('matches', [])
                    }
                }
                edges.append(edge)
        
        graph = {
            'incident_id': timeline.get('incident_id'),
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'node_count': len(nodes),
                'edge_count': len(edges),
                'start_time': timeline.get('start_time'),
                'end_time': timeline.get('end_time')
            }
        }
        
        logger.info(f"Exported graph: {len(nodes)} nodes, {len(edges)} edges")
        return graph
    
    def export_to_json(self, timeline: Dict[str, Any], output_path: str = None) -> str:
        """
        Export graph to JSON string or file.
        
        Args:
            timeline: Timeline dictionary
            output_path: Optional path to save JSON file
            
        Returns:
            JSON string
        """
        import json
        
        graph = self.export_graph(timeline)
        json_str = json.dumps(graph, indent=2)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(json_str)
            logger.info(f"Graph exported to: {output_path}")
        
        return json_str

