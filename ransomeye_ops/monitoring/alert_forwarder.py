# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/monitoring/alert_forwarder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Forwards system health alerts to Syslog/SIEM

import os
import sys
import socket
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class AlertForwarder:
    """Forwards alerts to Syslog/SIEM."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        
        self.syslog_host = os.environ.get('SYSLOG_HOST', 'localhost')
        self.syslog_port = int(os.environ.get('SYSLOG_PORT', '514'))
        self.syslog_facility = int(os.environ.get('SYSLOG_FACILITY', '16'))  # LOCAL0
        self.enable_syslog = os.environ.get('ENABLE_SYSLOG', 'true').lower() == 'true'
    
    def format_syslog_message(self, severity: int, message: str, metadata: Optional[Dict] = None) -> bytes:
        """Format message in RFC 3164 Syslog format."""
        # Priority = Facility * 8 + Severity
        priority = (self.syslog_facility * 8) + severity
        
        # Timestamp (offline-safe, no NTP)
        timestamp = datetime.now().strftime('%b %d %H:%M:%S')
        
        # Hostname
        hostname = socket.gethostname()
        
        # Tag
        tag = 'ransomeye'
        
        # Build message
        if metadata:
            metadata_str = json.dumps(metadata)
            full_message = f"{message} | {metadata_str}"
        else:
            full_message = message
        
        # RFC 3164 format: <PRI>TIMESTAMP HOSTNAME TAG: MESSAGE
        syslog_msg = f"<{priority}>{timestamp} {hostname} {tag}: {full_message}"
        
        return syslog_msg.encode('utf-8')
    
    def send_syslog(self, severity: int, message: str, metadata: Optional[Dict] = None) -> bool:
        """Send message to Syslog server."""
        if not self.enable_syslog:
            return False
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            syslog_msg = self.format_syslog_message(severity, message, metadata)
            sock.sendto(syslog_msg, (self.syslog_host, self.syslog_port))
            sock.close()
            
            return True
        except Exception as e:
            print(f"Failed to send syslog message: {e}")
            return False
    
    def forward_alert(self, alert_type: str, severity: str, message: str, metadata: Optional[Dict] = None) -> bool:
        """Forward alert to configured destinations."""
        # Map severity to syslog severity
        severity_map = {
            'critical': 2,  # CRIT
            'error': 3,     # ERR
            'warning': 4,   # WARNING
            'info': 6,      # INFO
            'debug': 7      # DEBUG
        }
        
        syslog_severity = severity_map.get(severity.lower(), 6)
        
        # Add alert metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'alert_type': alert_type,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
            'source': 'ransomeye_ops'
        })
        
        # Send to syslog
        success = self.send_syslog(syslog_severity, message, metadata)
        
        # Also print locally
        print(f"[{severity.upper()}] {alert_type}: {message}")
        if metadata:
            print(f"  Metadata: {json.dumps(metadata, indent=2)}")
        
        return success
    
    def forward_health_check_results(self, health_results: Dict) -> None:
        """Forward health check results as alerts if issues detected."""
        # Check disk usage
        disk_io = health_results.get('disk_io', {})
        if disk_io.get('success') and disk_io.get('percent_used', 0) > 80:
            self.forward_alert(
                'disk_usage_high',
                'warning',
                f"Disk usage at {disk_io.get('percent_used', 0):.1f}%",
                {'percent_used': disk_io.get('percent_used')}
            )
        
        # Check DB latency
        db_latency = health_results.get('db_latency', {})
        if db_latency.get('success') and db_latency.get('simple_query_ms', 0) > 100:
            self.forward_alert(
                'db_latency_high',
                'warning',
                f"Database latency: {db_latency.get('simple_query_ms', 0)} ms",
                {'latency_ms': db_latency.get('simple_query_ms')}
            )
        
        # Check overall status
        if health_results.get('overall_status') == 'DEGRADED':
            self.forward_alert(
                'system_degraded',
                'error',
                'System health check indicates degraded state',
                health_results
            )


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Forward alerts to Syslog/SIEM')
    parser.add_argument('--type', type=str, required=True, help='Alert type')
    parser.add_argument('--severity', type=str, required=True, choices=['critical', 'error', 'warning', 'info', 'debug'])
    parser.add_argument('--message', type=str, required=True, help='Alert message')
    parser.add_argument('--metadata', type=str, help='JSON metadata')
    
    args = parser.parse_args()
    
    forwarder = AlertForwarder()
    
    metadata = None
    if args.metadata:
        metadata = json.loads(args.metadata)
    
    success = forwarder.forward_alert(args.type, args.severity, args.message, metadata)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

