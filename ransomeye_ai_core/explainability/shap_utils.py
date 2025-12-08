# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_core/explainability/shap_utils.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Helper functions to serialize numpy/SHAP objects to pure JSON

import json
import numpy as np
from typing import Any, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NumpyEncoder(json.JSONEncoder):
    """JSON encoder for numpy types."""
    
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        return super(NumpyEncoder, self).default(obj)

def serialize_shap_values(shap_values: Any) -> dict:
    """
    Serialize SHAP values to a JSON-serializable dictionary.
    
    Args:
        shap_values: SHAP values (can be various formats)
        
    Returns:
        Dictionary representation of SHAP values
    """
    try:
        # Handle numpy arrays
        if isinstance(shap_values, np.ndarray):
            return {
                'type': 'array',
                'shape': list(shap_values.shape),
                'values': shap_values.tolist()
            }
        
        # Handle lists
        elif isinstance(shap_values, list):
            serialized = []
            for item in shap_values:
                if isinstance(item, np.ndarray):
                    serialized.append(item.tolist())
                elif isinstance(item, (int, float, str, bool)):
                    serialized.append(item)
                else:
                    serialized.append(str(item))
            return {
                'type': 'list',
                'values': serialized
            }
        
        # Handle dictionaries
        elif isinstance(shap_values, dict):
            serialized = {}
            for key, value in shap_values.items():
                if isinstance(value, np.ndarray):
                    serialized[key] = value.tolist()
                elif isinstance(value, (int, float, str, bool, list)):
                    serialized[key] = value
                else:
                    serialized[key] = str(value)
            return {
                'type': 'dict',
                'values': serialized
            }
        
        # Handle scalars
        elif isinstance(shap_values, (int, float, str, bool)):
            return {
                'type': 'scalar',
                'value': shap_values
            }
        
        # Fallback to string representation
        else:
            return {
                'type': 'unknown',
                'value': str(shap_values)
            }
            
    except Exception as e:
        logger.error(f"Error serializing SHAP values: {e}")
        return {
            'type': 'error',
            'error': str(e)
        }

def shap_to_json(shap_explanation: dict) -> str:
    """
    Convert SHAP explanation dictionary to JSON string.
    
    Args:
        shap_explanation: Dictionary containing SHAP explanation
        
    Returns:
        JSON string representation
    """
    try:
        # Deep copy and serialize all numpy types
        serialized = json.loads(json.dumps(shap_explanation, cls=NumpyEncoder))
        return json.dumps(serialized, indent=2)
    except Exception as e:
        logger.error(f"Error converting SHAP to JSON: {e}")
        return json.dumps({'error': str(e)})

def format_shap_explanation(base_value: Union[float, np.ndarray],
                            shap_values: Any,
                            feature_names: list = None,
                            data: Any = None) -> dict:
    """
    Format SHAP explanation into a structured dictionary.
    
    Args:
        base_value: Base value (expected value)
        shap_values: SHAP values
        feature_names: Optional list of feature names
        data: Optional input data
        
    Returns:
        Structured dictionary ready for JSON serialization
    """
    explanation = {
        'base_value': float(base_value) if isinstance(base_value, (int, float, np.number)) else base_value.tolist() if isinstance(base_value, np.ndarray) else str(base_value),
        'shap_values': serialize_shap_values(shap_values),
        'features': {}
    }
    
    # Add feature names if provided
    if feature_names:
        explanation['feature_names'] = feature_names
    
    # Add data if provided
    if data is not None:
        if isinstance(data, np.ndarray):
            explanation['data'] = data.tolist()
        elif isinstance(data, list):
            explanation['data'] = data
        else:
            explanation['data'] = str(data)
    
    # Format feature contributions
    shap_serialized = serialize_shap_values(shap_values)
    if isinstance(shap_values, np.ndarray) and len(shap_values.shape) == 1:
        # Single prediction
        if feature_names and len(feature_names) == len(shap_values):
            for i, name in enumerate(feature_names):
                explanation['features'][name] = {
                    'value': float(shap_values[i]),
                    'contribution': float(shap_values[i])
                }
        else:
            for i, value in enumerate(shap_values):
                explanation['features'][f'feature_{i}'] = {
                    'value': float(value),
                    'contribution': float(value)
                }
    
    return explanation

