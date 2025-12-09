# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/clusterer/clusterer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Groups related IOCs into Campaigns using unsupervised clustering (HDBSCAN or connected components)

import os
from typing import Dict, Any, List, Optional, Set
import logging

# Try to import clustering libraries
try:
    import numpy as np
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False
    logger.warning("scikit-learn not available. Using simple clustering")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IOCCampaignClusterer:
    """
    Clusters related IOCs into campaigns.
    Uses unsupervised clustering (HDBSCAN/DBSCAN) or connected components.
    """
    
    def __init__(self, min_cluster_size: int = 3):
        """
        Initialize clusterer.
        
        Args:
            min_cluster_size: Minimum size for a cluster
        """
        self.min_cluster_size = min_cluster_size
    
    def cluster(self, iocs: List[Dict[str, Any]]) -> Dict[int, List[str]]:
        """
        Cluster IOCs into campaigns.
        
        Args:
            iocs: List of IOC dictionaries
            
        Returns:
            Dictionary mapping campaign_id to list of IOC IDs
        """
        if len(iocs) < self.min_cluster_size:
            return {}
        
        # Method 1: Connected components based on shared tags/attributes
        campaigns = self._cluster_by_connected_components(iocs)
        
        # Method 2: If clustering available, use ML-based clustering
        if CLUSTERING_AVAILABLE and len(iocs) > 10:
            ml_campaigns = self._cluster_ml(iocs)
            # Merge campaigns
            campaigns = self._merge_campaigns(campaigns, ml_campaigns)
        
        logger.info(f"Clustered {len(iocs)} IOCs into {len(campaigns)} campaigns")
        return campaigns
    
    def _cluster_by_connected_components(self, iocs: List[Dict[str, Any]]) -> Dict[int, List[str]]:
        """
        Cluster IOCs using connected components based on shared tags/attributes.
        
        Args:
            iocs: List of IOC dictionaries
            
        Returns:
            Dictionary mapping campaign_id to list of IOC IDs
        """
        # Build graph of IOCs connected by shared tags
        ioc_ids = [ioc.get('id', str(i)) for i, ioc in enumerate(iocs)]
        tag_map: Dict[str, Set[int]] = {}  # tag -> set of IOC indices
        
        for i, ioc in enumerate(iocs):
            tags = ioc.get('tags', [])
            for tag in tags:
                if tag not in tag_map:
                    tag_map[tag] = set()
                tag_map[tag].add(i)
        
        # Find connected components
        visited = set()
        campaigns: Dict[int, List[str]] = {}
        campaign_id = 0
        
        for i in range(len(iocs)):
            if i in visited:
                continue
            
            # BFS to find connected component
            component = []
            queue = [i]
            visited.add(i)
            
            while queue:
                current = queue.pop(0)
                component.append(ioc_ids[current])
                
                # Find neighbors (IOCs sharing tags)
                current_tags = set(iocs[current].get('tags', []))
                for tag in current_tags:
                    neighbors = tag_map.get(tag, set())
                    for neighbor in neighbors:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
            
            # Only create campaign if size >= min_cluster_size
            if len(component) >= self.min_cluster_size:
                campaigns[campaign_id] = component
                campaign_id += 1
        
        return campaigns
    
    def _cluster_ml(self, iocs: List[Dict[str, Any]]) -> Dict[int, List[str]]:
        """
        Cluster IOCs using ML-based clustering (DBSCAN).
        
        Args:
            iocs: List of IOC dictionaries
            
        Returns:
            Dictionary mapping campaign_id to list of IOC IDs
        """
        if not CLUSTERING_AVAILABLE:
            return {}
        
        try:
            # Extract features
            features = []
            ioc_ids = []
            
            for ioc in iocs:
                # Feature vector: [type_encoded, tag_count, confidence, source_encoded]
                ioc_type = ioc.get('type', 'unknown')
                type_encoded = self._encode_type(ioc_type)
                tag_count = len(ioc.get('tags', []))
                confidence = ioc.get('confidence', 50) / 100.0
                source_encoded = hash(ioc.get('source', '')) % 100 / 100.0
                
                features.append([type_encoded, tag_count, confidence, source_encoded])
                ioc_ids.append(ioc.get('id', ''))
            
            if len(features) < self.min_cluster_size:
                return {}
            
            # Normalize features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # DBSCAN clustering
            clustering = DBSCAN(eps=0.5, min_samples=self.min_cluster_size)
            labels = clustering.fit_predict(features_scaled)
            
            # Group by cluster
            campaigns: Dict[int, List[str]] = {}
            for i, label in enumerate(labels):
                if label == -1:  # Noise
                    continue
                
                if label not in campaigns:
                    campaigns[label] = []
                campaigns[label].append(ioc_ids[i])
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Error in ML clustering: {e}")
            return {}
    
    def _encode_type(self, ioc_type: str) -> float:
        """Encode IOC type to numeric value."""
        type_map = {
            'ipv4': 0.1,
            'ipv6': 0.2,
            'domain': 0.3,
            'url': 0.4,
            'hash': 0.5,
            'email': 0.6,
            'unknown': 0.0
        }
        return type_map.get(ioc_type.lower(), 0.0)
    
    def _merge_campaigns(
        self,
        campaigns1: Dict[int, List[str]],
        campaigns2: Dict[int, List[str]]
    ) -> Dict[int, List[str]]:
        """
        Merge two campaign dictionaries.
        
        Args:
            campaigns1: First campaign dict
            campaigns2: Second campaign dict
            
        Returns:
            Merged campaigns
        """
        merged = campaigns1.copy()
        next_id = max(merged.keys(), default=-1) + 1
        
        for campaign_id, ioc_ids in campaigns2.items():
            # Check for overlap
            merged_into = None
            for existing_id, existing_iocs in merged.items():
                if set(ioc_ids) & set(existing_iocs):
                    merged_into = existing_id
                    break
            
            if merged_into is not None:
                # Merge into existing campaign
                merged[merged_into].extend([ioc_id for ioc_id in ioc_ids if ioc_id not in merged[merged_into]])
            else:
                # Create new campaign
                merged[next_id] = ioc_ids
                next_id += 1
        
        return merged

