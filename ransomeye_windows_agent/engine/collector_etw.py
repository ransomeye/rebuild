# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/engine/collector_etw.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: ETW (Event Tracing for Windows) collector with EventLog fallback for telemetry

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

try:
    import win32evtlog
    import win32con
    import win32security
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ETWCollector:
    """ETW and EventLog telemetry collector for Windows."""
    
    def __init__(self, detector=None, persistence=None):
        """
        Initialize ETW collector.
        
        Args:
            detector: Detector instance for threat detection
            persistence: PersistenceManager instance for saving events
        """
        self.detector = detector
        self.persistence = persistence
        self.etw_session = None
        self.use_etw = os.environ.get('ENABLE_ETW', 'true').lower() == 'true'
        self.fallback_to_eventlog = True
        
        # ETW providers to monitor
        self.providers = [
            # Process events
            "{22FB2CD6-0E7B-422B-A0C7-2FAD1FD0E716}",  # Microsoft-Windows-Kernel-Process
            # Network events
            "{7DD42A49-5329-4832-8DFD-43D979153A88}",  # Microsoft-Windows-TCPIP
            # File events
            "{EDD08927-9CC4-4E65-B970-C2560FB5C289}",  # Microsoft-Windows-Kernel-File
        ]
        
        logger.info(f"ETW Collector initialized (ETW: {self.use_etw}, Fallback: {self.fallback_to_eventlog})")
    
    def start_session(self):
        """Start ETW trace session."""
        if not self.use_etw:
            logger.info("ETW disabled, using EventLog fallback")
            return
        
        try:
            # Try to use ETW via pywintrace or direct Windows API
            # For now, fallback to EventLog if ETW setup fails
            logger.info("ETW session start attempted")
            self.fallback_to_eventlog = True
        except Exception as e:
            logger.warning(f"ETW session start failed: {e}, using EventLog fallback")
            self.fallback_to_eventlog = True
    
    def stop_session(self):
        """Stop ETW trace session."""
        if self.etw_session:
            try:
                # Close ETW session
                self.etw_session = None
                logger.info("ETW session stopped")
            except Exception as e:
                logger.error(f"Error stopping ETW session: {e}")
    
    def collect_events(self):
        """Collect telemetry events from ETW or EventLog."""
        try:
            if self.fallback_to_eventlog or not self.use_etw:
                # Use EventLog and process monitoring
                telemetry = self._collect_from_eventlog_and_psutil()
            else:
                # Use ETW (if available)
                telemetry = self._collect_from_etw()
            
            if telemetry:
                # Run detection
                if self.detector:
                    detection_result = self.detector.detect(telemetry)
                    telemetry['detection'] = detection_result
                
                # Save to buffer
                if self.persistence:
                    self.persistence.save_event(telemetry)
        
        except Exception as e:
            logger.error(f"Error collecting events: {e}", exc_info=True)
    
    def _collect_from_etw(self) -> Optional[Dict[str, Any]]:
        """Collect events from ETW session."""
        # Placeholder for ETW collection
        # In production, would use pywintrace or ctypes to call Windows ETW APIs
        return None
    
    def _collect_from_eventlog_and_psutil(self) -> Dict[str, Any]:
        """Collect telemetry using EventLog and psutil (fallback method)."""
        telemetry = {
            "timestamp": datetime.utcnow().isoformat(),
            "hostname": os.environ.get('COMPUTERNAME', 'unknown'),
            "platform": "windows",
            "processes": [],
            "network": {"connections": []},
            "files": [],
            "events": []
        }
        
        # Collect process information
        if PSUTIL_AVAILABLE:
            try:
                processes = self._collect_processes()
                telemetry["processes"] = processes
            except Exception as e:
                logger.error(f"Error collecting processes: {e}")
        
        # Collect network connections
        if PSUTIL_AVAILABLE:
            try:
                connections = self._collect_network_connections()
                telemetry["network"]["connections"] = connections
            except Exception as e:
                logger.error(f"Error collecting network: {e}")
        
        # Collect recent security events from EventLog
        if WIN32_AVAILABLE:
            try:
                events = self._collect_security_events()
                telemetry["events"] = events
            except Exception as e:
                logger.error(f"Error collecting EventLog: {e}")
        
        return telemetry
    
    def _collect_processes(self) -> List[Dict[str, Any]]:
        """Collect process information using psutil."""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'cpu_percent', 
                                            'memory_info', 'create_time', 'username']):
                try:
                    pinfo = proc.info
                    proc_data = {
                        "pid": pinfo['pid'],
                        "name": pinfo['name'] or 'unknown',
                        "exe": pinfo['exe'] or '',
                        "cmdline": pinfo['cmdline'] or [],
                        "cpu_percent": pinfo['cpu_percent'] or 0.0,
                        "memory_rss": pinfo['memory_info'].rss if pinfo['memory_info'] else 0,
                        "create_time": pinfo['create_time'],
                        "username": pinfo['username'] or 'unknown'
                    }
                    processes.append(proc_data)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error iterating processes: {e}")
        
        return processes
    
    def _collect_network_connections(self) -> List[Dict[str, Any]]:
        """Collect network connection information."""
        connections = []
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                try:
                    conn_data = {
                        "fd": conn.fd,
                        "family": str(conn.family),
                        "type": str(conn.type),
                        "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                        "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                        "status": conn.status
                    }
                    connections.append(conn_data)
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error collecting network connections: {e}")
        
        return connections
    
    def _collect_security_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Collect recent security events from Windows EventLog."""
        events = []
        
        if not WIN32_AVAILABLE:
            return events
        
        try:
            # Open Security event log
            hand = win32evtlog.OpenEventLog(None, "Security")
            
            try:
                # Read recent events
                flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                events_read = win32evtlog.ReadEventLog(hand, flags, 0)
                
                count = 0
                for event in events_read:
                    if count >= limit:
                        break
                    
                    try:
                        # Extract event data
                        event_id = win32evtlog.SafeArrayGetElement(event.EventID, 0)
                        event_time = event.TimeGenerated
                        event_source = event.SourceName
                        
                        # Redact sensitive data
                        event_data = {
                            "event_id": int(event_id),
                            "time": datetime.fromtimestamp(event_time).isoformat(),
                            "source": event_source,
                            "category": event.EventCategory,
                            "type": self._get_event_type_name(event.EventType)
                        }
                        
                        # Only include non-sensitive events
                        if event_id in [4624, 4625, 4648, 4672, 4688, 4689, 4697, 4698]:
                            # Logon, process creation events
                            event_data["redacted"] = True
                            events.append(event_data)
                            count += 1
                    except Exception:
                        continue
                
            finally:
                win32evtlog.CloseEventLog(hand)
        
        except Exception as e:
            logger.error(f"Error reading EventLog: {e}")
        
        return events
    
    def _get_event_type_name(self, event_type: int) -> str:
        """Convert event type code to name."""
        event_types = {
            win32con.EVENTLOG_ERROR_TYPE: "Error",
            win32con.EVENTLOG_WARNING_TYPE: "Warning",
            win32con.EVENTLOG_INFORMATION_TYPE: "Information",
            win32con.EVENTLOG_AUDIT_SUCCESS: "AuditSuccess",
            win32con.EVENTLOG_AUDIT_FAILURE: "AuditFailure"
        }
        return event_types.get(event_type, "Unknown")
    
    def _redact_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact PII from telemetry data."""
        redacted = data.copy()
        
        # Redact usernames (keep structure, mask values)
        if 'username' in redacted:
            redacted['username'] = '[REDACTED]'
        
        # Redact file paths containing user data
        if 'files' in redacted:
            for file_info in redacted['files']:
                path = file_info.get('path', '')
                if 'Users' in path or 'AppData' in path:
                    file_info['path'] = '[REDACTED_PATH]'
        
        return redacted

