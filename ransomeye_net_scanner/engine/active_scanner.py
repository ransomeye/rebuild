# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/engine/active_scanner.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wrapper for python-nmap with Host Discovery and Service Detection

import os
import subprocess
from typing import Dict, Any, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import python-nmap
try:
    import nmap
    NMAP_AVAILABLE = True
except ImportError:
    NMAP_AVAILABLE = False
    logger.warning("python-nmap not available, active scanning disabled")

class ActiveScanner:
    """
    Active network scanner using Nmap.
    """
    
    def __init__(self):
        """Initialize active scanner."""
        self.nm = None
        self.nmap_available = False
        
        if NMAP_AVAILABLE:
            try:
                self.nm = nmap.PortScanner()
                # Test if nmap binary is available
                result = subprocess.run(['which', 'nmap'], capture_output=True, text=True)
                if result.returncode == 0:
                    self.nmap_available = True
                    logger.info("Nmap scanner initialized")
                else:
                    logger.warning("Nmap binary not found in PATH")
            except Exception as e:
                logger.error(f"Failed to initialize Nmap scanner: {e}")
    
    def is_nmap_available(self) -> bool:
        """
        Check if Nmap is available.
        
        Returns:
            True if Nmap is available, False otherwise
        """
        return self.nmap_available and self.nm is not None
    
    def scan_subnet(self, subnet: str, intensity: str = "T3") -> Dict[str, Any]:
        """
        Scan subnet with Host Discovery and Service Detection.
        
        Args:
            subnet: Subnet to scan (e.g., "192.168.1.0/24")
            intensity: Scan intensity (T1-T5)
            
        Returns:
            Scan results dictionary
        """
        if not self.is_nmap_available():
            logger.error("Nmap not available, cannot perform scan")
            return {
                "subnet": subnet,
                "status": "error",
                "error": "Nmap not available",
                "hosts": []
            }
        
        try:
            # Build Nmap arguments
            # -sn: Ping scan (host discovery)
            # -sV: Version detection
            # -T{intensity}: Timing template
            scan_args = f"-sn -sV -T{intensity}"
            
            logger.info(f"Scanning subnet {subnet} with intensity {intensity}")
            
            # Perform scan
            self.nm.scan(hosts=subnet, arguments=scan_args)
            
            # Parse results
            hosts = []
            for host in self.nm.all_hosts():
                host_info = {
                    "ip": host,
                    "hostname": self.nm[host].hostname(),
                    "state": self.nm[host].state(),
                    "services": []
                }
                
                # Extract services
                for proto in self.nm[host].all_protocols():
                    ports = self.nm[host][proto].keys()
                    for port in ports:
                        port_info = self.nm[host][proto][port]
                        host_info["services"].append({
                            "port": port,
                            "protocol": proto,
                            "state": port_info.get('state', 'unknown'),
                            "name": port_info.get('name', 'unknown'),
                            "product": port_info.get('product', ''),
                            "version": port_info.get('version', ''),
                            "banner": f"{port_info.get('product', '')} {port_info.get('version', '')}".strip()
                        })
                
                hosts.append(host_info)
            
            logger.info(f"Scan completed: {len(hosts)} hosts found in {subnet}")
            
            return {
                "subnet": subnet,
                "status": "completed",
                "intensity": intensity,
                "hosts": hosts,
                "total_hosts": len(hosts)
            }
            
        except Exception as e:
            logger.error(f"Error scanning subnet {subnet}: {e}", exc_info=True)
            return {
                "subnet": subnet,
                "status": "error",
                "error": str(e),
                "hosts": []
            }

