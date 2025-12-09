# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/engine/flow_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Flow session tracking manager that maintains active sessions and calculates duration/byte counts

import time
import logging
from collections import defaultdict
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FlowStats:
    """Flow statistics container."""
    flow_id: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    first_seen: float
    last_seen: float
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    flags: set = field(default_factory=set)
    
    @property
    def duration(self) -> float:
        """Get flow duration in seconds."""
        return self.last_seen - self.first_seen
    
    @property
    def total_bytes(self) -> int:
        """Get total bytes transferred."""
        return self.bytes_sent + self.bytes_recv
    
    @property
    def total_packets(self) -> int:
        """Get total packets."""
        return self.packets_sent + self.packets_recv
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'flow_id': self.flow_id,
            'src_ip': self.src_ip,
            'dst_ip': self.dst_ip,
            'src_port': self.src_port,
            'dst_port': self.dst_port,
            'protocol': self.protocol,
            'first_seen': datetime.fromtimestamp(self.first_seen).isoformat(),
            'last_seen': datetime.fromtimestamp(self.last_seen).isoformat(),
            'duration_seconds': self.duration,
            'bytes_sent': self.bytes_sent,
            'bytes_recv': self.bytes_recv,
            'total_bytes': self.total_bytes,
            'packets_sent': self.packets_sent,
            'packets_recv': self.packets_recv,
            'total_packets': self.total_packets,
            'flags': list(self.flags)
        }


class FlowManager:
    """Manages active flow sessions."""
    
    def __init__(self, idle_timeout: int = 300):
        """
        Initialize flow manager.
        
        Args:
            idle_timeout: Seconds before considering a flow idle (default: 300)
        """
        self.flows: Dict[str, FlowStats] = {}
        self.idle_timeout = idle_timeout
        self.closed_flows: Dict[str, FlowStats] = {}
        self.max_closed_flows = 10000  # Keep last 10k closed flows
    
    def _make_flow_id(self, src_ip: str, dst_ip: str, src_port: int, 
                      dst_port: int, protocol: str) -> str:
        """Generate deterministic flow ID from 5-tuple."""
        # Normalize: always use smaller IP/port as first
        if src_ip < dst_ip or (src_ip == dst_ip and src_port < dst_port):
            return f"{src_ip}:{src_port}-{dst_ip}:{dst_port}-{protocol}"
        else:
            return f"{dst_ip}:{dst_port}-{src_ip}:{src_port}-{protocol}"
    
    def update_flow(self, src_ip: str, dst_ip: str, src_port: int, 
                   dst_port: int, protocol: str, packet_size: int,
                   direction: str = 'sent', flags: set = None) -> FlowStats:
        """
        Update or create flow statistics.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            src_port: Source port
            dst_port: Destination port
            protocol: Protocol (TCP, UDP, ICMP, etc.)
            packet_size: Packet size in bytes
            direction: 'sent' or 'recv'
            flags: TCP flags set
            
        Returns:
            FlowStats object
        """
        flow_id = self._make_flow_id(src_ip, dst_ip, src_port, dst_port, protocol)
        now = time.time()
        
        if flow_id not in self.flows:
            # New flow
            self.flows[flow_id] = FlowStats(
                flow_id=flow_id,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                first_seen=now,
                last_seen=now
            )
        
        flow = self.flows[flow_id]
        flow.last_seen = now
        
        if direction == 'sent':
            flow.bytes_sent += packet_size
            flow.packets_sent += 1
        else:
            flow.bytes_recv += packet_size
            flow.packets_recv += 1
        
        if flags:
            flow.flags.update(flags)
        
        return flow
    
    def get_flow(self, src_ip: str, dst_ip: str, src_port: int,
                dst_port: int, protocol: str) -> Optional[FlowStats]:
        """Get flow statistics if exists."""
        flow_id = self._make_flow_id(src_ip, dst_ip, src_port, dst_port, protocol)
        return self.flows.get(flow_id)
    
    def close_flow(self, flow_id: str) -> Optional[FlowStats]:
        """
        Close a flow and move to closed flows.
        
        Args:
            flow_id: Flow identifier
            
        Returns:
            Closed FlowStats or None
        """
        if flow_id in self.flows:
            flow = self.flows.pop(flow_id)
            self.closed_flows[flow_id] = flow
            
            # Limit closed flows cache
            if len(self.closed_flows) > self.max_closed_flows:
                # Remove oldest
                oldest = min(self.closed_flows.items(), 
                           key=lambda x: x[1].last_seen)
                self.closed_flows.pop(oldest[0])
            
            return flow
        return None
    
    def cleanup_idle_flows(self) -> int:
        """
        Clean up idle flows.
        
        Returns:
            Number of flows closed
        """
        now = time.time()
        idle_flows = []
        
        for flow_id, flow in self.flows.items():
            if now - flow.last_seen > self.idle_timeout:
                idle_flows.append(flow_id)
        
        for flow_id in idle_flows:
            self.close_flow(flow_id)
        
        if idle_flows:
            logger.info(f"Cleaned up {len(idle_flows)} idle flows")
        
        return len(idle_flows)
    
    def get_active_flows(self) -> Dict[str, FlowStats]:
        """Get all active flows."""
        return self.flows.copy()
    
    def get_active_flow_count(self) -> int:
        """Get count of active flows."""
        return len(self.flows)
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        active = self.get_active_flows()
        total_bytes = sum(f.total_bytes for f in active.values())
        total_packets = sum(f.total_packets for f in active.values())
        
        return {
            'active_flows': len(active),
            'closed_flows_cached': len(self.closed_flows),
            'total_bytes': total_bytes,
            'total_packets': total_packets,
            'avg_bytes_per_flow': total_bytes / len(active) if active else 0,
            'avg_packets_per_flow': total_packets / len(active) if active else 0
        }

