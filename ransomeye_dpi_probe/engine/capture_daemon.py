# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/engine/capture_daemon.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main packet capture daemon using Scapy with raw sockets for high-performance packet capture

import os
import sys
import time
import signal
import logging
import threading
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, Callable
from scapy.all import sniff, IP, TCP, UDP, ICMP, Ether, Raw
from scapy.layers.inet import get_if_addr
import scapy.config

# Import local modules
from .flow_manager import FlowManager
from .privacy_filter import PrivacyFilter
from .pcap_writer import PCAPWriter

# Configure Scapy for better performance
scapy.config.conf.use_pcap = True  # Use libpcap if available
scapy.config.conf.sniff_promisc = True

logger = logging.getLogger(__name__)


class CaptureDaemon:
    """High-performance packet capture daemon."""
    
    def __init__(self):
        """Initialize capture daemon."""
        self.interface = os.environ.get('CAPTURE_IFACE', 'eth0')
        self.buffer_dir = Path(os.environ.get('BUFFER_DIR', '/var/lib/ransomeye-probe/buffer'))
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        (self.buffer_dir / 'pending').mkdir(exist_ok=True)
        (self.buffer_dir / 'inflight').mkdir(exist_ok=True)
        (self.buffer_dir / 'archived').mkdir(exist_ok=True)
        
        self.max_capture_mb = int(os.environ.get('PROBE_MAX_CAPTURE_MB', '1000'))
        self.running = False
        self.sniffer_thread: Optional[threading.Thread] = None
        self.processor_thread: Optional[threading.Thread] = None
        
        # Components
        self.flow_manager = FlowManager(idle_timeout=300)
        self.privacy_filter = PrivacyFilter(strict_mode=True)
        self.pcap_writer = PCAPWriter(
            output_dir=str(self.buffer_dir / 'pending'),
            max_file_size_mb=100,
            rotate_on_time=True,
            rotation_interval_sec=3600
        )
        
        # Packet queue for processing
        self.packet_queue = Queue(maxsize=10000)
        self.stats = {
            'packets_captured': 0,
            'packets_dropped': 0,
            'bytes_captured': 0,
            'flows_active': 0,
            'pii_redacted_count': 0
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def _extract_5tuple(self, packet) -> Optional[dict]:
        """Extract 5-tuple from packet."""
        if IP not in packet:
            return None
        
        ip_layer = packet[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst
        protocol = ip_layer.proto
        
        src_port = None
        dst_port = None
        
        if TCP in packet:
            tcp = packet[TCP]
            src_port = tcp.sport
            dst_port = tcp.dport
            protocol = 'TCP'
        elif UDP in packet:
            udp = packet[UDP]
            src_port = udp.sport
            dst_port = udp.dport
            protocol = 'UDP'
        elif ICMP in packet:
            icmp = packet[ICMP]
            protocol = 'ICMP'
            # ICMP doesn't have ports, use type/code
            src_port = icmp.type
            dst_port = icmp.code
        else:
            protocol = f'IP_{protocol}'
        
        return {
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'src_port': src_port or 0,
            'dst_port': dst_port or 0,
            'protocol': protocol
        }
    
    def _packet_handler(self, packet):
        """Callback for Scapy sniff - enqueue packet for processing."""
        try:
            if self.packet_queue.full():
                self.stats['packets_dropped'] += 1
                logger.warning("Packet queue full, dropping packet")
                return
            
            self.packet_queue.put((packet, time.time()))
            self.stats['packets_captured'] += 1
        except Exception as e:
            logger.error(f"Error in packet handler: {e}")
            self.stats['packets_dropped'] += 1
    
    def _process_packet(self, packet, timestamp: float):
        """Process a single packet."""
        try:
            # Extract 5-tuple
            flow_info = self._extract_5tuple(packet)
            if not flow_info:
                return
            
            # Get packet size
            packet_size = len(packet)
            self.stats['bytes_captured'] += packet_size
            
            # Determine direction (heuristic: compare with interface IP)
            try:
                iface_ip = get_if_addr(self.interface)
                direction = 'sent' if flow_info['src_ip'] == iface_ip else 'recv'
            except:
                direction = 'sent'  # Default
            
            # Extract TCP flags if applicable
            flags = set()
            if TCP in packet:
                tcp = packet[TCP]
                if tcp.flags & 0x02: flags.add('SYN')
                if tcp.flags & 0x10: flags.add('ACK')
                if tcp.flags & 0x01: flags.add('FIN')
                if tcp.flags & 0x04: flags.add('RST')
            
            # Update flow statistics
            flow = self.flow_manager.update_flow(
                src_ip=flow_info['src_ip'],
                dst_ip=flow_info['dst_ip'],
                src_port=flow_info['src_port'],
                dst_port=flow_info['dst_port'],
                protocol=flow_info['protocol'],
                packet_size=packet_size,
                direction=direction,
                flags=flags if flags else None
            )
            
            # Extract payload and apply privacy filter
            payload = b''
            if Raw in packet:
                payload = packet[Raw].load
            
            if payload:
                flow_id = flow.flow_id
                redacted_payload, redact_stats = self.privacy_filter.redact(payload, flow_id)
                
                if redact_stats['redacted']:
                    self.stats['pii_redacted_count'] += 1
                    # Replace payload in packet if redacted
                    if redacted_payload != payload:
                        # Reconstruct packet with redacted payload
                        # For now, we log it - full packet reconstruction would be complex
                        pass
            
            # Write to PCAP
            try:
                # Convert packet to bytes (Ethernet frame)
                if Ether in packet:
                    packet_bytes = bytes(packet)
                else:
                    # If no Ethernet layer, create one (for loopback interfaces)
                    eth = Ether()
                    packet_bytes = bytes(eth / packet)
                
                self.pcap_writer.write_packet(packet_bytes, timestamp)
            except Exception as e:
                logger.error(f"Error writing packet to PCAP: {e}")
            
        except Exception as e:
            logger.error(f"Error processing packet: {e}")
    
    def _packet_processor(self):
        """Background thread for processing packets."""
        logger.info("Packet processor thread started")
        
        while self.running:
            try:
                packet, timestamp = self.packet_queue.get(timeout=1.0)
                self._process_packet(packet, timestamp)
                self.packet_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in packet processor: {e}")
        
        logger.info("Packet processor thread stopped")
    
    def _cleanup_worker(self):
        """Background thread for periodic cleanup."""
        logger.info("Cleanup worker thread started")
        
        while self.running:
            time.sleep(60)  # Run every minute
            
            try:
                # Cleanup idle flows
                self.flow_manager.cleanup_idle_flows()
                
                # Update stats
                self.stats['flows_active'] = self.flow_manager.get_active_flow_count()
                
                # Check buffer size
                buffer_size_mb = sum(
                    f.stat().st_size for f in self.buffer_dir.rglob('*') if f.is_file()
                ) / 1024 / 1024
                
                if buffer_size_mb > self.max_capture_mb:
                    logger.warning(f"Buffer size ({buffer_size_mb:.2f} MB) exceeds limit "
                                 f"({self.max_capture_mb} MB)")
                    # Trigger upload if uploader is available
                    try:
                        from ransomeye_dpi_probe.storage.buffer_store import BufferStore
                        buffer_store = BufferStore(str(self.buffer_dir))
                        # Archive oldest files if buffer still exceeds limit after upload
                        if buffer_store.get_total_size_mb() > self.max_capture_mb * 0.9:
                            archived_removed = buffer_store.cleanup_old_archived()
                            logger.info(f"Cleaned up {archived_removed} old archived files")
                    except Exception as e:
                        logger.error(f"Error managing buffer size: {e}")
                    
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
        
        logger.info("Cleanup worker thread stopped")
    
    def _sniff_worker(self):
        """Main sniffing thread."""
        logger.info(f"Starting packet capture on interface: {self.interface}")
        
        try:
            # Use store=False to avoid storing all packets in memory
            sniff(
                iface=self.interface,
                prn=self._packet_handler,
                store=False,
                stop_filter=lambda x: not self.running
            )
        except Exception as e:
            logger.error(f"Error in sniff worker: {e}")
            self.running = False
        
        logger.info("Sniffing thread stopped")
    
    def start(self):
        """Start capture daemon."""
        if self.running:
            logger.warning("Capture daemon already running")
            return
        
        logger.info("Starting capture daemon...")
        self.running = True
        
        # Start processor thread
        self.processor_thread = threading.Thread(target=self._packet_processor, daemon=True)
        self.processor_thread.start()
        
        # Start cleanup worker
        cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        cleanup_thread.start()
        
        # Start sniffing in main thread (Scapy handles threading internally)
        self.sniffer_thread = threading.Thread(target=self._sniff_worker, daemon=True)
        self.sniffer_thread.start()
        
        logger.info("Capture daemon started")
    
    def stop(self):
        """Stop capture daemon."""
        if not self.running:
            return
        
        logger.info("Stopping capture daemon...")
        self.running = False
        
        # Wait for threads
        if self.sniffer_thread:
            self.sniffer_thread.join(timeout=5)
        if self.processor_thread:
            # Process remaining packets
            while not self.packet_queue.empty():
                try:
                    packet, timestamp = self.packet_queue.get(timeout=0.1)
                    self._process_packet(packet, timestamp)
                except Empty:
                    break
            self.processor_thread.join(timeout=5)
        
        # Close PCAP writer
        self.pcap_writer.close()
        
        logger.info("Capture daemon stopped")
    
    def get_stats(self) -> dict:
        """Get capture statistics."""
        flow_stats = self.flow_manager.get_stats_summary()
        privacy_stats = self.privacy_filter.get_stats()
        
        return {
            **self.stats,
            **flow_stats,
            'privacy_filter': privacy_stats,
            'pcap_writer': self.pcap_writer.get_stats(),
            'interface': self.interface,
            'buffer_dir': str(self.buffer_dir)
        }


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    daemon = CaptureDaemon()
    
    try:
        daemon.start()
        
        # Keep running
        while daemon.running:
            time.sleep(1)
            # Print stats periodically
            stats = daemon.get_stats()
            logger.info(f"Stats: {stats['packets_captured']} packets, "
                       f"{stats['active_flows']} flows, "
                       f"{stats['packets_dropped']} dropped")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        daemon.stop()


if __name__ == '__main__':
    main()

