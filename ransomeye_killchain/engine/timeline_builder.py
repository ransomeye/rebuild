# Path and File Name : /home/ransomeye/rebuild/ransomeye_killchain/engine/timeline_builder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Logic to ingest alerts and build timeline by sorting/correlating by timestamp and entity

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimelineBuilder:
    """Builds attack timeline from alerts by sorting and correlating events."""
    
    def __init__(self):
        """Initialize timeline builder."""
        pass
    
    def build_timeline(self, alerts: List[Dict[str, Any]], 
                      incident_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Build timeline from list of alerts.
        
        Args:
            alerts: List of alert dictionaries
            incident_id: Optional incident identifier
            
        Returns:
            Timeline dictionary with sorted events and correlations
        """
        if not alerts:
            return {
                'incident_id': incident_id,
                'events': [],
                'entities': {},
                'start_time': None,
                'end_time': None
            }
        
        # Parse and sort alerts by timestamp
        events = []
        for alert in alerts:
            event = self._parse_alert(alert)
            if event:
                events.append(event)
        
        # Sort by timestamp
        events.sort(key=lambda x: x.get('timestamp', ''))
        
        # Extract entities and correlate
        entities = self._extract_entities(events)
        correlations = self._correlate_events(events)
        
        # Get time range
        start_time = events[0].get('timestamp') if events else None
        end_time = events[-1].get('timestamp') if events else None
        
        timeline = {
            'incident_id': incident_id,
            'events': events,
            'entities': entities,
            'correlations': correlations,
            'start_time': start_time,
            'end_time': end_time,
            'event_count': len(events)
        }
        
        logger.info(f"Built timeline with {len(events)} events for incident {incident_id}")
        return timeline
    
    def _parse_alert(self, alert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse alert into timeline event.
        
        Args:
            alert: Alert dictionary
            
        Returns:
            Event dictionary or None
        """
        try:
            # Extract timestamp
            timestamp = alert.get('timestamp')
            if not timestamp:
                # Try to parse from various formats
                timestamp = datetime.utcnow().isoformat() + 'Z'
            
            event = {
                'timestamp': timestamp,
                'source': alert.get('source', 'unknown'),
                'target': alert.get('target', 'unknown'),
                'alert_type': alert.get('alert_type', 'unknown'),
                'severity': alert.get('severity', 'medium'),
                'matches': alert.get('matches', []),
                'metadata': alert.get('metadata', {})
            }
            
            return event
            
        except Exception as e:
            logger.warning(f"Failed to parse alert: {e}")
            return None
    
    def _extract_entities(self, events: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Extract entities (IPs, files, etc.) from events.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Dictionary of entities with their properties
        """
        entities = {}
        
        for event in events:
            # Extract source entity
            source = event.get('source')
            if source:
                if source not in entities:
                    entities[source] = {
                        'type': 'ip',  # Could be enhanced to detect type
                        'first_seen': event.get('timestamp'),
                        'last_seen': event.get('timestamp'),
                        'event_count': 0,
                        'severities': []
                    }
                else:
                    entities[source]['last_seen'] = event.get('timestamp')
                    entities[source]['event_count'] += 1
                    entities[source]['severities'].append(event.get('severity'))
            
            # Extract target entity
            target = event.get('target')
            if target and target != source:
                if target not in entities:
                    entities[target] = {
                        'type': 'ip',
                        'first_seen': event.get('timestamp'),
                        'last_seen': event.get('timestamp'),
                        'event_count': 0,
                        'severities': []
                    }
                else:
                    entities[target]['last_seen'] = event.get('timestamp')
                    entities[target]['event_count'] += 1
                    entities[target]['severities'].append(event.get('severity'))
        
        return entities
    
    def _correlate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Correlate events by entity relationships.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            List of correlation dictionaries
        """
        correlations = []
        
        # Group events by source-target pairs
        relationships = {}
        for event in events:
            source = event.get('source')
            target = event.get('target')
            
            if source and target:
                key = f"{source}->{target}"
                if key not in relationships:
                    relationships[key] = {
                        'source': source,
                        'target': target,
                        'events': [],
                        'first_seen': event.get('timestamp'),
                        'last_seen': event.get('timestamp')
                    }
                relationships[key]['events'].append(event)
                relationships[key]['last_seen'] = event.get('timestamp')
        
        # Convert to correlation list
        for rel in relationships.values():
            correlations.append({
                'source': rel['source'],
                'target': rel['target'],
                'event_count': len(rel['events']),
                'first_seen': rel['first_seen'],
                'last_seen': rel['last_seen']
            })
        
        return correlations

