# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/loaders/shap_injector.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Formats raw SHAP JSON into natural language

import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SHAPInjector:
    """
    Formats SHAP values into natural language for inclusion in summaries.
    """
    
    def __init__(self):
        """Initialize SHAP injector."""
        pass
    
    def format_shap(self, shap_values: Dict[str, float]) -> str:
        """
        Format SHAP values into natural language.
        
        Args:
            shap_values: Dictionary of feature names to SHAP values
            
        Returns:
            Formatted text describing SHAP values
        """
        if not shap_values:
            return "No SHAP feature importance data available."
        
        # Sort by absolute value (importance)
        sorted_features = sorted(
            shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        text_parts = []
        text_parts.append("## AI Feature Importance Analysis")
        text_parts.append("")
        text_parts.append("The AI model flagged this incident based on the following feature importance:")
        text_parts.append("")
        
        # Top 5 most important features
        top_features = sorted_features[:5]
        
        for i, (feature, value) in enumerate(top_features, 1):
            importance_pct = abs(value) * 100
            direction = "increased" if value > 0 else "decreased"
            
            # Human-readable feature names
            feature_name = self._humanize_feature_name(feature)
            
            text_parts.append(
                f"{i}. **{feature_name}** ({importance_pct:.1f}% importance): "
                f"The {direction} value of this feature was a key indicator."
            )
        
        # Summary
        if len(sorted_features) > 5:
            text_parts.append("")
            text_parts.append(f"Additional {len(sorted_features) - 5} features were analyzed.")
        
        text_parts.append("")
        text_parts.append("These SHAP values indicate which features the AI model considered most important when classifying this incident.")
        
        return "\n".join(text_parts)
    
    def _humanize_feature_name(self, feature: str) -> str:
        """
        Convert feature name to human-readable format.
        
        Args:
            feature: Feature name (e.g., "packet_size", "src_port")
            
        Returns:
            Human-readable name
        """
        # Common mappings
        mappings = {
            'packet_size': 'Packet Size',
            'src_port': 'Source Port',
            'dst_port': 'Destination Port',
            'protocol': 'Protocol',
            'duration': 'Connection Duration',
            'bytes_sent': 'Bytes Sent',
            'bytes_received': 'Bytes Received',
            'packet_count': 'Packet Count',
            'tcp_flags': 'TCP Flags',
            'http_method': 'HTTP Method',
            'user_agent': 'User Agent',
            'uri': 'URI',
            'status_code': 'HTTP Status Code'
        }
        
        # Try direct mapping
        if feature in mappings:
            return mappings[feature]
        
        # Try to format snake_case to Title Case
        if '_' in feature:
            words = feature.split('_')
            return ' '.join(word.capitalize() for word in words)
        
        # Capitalize first letter
        return feature.capitalize()
    
    def format_shap_for_table(self, shap_values: Dict[str, float], limit: int = 10) -> list:
        """
        Format SHAP values for table display.
        
        Args:
            shap_values: Dictionary of feature names to SHAP values
            limit: Maximum number of features to include
            
        Returns:
            List of dictionaries for table rows
        """
        if not shap_values:
            return []
        
        sorted_features = sorted(
            shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:limit]
        
        rows = []
        for feature, value in sorted_features:
            rows.append({
                'feature': self._humanize_feature_name(feature),
                'value': value,
                'importance': abs(value) * 100
            })
        
        return rows

