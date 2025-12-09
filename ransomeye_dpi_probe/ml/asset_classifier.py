# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/ml/asset_classifier.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: ML-based flow classifier for detecting C2 beaconing, data exfiltration, and other malicious patterns

import os
import pickle
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from .shap_support import SHAPExplainer

logger = logging.getLogger(__name__)


class AssetClassifier:
    """ML-based flow classifier for threat detection."""
    
    # Feature names for flow classification
    FEATURE_NAMES = [
        'packet_count',
        'total_bytes',
        'duration_seconds',
        'bytes_per_packet_avg',
        'packets_per_second',
        'bytes_per_second',
        'src_port',
        'dst_port',
        'protocol_tcp',
        'protocol_udp',
        'protocol_icmp',
        'syn_count',
        'ack_count',
        'fin_count',
        'rst_count',
        'inter_arrival_time_mean',
        'inter_arrival_time_std',
        'packet_size_mean',
        'packet_size_std',
        'payload_entropy',
        'payload_ratio',
        'connection_duration_short',
        'connection_duration_long',
        'bytes_ratio_sent_recv',
        'unique_dst_ports',
        'unique_dst_ips'
    ]
    
    # Class labels
    CLASS_LABELS = ['normal', 'c2_beaconing', 'data_exfiltration', 'port_scan', 'malicious']
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize classifier.
        
        Args:
            model_path: Path to saved model pickle file
        """
        self.model_path = model_path or os.environ.get(
            'MODEL_DIR', 
            '/home/ransomeye/rebuild/models'
        )
        
        model_file = Path(self.model_path) / 'asset_classifier.pkl'
        scaler_file = Path(self.model_path) / 'asset_classifier_scaler.pkl'
        
        if model_file.exists() and scaler_file.exists():
            try:
                with open(model_file, 'rb') as f:
                    self.model = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info(f"Loaded classifier from {model_file}")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self._init_default_model()
        else:
            logger.warning(f"Model not found at {model_file}, initializing default model")
            self._init_default_model()
        
        # Initialize SHAP explainer
        try:
            self.shap_explainer = SHAPExplainer(self.model, self.FEATURE_NAMES)
        except Exception as e:
            logger.warning(f"Could not initialize SHAP explainer: {e}")
            self.shap_explainer = None
    
    def _init_default_model(self):
        """Initialize default untrained model."""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        
        # Train with dummy data to initialize
        dummy_X = np.random.rand(10, len(self.FEATURE_NAMES))
        dummy_y = np.random.randint(0, len(self.CLASS_LABELS), 10)
        self.scaler.fit(dummy_X)
        X_scaled = self.scaler.transform(dummy_X)
        self.model.fit(X_scaled, dummy_y)
        logger.info("Initialized default untrained model")
    
    def extract_features(self, flow_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract features from flow data.
        
        Args:
            flow_data: Flow statistics dictionary
            
        Returns:
            Feature vector
        """
        features = []
        
        # Basic statistics
        features.append(float(flow_data.get('total_packets', 0)))
        features.append(float(flow_data.get('total_bytes', 0)))
        features.append(float(flow_data.get('duration_seconds', 0)))
        
        # Derived metrics
        total_packets = flow_data.get('total_packets', 1)
        total_bytes = flow_data.get('total_bytes', 1)
        duration = max(flow_data.get('duration_seconds', 1), 0.1)
        
        features.append(total_bytes / total_packets if total_packets > 0 else 0)
        features.append(total_packets / duration)
        features.append(total_bytes / duration)
        
        # Ports
        features.append(float(flow_data.get('src_port', 0)))
        features.append(float(flow_data.get('dst_port', 0)))
        
        # Protocol encoding
        protocol = flow_data.get('protocol', '').upper()
        features.append(1.0 if protocol == 'TCP' else 0.0)
        features.append(1.0 if protocol == 'UDP' else 0.0)
        features.append(1.0 if protocol == 'ICMP' else 0.0)
        
        # TCP flags
        flags = flow_data.get('flags', [])
        features.append(1.0 if 'SYN' in flags else 0.0)
        features.append(1.0 if 'ACK' in flags else 0.0)
        features.append(1.0 if 'FIN' in flags else 0.0)
        features.append(1.0 if 'RST' in flags else 0.0)
        
        # Timing features (if available)
        inter_arrival_times = flow_data.get('inter_arrival_times', [])
        if inter_arrival_times:
            features.append(float(np.mean(inter_arrival_times)))
            features.append(float(np.std(inter_arrival_times)))
        else:
            features.append(0.0)
            features.append(0.0)
        
        # Packet size statistics (if available)
        packet_sizes = flow_data.get('packet_sizes', [])
        if packet_sizes:
            features.append(float(np.mean(packet_sizes)))
            features.append(float(np.std(packet_sizes)))
        else:
            features.append(0.0)
            features.append(0.0)
        
        # Payload features
        payload_size = flow_data.get('payload_size', 0)
        features.append(float(flow_data.get('payload_entropy', 0.0)))
        features.append(payload_size / total_bytes if total_bytes > 0 else 0.0)
        
        # Connection duration categories
        features.append(1.0 if duration < 1.0 else 0.0)  # Short
        features.append(1.0 if duration > 60.0 else 0.0)  # Long
        
        # Byte ratio
        bytes_sent = flow_data.get('bytes_sent', 1)
        bytes_recv = flow_data.get('bytes_recv', 1)
        features.append(bytes_sent / bytes_recv if bytes_recv > 0 else 0.0)
        
        # Unique destinations (if available)
        features.append(float(flow_data.get('unique_dst_ports', 1)))
        features.append(float(flow_data.get('unique_dst_ips', 1)))
        
        return np.array(features)
    
    def classify(self, flow_data: Dict[str, Any], generate_shap: bool = True) -> Dict[str, Any]:
        """
        Classify a flow.
        
        Args:
            flow_data: Flow statistics dictionary
            generate_shap: Whether to generate SHAP explanation
            
        Returns:
            Classification result with SHAP explanation
        """
        try:
            # Extract features
            features = self.extract_features(flow_data)
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            
            # Predict
            prediction = self.model.predict(features_scaled)[0]
            prediction_proba = self.model.predict_proba(features_scaled)[0]
            
            result = {
                'flow_id': flow_data.get('flow_id', 'unknown'),
                'prediction': int(prediction),
                'prediction_label': self.CLASS_LABELS[prediction],
                'confidence': float(max(prediction_proba)),
                'probabilities': {
                    label: float(prob) 
                    for label, prob in zip(self.CLASS_LABELS, prediction_proba)
                }
            }
            
            # Generate SHAP explanation
            if generate_shap and self.shap_explainer:
                try:
                    shap_explanation = self.shap_explainer.explain(features_scaled)
                    result['shap_explanation'] = shap_explanation
                except Exception as e:
                    logger.error(f"Error generating SHAP explanation: {e}")
                    result['shap_explanation'] = {'error': str(e)}
            else:
                result['shap_explanation'] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Error classifying flow: {e}")
            return {
                'flow_id': flow_data.get('flow_id', 'unknown'),
                'error': str(e),
                'prediction': None
            }
    
    def classify_batch(self, flows: List[Dict[str, Any]], generate_shap: bool = False) -> List[Dict[str, Any]]:
        """
        Classify multiple flows.
        
        Args:
            flows: List of flow statistics dictionaries
            generate_shap: Whether to generate SHAP for each
            
        Returns:
            List of classification results
        """
        results = []
        for flow in flows:
            result = self.classify(flow, generate_shap=generate_shap)
            results.append(result)
        return results
    
    def save_model(self, model_dir: Optional[str] = None):
        """Save model to disk."""
        model_dir = Path(model_dir or self.model_path)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_file = model_dir / 'asset_classifier.pkl'
        scaler_file = model_dir / 'asset_classifier_scaler.pkl'
        
        with open(model_file, 'wb') as f:
            pickle.dump(self.model, f)
        with open(scaler_file, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        logger.info(f"Saved classifier to {model_file}")

