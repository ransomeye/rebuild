# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/engine/asset_manager.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Logic to merge Active/Passive data, avoiding duplicates by MAC Address

from typing import Dict, Any, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssetManager:
    """
    Manages assets from active and passive scanning.
    """
    
    def __init__(self):
        """Initialize asset manager."""
        from ..storage.asset_db import AssetDB
        from ..cve.cve_matcher import CVEMatcher
        
        self.asset_db = AssetDB()
        self.cve_matcher = CVEMatcher()
    
    def is_cve_db_loaded(self) -> bool:
        """
        Check if CVE database is loaded.
        
        Returns:
            True if CVE DB is loaded, False otherwise
        """
        return self.cve_matcher.is_db_loaded()
    
    def process_scan_results(self, scan_result: Dict[str, Any]):
        """
        Process active scan results.
        
        Args:
            scan_result: Scan result dictionary
        """
        for host in scan_result.get('hosts', []):
            asset = {
                "ip": host.get('ip'),
                "hostname": host.get('hostname', ''),
                "mac": "",  # May not be available from active scan
                "services": host.get('services', []),
                "source": "active_scan",
                "last_seen": datetime.utcnow().isoformat()
            }
            
            # Match CVEs for services
            vulnerabilities = []
            for service in asset.get('services', []):
                banner = service.get('banner', '')
                if banner:
                    cves = self.cve_matcher.match_banner(banner)
                    for cve in cves:
                        vulnerabilities.append({
                            "cve_id": cve.get('cve_id'),
                            "cvss_score": cve.get('cvss_score'),
                            "service": service.get('name'),
                            "port": service.get('port')
                        })
            
            asset["vulnerabilities"] = vulnerabilities
            
            # Store or update asset
            self.asset_db.upsert_asset(asset)
        
        logger.info(f"Processed {len(scan_result.get('hosts', []))} hosts from scan")
    
    def process_passive_discovery(self, discovered_assets: List[Dict[str, Any]]):
        """
        Process passive discovery results.
        
        Args:
            discovered_assets: List of discovered assets
        """
        for asset in discovered_assets:
            # Use MAC as key for deduplication
            mac = asset.get('mac', '')
            if not mac:
                continue
            
            # Check if asset exists
            existing = self.asset_db.get_asset_by_mac(mac)
            
            if existing:
                # Update existing asset
                existing.update({
                    "last_seen": datetime.utcnow().isoformat(),
                    "source": f"{existing.get('source', '')},passive"
                })
                self.asset_db.upsert_asset(existing)
            else:
                # Create new asset
                new_asset = {
                    "mac": mac,
                    "ip": asset.get('ip', ''),
                    "hostname": asset.get('hostname', ''),
                    "vendor": asset.get('vendor', ''),
                    "source": "passive",
                    "first_seen": asset.get('timestamp', datetime.utcnow().isoformat()),
                    "last_seen": datetime.utcnow().isoformat()
                }
                self.asset_db.upsert_asset(new_asset)
        
        logger.info(f"Processed {len(discovered_assets)} passive discoveries")

