# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/engine/collector.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Collects process, network, and file telemetry using psutil and /proc

import os
import psutil
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelemetryCollector:
    """Collects system telemetry data."""
    
    def __init__(self, detector, persistence):
        """
        Initialize telemetry collector.
        
        Args:
            detector: Detector instance for analysis
            persistence: PersistenceManager instance for storage
        """
        self.detector = detector
        self.persistence = persistence
        self.collection_interval = float(os.environ.get('COLLECTION_INTERVAL', '5.0'))
        logger.info("Telemetry collector initialized")
    
    def collect_telemetry(self):
        """Collect all telemetry data."""
        try:
            # Collect process data
            processes = self._collect_processes()
            
            # Collect network data
            network = self._collect_network()
            
            # Collect file system data
            files = self._collect_files()
            
            # Combine into telemetry event
            telemetry = {
                "timestamp": datetime.utcnow().isoformat(),
                "hostname": os.uname().nodename,
                "processes": processes,
                "network": network,
                "files": files
            }
            
            # Run detection
            detection_result = self.detector.detect(telemetry)
            
            # If threat detected, generate alert
            if detection_result.get("threat_detected", False):
                alert = self._create_alert(telemetry, detection_result)
                self.persistence.save_event(alert)
                logger.warning(f"Threat detected: {detection_result.get('threat_type')}")
            else:
                # Save normal telemetry
                self.persistence.save_event(telemetry)
        
        except Exception as e:
            logger.error(f"Error collecting telemetry: {e}", exc_info=True)
    
    def _collect_processes(self) -> List[Dict[str, Any]]:
        """Collect process information."""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'cpu_percent', 
                                            'memory_info', 'open_files', 'connections', 'create_time']):
                try:
                    proc_info = proc.info
                    
                    # Calculate process hash
                    exe_path = proc_info.get('exe', '')
                    proc_hash = None
                    if exe_path and Path(exe_path).exists():
                        try:
                            with open(exe_path, 'rb') as f:
                                proc_hash = hashlib.sha256(f.read()).hexdigest()
                        except Exception:
                            pass
                    
                    processes.append({
                        "pid": proc_info.get('pid'),
                        "name": proc_info.get('name'),
                        "exe": exe_path,
                        "cmdline": proc_info.get('cmdline', []),
                        "cpu_percent": proc_info.get('cpu_percent', 0.0),
                        "memory_rss": proc_info.get('memory_info', {}).get('rss', 0) if isinstance(proc_info.get('memory_info'), dict) else 0,
                        "memory_vms": proc_info.get('memory_info', {}).get('vms', 0) if isinstance(proc_info.get('memory_info'), dict) else 0,
                        "open_files_count": len(proc_info.get('open_files', [])) if proc_info.get('open_files') else 0,
                        "connections_count": len(proc_info.get('connections', [])) if proc_info.get('connections') else 0,
                        "create_time": proc_info.get('create_time'),
                        "exe_hash_sha256": proc_hash
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        except Exception as e:
            logger.error(f"Error collecting processes: {e}")
        
        return processes
    
    def _collect_network(self) -> Dict[str, Any]:
        """Collect network information."""
        network_data = {
            "connections": [],
            "interfaces": {}
        }
        
        try:
            # Collect active connections
            for conn in psutil.net_connections(kind='inet'):
                try:
                    network_data["connections"].append({
                        "fd": conn.fd,
                        "family": str(conn.family),
                        "type": str(conn.type),
                        "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                        "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                        "status": conn.status
                    })
                except Exception:
                    continue
            
            # Collect interface statistics
            interfaces = psutil.net_if_stats()
            io_counters = psutil.net_io_counters(pernic=True)
            
            for iface_name, iface_stats in interfaces.items():
                network_data["interfaces"][iface_name] = {
                    "isup": iface_stats.isup,
                    "speed": iface_stats.speed,
                    "mtu": iface_stats.mtu
                }
                
                if iface_name in io_counters:
                    io = io_counters[iface_name]
                    network_data["interfaces"][iface_name].update({
                        "bytes_sent": io.bytes_sent,
                        "bytes_recv": io.bytes_recv,
                        "packets_sent": io.packets_sent,
                        "packets_recv": io.packets_recv
                    })
        
        except Exception as e:
            logger.error(f"Error collecting network data: {e}")
        
        return network_data
    
    def _collect_files(self) -> List[Dict[str, Any]]:
        """Collect file system information."""
        files = []
        
        try:
            # Monitor specific directories (configurable)
            monitor_dirs = os.environ.get('MONITOR_DIRS', '/tmp,/var/tmp,/home').split(',')
            
            for monitor_dir in monitor_dirs:
                monitor_path = Path(monitor_dir.strip())
                if not monitor_path.exists():
                    continue
                
                try:
                    # Collect recently modified files
                    for file_path in monitor_path.rglob('*'):
                        if not file_path.is_file():
                            continue
                        
                        try:
                            stat = file_path.stat()
                            
                            # Only collect files modified in last hour
                            import time
                            if time.time() - stat.st_mtime > 3600:
                                continue
                            
                            # Calculate file hash
                            file_hash = None
                            try:
                                if stat.st_size < 10 * 1024 * 1024:  # Only hash files < 10MB
                                    with open(file_path, 'rb') as f:
                                        file_hash = hashlib.sha256(f.read()).hexdigest()
                            except Exception:
                                pass
                            
                            files.append({
                                "path": str(file_path),
                                "size": stat.st_size,
                                "mtime": stat.st_mtime,
                                "mode": oct(stat.st_mode),
                                "hash_sha256": file_hash
                            })
                        except (PermissionError, OSError):
                            continue
                
                except Exception as e:
                    logger.debug(f"Error scanning {monitor_dir}: {e}")
        
        except Exception as e:
            logger.error(f"Error collecting file data: {e}")
        
        return files[:100]  # Limit to 100 files per collection
    
    def _create_alert(self, telemetry: Dict[str, Any], detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert from detection result."""
        return {
            "event_type": "threat_detected",
            "timestamp": datetime.utcnow().isoformat(),
            "hostname": os.uname().nodename,
            "threat_type": detection_result.get("threat_type"),
            "threat_score": detection_result.get("threat_score"),
            "ml_explanation": detection_result.get("ml_explanation"),
            "shap_values": detection_result.get("shap_values"),
            "telemetry": telemetry,
            "detection_metadata": detection_result.get("metadata", {})
        }

