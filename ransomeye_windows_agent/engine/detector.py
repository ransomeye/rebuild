# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/engine/detector.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Runs static rules and ML inference for threat detection with SHAP explainability

import os
from typing import Dict, Any, Optional
import logging

from ..models.inferencer import ModelInferencer
from ..models.shap_support import SHAPSupport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Detector:
    """Threat detection engine combining rules and ML."""
    
    def __init__(self):
        """Initialize detector."""
        self.inferencer = ModelInferencer()
        self.shap_support = SHAPSupport(self.inferencer)
        self.threshold = float(os.environ.get('DETECTION_THRESHOLD', '0.7'))
        
        # Static rules (Windows-specific)
        self.suspicious_extensions = [
            '.encrypted', '.locked', '.crypto', '.vault', '.ecc', '.ezz', '.exx', 
            '.xyz', '.aaa', '.micro', '.dharma', '.cobra', '.locky', '.cerber',
            '.petya', '.wannacry', '.ryuk', '.maze', '.sodinokibi'
        ]
        self.suspicious_process_names = [
            'encrypt', 'crypto', 'lock', 'ransom', 'wannacry', 'petya',
            'vssadmin', 'bcdedit', 'wbadmin', 'wmic', 'powershell'
        ]
        self.suspicious_paths = [
            'C:\\Windows\\Temp\\', 'C:\\Temp\\', 'C:\\Users\\', 
            'AppData\\Local\\Temp\\', 'AppData\\Roaming\\'
        ]
        self.suspicious_registry_keys = [
            'HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',
            'HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'
        ]
        
        logger.info(f"Detector initialized (threshold: {self.threshold})")
    
    def detect(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect threats in telemetry data.
        
        Args:
            telemetry: Telemetry data dictionary
            
        Returns:
            Detection result with threat_detected flag
        """
        result = {
            "threat_detected": False,
            "threat_type": None,
            "threat_score": 0.0,
            "ml_explanation": None,
            "shap_values": None,
            "metadata": {}
        }
        
        # Run static rules first
        rule_result = self._run_static_rules(telemetry)
        if rule_result.get("threat_detected"):
            result.update(rule_result)
            return result
        
        # Run ML inference
        ml_result = self._run_ml_inference(telemetry)
        if ml_result.get("threat_score", 0.0) >= self.threshold:
            result["threat_detected"] = True
            result["threat_type"] = "ml_detected"
            result["threat_score"] = ml_result.get("threat_score", 0.0)
            result["ml_explanation"] = ml_result.get("explanation")
            result["shap_values"] = ml_result.get("shap_values")
            result["metadata"] = ml_result.get("metadata", {})
        
        return result
    
    def _run_static_rules(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Run static detection rules."""
        result = {
            "threat_detected": False,
            "threat_type": None,
            "threat_score": 1.0,  # Static rules are high confidence
            "metadata": {}
        }
        
        # Check processes
        processes = telemetry.get("processes", [])
        for proc in processes:
            proc_name = proc.get("name", "").lower()
            exe = proc.get("exe", "").lower()
            cmdline = " ".join(proc.get("cmdline", [])).lower() if proc.get("cmdline") else ""
            
            # Check for suspicious process names
            for suspicious in self.suspicious_process_names:
                if suspicious in proc_name or suspicious in exe or suspicious in cmdline:
                    # Additional check: if it's a legitimate system tool, verify context
                    if suspicious in ['vssadmin', 'bcdedit', 'wbadmin', 'wmic']:
                        # Check if it's being used maliciously (e.g., deleting shadow copies)
                        if 'delete' in cmdline or 'shadows' in cmdline:
                            result["threat_detected"] = True
                            result["threat_type"] = "suspicious_process"
                            result["metadata"] = {
                                "pid": proc.get("pid"),
                                "name": proc.get("name"),
                                "exe": proc.get("exe"),
                                "cmdline": proc.get("cmdline", [])
                            }
                            return result
                    else:
                        result["threat_detected"] = True
                        result["threat_type"] = "suspicious_process"
                        result["metadata"] = {
                            "pid": proc.get("pid"),
                            "name": proc.get("name"),
                            "exe": proc.get("exe")
                        }
                        return result
        
        # Check files
        files = telemetry.get("files", [])
        for file_info in files:
            file_path = file_info.get("path", "").lower()
            
            # Check for suspicious extensions
            for ext in self.suspicious_extensions:
                if file_path.endswith(ext):
                    result["threat_detected"] = True
                    result["threat_type"] = "suspicious_file"
                    result["metadata"] = {
                        "file_path": file_info.get("path"),
                        "file_hash": file_info.get("hash_sha256")
                    }
                    return result
            
            # Check for suspicious paths
            for path in self.suspicious_paths:
                if path.lower() in file_path:
                    # Additional check: encrypted extension
                    for ext in self.suspicious_extensions:
                        if file_path.endswith(ext):
                            result["threat_detected"] = True
                            result["threat_type"] = "ransomware_file"
                            result["metadata"] = {
                                "file_path": file_info.get("path"),
                                "file_hash": file_info.get("hash_sha256")
                            }
                            return result
        
        # Check events for suspicious patterns
        events = telemetry.get("events", [])
        for event in events:
            event_id = event.get("event_id", 0)
            # Event 1102: Audit log cleared (suspicious)
            if event_id == 1102:
                result["threat_detected"] = True
                result["threat_type"] = "audit_log_cleared"
                result["metadata"] = {
                    "event_id": event_id,
                    "time": event.get("time")
                }
                return result
        
        return result
    
    def _run_ml_inference(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Run ML model inference."""
        try:
            # Extract features from telemetry
            features = self._extract_features(telemetry)
            
            # Run inference
            inference_result = self.inferencer.predict(features)
            
            # Generate SHAP explanation
            shap_result = self.shap_support.generate_explanation(features, inference_result)
            
            return {
                "threat_score": inference_result.get("threat_score", 0.0),
                "explanation": inference_result.get("explanation"),
                "shap_values": shap_result.get("feature_importance", {}),
                "metadata": {
                    "model_version": inference_result.get("model_version"),
                    "features_used": list(features.keys())
                }
            }
        
        except Exception as e:
            logger.error(f"ML inference error: {e}")
            return {
                "threat_score": 0.0,
                "explanation": f"Inference error: {str(e)}",
                "shap_values": None,
                "metadata": {}
            }
    
    def _extract_features(self, telemetry: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from telemetry for ML model."""
        features = {}
        
        processes = telemetry.get("processes", [])
        files = telemetry.get("files", [])
        network = telemetry.get("network", {})
        events = telemetry.get("events", [])
        
        # Process features
        features["process_count"] = float(len(processes))
        features["high_cpu_processes"] = float(sum(1 for p in processes if p.get("cpu_percent", 0) > 50))
        features["high_memory_processes"] = float(sum(1 for p in processes if p.get("memory_rss", 0) > 100 * 1024 * 1024))
        features["suspicious_process_names"] = float(sum(
            1 for p in processes 
            if any(susp in p.get("name", "").lower() for susp in self.suspicious_process_names)
        ))
        
        # File features
        features["file_count"] = float(len(files))
        features["suspicious_extensions"] = float(sum(
            1 for f in files 
            if any(f.get("path", "").lower().endswith(ext) for ext in self.suspicious_extensions)
        ))
        features["suspicious_paths"] = float(sum(
            1 for f in files 
            if any(path.lower() in f.get("path", "").lower() for path in self.suspicious_paths)
        ))
        
        # Network features
        connections = network.get("connections", [])
        features["connection_count"] = float(len(connections))
        features["established_connections"] = float(sum(
            1 for c in connections if c.get("status") == "ESTABLISHED"
        ))
        
        # Event features
        features["security_event_count"] = float(len(events))
        features["audit_log_cleared"] = float(sum(1 for e in events if e.get("event_id") == 1102))
        
        return features

