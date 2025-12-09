# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/normalizer/enrichment.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Local GeoIP/ASN lookup wrapper (use geoip2 DB path from Env, handle missing DB gracefully)

import os
import ipaddress
from typing import Dict, Any, Optional
import logging

# Try to import geoip2
try:
    import geoip2.database
    import geoip2.errors
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    logging.warning("geoip2 not available. Install: pip install geoip2")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IOCEnricher:
    """
    Enriches IOCs with GeoIP and ASN information.
    Uses local GeoIP2 database.
    """
    
    def __init__(self, geoip_db_path: Optional[str] = None):
        """
        Initialize enricher.
        
        Args:
            geoip_db_path: Path to GeoIP2 database file
        """
        self.geoip_db_path = geoip_db_path or os.environ.get('GEOIP_DB_PATH', '')
        self.reader = None
        
        if self.geoip_db_path and os.path.exists(self.geoip_db_path) and GEOIP2_AVAILABLE:
            try:
                self.reader = geoip2.database.Reader(self.geoip_db_path)
                logger.info(f"Loaded GeoIP2 database from {self.geoip_db_path}")
            except Exception as e:
                logger.warning(f"Could not load GeoIP2 database: {e}")
        else:
            logger.warning("GeoIP2 database not available")
    
    def enrich(self, ioc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich IOC with GeoIP/ASN data.
        
        Args:
            ioc: IOC dictionary
            
        Returns:
            Enriched IOC dictionary
        """
        enriched = ioc.copy()
        value = ioc.get('value', '')
        ioc_type = ioc.get('type', '').lower()
        
        # Only enrich IP addresses
        if ioc_type not in ['ipv4', 'ipv6', 'ip']:
            return enriched
        
        try:
            ip = ipaddress.ip_address(value)
        except ValueError:
            return enriched
        
        enrichment = {}
        
        # GeoIP lookup
        geoip_data = self._lookup_geoip(ip)
        if geoip_data:
            enrichment['geoip'] = geoip_data
        
        # ASN lookup
        asn_data = self._lookup_asn(ip)
        if asn_data:
            enrichment['asn'] = asn_data
        
        if enrichment:
            enriched['enrichment'] = enrichment
        
        return enriched
    
    def _lookup_geoip(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> Optional[Dict[str, Any]]:
        """
        Lookup GeoIP data for IP address.
        
        Args:
            ip: IP address object
            
        Returns:
            GeoIP data dictionary or None
        """
        if not self.reader:
            return None
        
        try:
            response = self.reader.city(str(ip))
            
            geoip_data = {
                'country': response.country.iso_code or '',
                'country_name': response.country.name or '',
                'city': response.city.name or '',
                'latitude': float(response.location.latitude) if response.location.latitude else None,
                'longitude': float(response.location.longitude) if response.location.longitude else None
            }
            
            return geoip_data
        except geoip2.errors.AddressNotFoundError:
            return None
        except Exception as e:
            logger.warning(f"Error in GeoIP lookup: {e}")
            return None
    
    def _lookup_asn(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> Optional[Dict[str, Any]]:
        """
        Lookup ASN data for IP address.
        
        Args:
            ip: IP address object
            
        Returns:
            ASN data dictionary or None
        """
        if not self.reader:
            return None
        
        try:
            # Try ASN database (if available)
            # Note: This requires a separate ASN database file
            # For now, we'll try to get ASN from the city database if available
            response = self.reader.city(str(ip))
            
            # ASN data is typically in a separate database
            # This is a placeholder - real implementation would use ASN database
            return None
        except Exception as e:
            logger.debug(f"ASN lookup not available: {e}")
            return None
    
    def close(self):
        """Close GeoIP2 reader."""
        if self.reader:
            self.reader.close()

