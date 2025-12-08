# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/engine/passive_listener.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Uses scapy to sniff CAPTURE_IFACE for ARP, DHCP, and mDNS packets

import os
import threading
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import scapy
try:
    from scapy.all import sniff, ARP, DHCP, IP, Ether, get_if_list
    from scapy.layers.dns import DNS
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logger.warning("scapy not available, passive listening disabled")

class PassiveListener:
    """
    Passive network listener using Scapy.
    """
    
    def __init__(self):
        """Initialize passive listener."""
        self.capture_interface = os.environ.get('CAPTURE_IFACE', 'eth0')
        self.running = False
        self.sniff_thread = None
        self.discovered_assets = []
        self.scapy_available = SCAPY_AVAILABLE
    
    def is_running(self) -> bool:
        """
        Check if listener is running.
        
        Returns:
            True if running, False otherwise
        """
        return self.running
    
    def start(self):
        """Start passive listener in background thread."""
        if not self.scapy_available:
            logger.error("Scapy not available, cannot start passive listener")
            return
        
        if self.running:
            logger.warning("Passive listener already running")
            return
        
        self.running = True
        self.sniff_thread = threading.Thread(target=self._sniff_loop, daemon=True)
        self.sniff_thread.start()
        logger.info(f"Passive listener started on interface: {self.capture_interface}")
    
    def stop(self):
        """Stop passive listener."""
        self.running = False
        if self.sniff_thread:
            self.sniff_thread.join(timeout=5)
        logger.info("Passive listener stopped")
    
    def _sniff_loop(self):
        """Main sniffing loop."""
        try:
            # Filter for ARP, DHCP, and mDNS
            filter_str = "arp or udp port 67 or udp port 68 or udp port 5353"
            
            sniff(
                iface=self.capture_interface,
                filter=filter_str,
                prn=self._process_packet,
                stop_filter=lambda x: not self.running,
                store=False
            )
        except Exception as e:
            logger.error(f"Error in sniff loop: {e}", exc_info=True)
            self.running = False
    
    def _process_packet(self, packet):
        """
        Process captured packet.
        
        Args:
            packet: Scapy packet object
        """
        try:
            # Process ARP packets
            if packet.haslayer(ARP):
                self._process_arp(packet)
            
            # Process DHCP packets
            if packet.haslayer(DHCP):
                self._process_dhcp(packet)
            
            # Process mDNS packets
            if packet.haslayer(DNS) and packet.haslayer(IP):
                if packet[IP].dport == 5353 or packet[IP].sport == 5353:
                    self._process_mdns(packet)
                    
        except Exception as e:
            logger.debug(f"Error processing packet: {e}")
    
    def _process_arp(self, packet):
        """Process ARP packet."""
        arp = packet[ARP]
        
        asset = {
            "mac": arp.hwsrc,
            "ip": arp.psrc,
            "type": "discovered",
            "source": "arp",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._add_asset(asset)
        logger.debug(f"ARP discovery: {arp.psrc} -> {arp.hwsrc}")
    
    def _process_dhcp(self, packet):
        """Process DHCP packet."""
        dhcp = packet[DHCP]
        
        # Extract DHCP options
        mac = None
        hostname = None
        vendor = None
        
        if packet.haslayer(Ether):
            mac = packet[Ether].src
        
        # Parse DHCP options
        if dhcp.options:
            for option in dhcp.options:
                if isinstance(option, tuple):
                    opt_type, opt_value = option
                    if opt_type == 12:  # Hostname
                        hostname = opt_value.decode('utf-8', errors='ignore')
                    elif opt_type == 60:  # Vendor Class Identifier
                        vendor = opt_value.decode('utf-8', errors='ignore')
        
        if mac:
            asset = {
                "mac": mac,
                "hostname": hostname,
                "vendor": vendor,
                "type": "discovered",
                "source": "dhcp",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._add_asset(asset)
            logger.debug(f"DHCP discovery: {mac} ({hostname})")
    
    def _process_mdns(self, packet):
        """Process mDNS packet."""
        # Extract mDNS information
        if packet.haslayer(DNS):
            dns = packet[DNS]
            if dns.qr == 0:  # Query
                if dns.qd:
                    hostname = dns.qd.qname.decode('utf-8', errors='ignore').rstrip('.')
                    
                    asset = {
                        "hostname": hostname,
                        "type": "discovered",
                        "source": "mdns",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    self._add_asset(asset)
                    logger.debug(f"mDNS discovery: {hostname}")
    
    def _add_asset(self, asset: Dict[str, Any]):
        """
        Add discovered asset.
        
        Args:
            asset: Asset dictionary
        """
        self.discovered_assets.append(asset)
        # Limit buffer size
        if len(self.discovered_assets) > 1000:
            self.discovered_assets.pop(0)
    
    def get_discovered_assets(self) -> List[Dict[str, Any]]:
        """
        Get list of discovered assets.
        
        Returns:
            List of discovered assets
        """
        return self.discovered_assets.copy()

