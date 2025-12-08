# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/cve/cve_matcher.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Takes Service Banner and performs fuzzy matching against local SQLite CPE data

import os
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import thefuzz
try:
    from thefuzz import fuzz, process
    FUZZ_AVAILABLE = True
except ImportError:
    try:
        from fuzzywuzzy import fuzz, process
        FUZZ_AVAILABLE = True
    except ImportError:
        FUZZ_AVAILABLE = False
        logger.warning("thefuzz/fuzzywuzzy not available, using difflib for fuzzy matching")

if not FUZZ_AVAILABLE:
    import difflib

class CVEMatcher:
    """
    Matches service banners to CVEs using fuzzy matching.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize CVE matcher.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path or os.environ.get(
            'NVD_DB_PATH',
            '/home/ransomeye/rebuild/ransomeye_net_scanner/data/nvd.db'
        ))
        self.db_loaded = self.db_path.exists()
    
    def is_db_loaded(self) -> bool:
        """
        Check if CVE database is loaded.
        
        Returns:
            True if database exists, False otherwise
        """
        return self.db_loaded
    
    def match_banner(self, banner: str, threshold: int = 70) -> List[Dict[str, Any]]:
        """
        Match service banner to CVEs.
        
        Args:
            banner: Service banner string (e.g., "Apache 2.4.49")
            threshold: Fuzzy match threshold (0-100)
            
        Returns:
            List of matching CVEs with CVSS scores
        """
        if not self.is_db_loaded():
            logger.warning("CVE database not loaded")
            return []
        
        try:
            # Extract vendor, product, version from banner
            vendor, product, version = self._parse_banner(banner)
            
            if not product:
                return []
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Query CPEs matching vendor/product
            if vendor:
                cursor.execute('''
                    SELECT cpe, vendor, product, version, cve_ids
                    FROM cpes
                    WHERE vendor LIKE ? AND product LIKE ?
                ''', (f'%{vendor}%', f'%{product}%'))
            else:
                cursor.execute('''
                    SELECT cpe, vendor, product, version, cve_ids
                    FROM cpes
                    WHERE product LIKE ?
                ''', (f'%{product}%',))
            
            cpe_candidates = cursor.fetchall()
            
            # Fuzzy match against candidates
            matches = []
            for cpe, cpe_vendor, cpe_product, cpe_version, cve_ids in cpe_candidates:
                # Build comparison string
                cpe_string = f"{cpe_vendor} {cpe_product} {cpe_version}".strip()
                banner_normalized = banner.strip()
                
                # Calculate similarity
                if FUZZ_AVAILABLE:
                    similarity = fuzz.ratio(banner_normalized.lower(), cpe_string.lower())
                else:
                    similarity = difflib.SequenceMatcher(
                        None, banner_normalized.lower(), cpe_string.lower()
                    ).ratio() * 100
                
                if similarity >= threshold:
                    # Get CVE details
                    cve_id_list = cve_ids.split(',') if cve_ids else []
                    for cve_id in cve_id_list[:10]:  # Limit to top 10 CVEs
                        cursor.execute('''
                            SELECT cve_id, cvss_v3_score, cvss_v2_score, severity
                            FROM cves
                            WHERE cve_id = ?
                        ''', (cve_id,))
                        
                        cve_data = cursor.fetchone()
                        if cve_data:
                            matches.append({
                                'cve_id': cve_data[0],
                                'cvss_score': cve_data[1] or cve_data[2] or 0.0,
                                'severity': cve_data[3] or 'UNKNOWN',
                                'cpe': cpe,
                                'match_score': similarity
                            })
            
            conn.close()
            
            # Sort by CVSS score (descending)
            matches.sort(key=lambda x: x['cvss_score'], reverse=True)
            
            # Remove duplicates
            seen = set()
            unique_matches = []
            for match in matches:
                if match['cve_id'] not in seen:
                    seen.add(match['cve_id'])
                    unique_matches.append(match)
            
            logger.debug(f"Matched {len(unique_matches)} CVEs for banner: {banner}")
            return unique_matches[:20]  # Return top 20 matches
            
        except Exception as e:
            logger.error(f"Error matching banner: {e}", exc_info=True)
            return []
    
    def _parse_banner(self, banner: str) -> tuple:
        """
        Parse banner to extract vendor, product, version.
        
        Args:
            banner: Service banner string
            
        Returns:
            Tuple of (vendor, product, version)
        """
        # Common patterns
        # Apache 2.4.49
        # nginx/1.21.0
        # Microsoft IIS 10.0
        # OpenSSH 8.2
        
        banner = banner.strip()
        
        # Try to extract version
        version_pattern = r'(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)'
        version_match = re.search(version_pattern, banner)
        version = version_match.group(1) if version_match else ''
        
        # Remove version from banner
        banner_no_version = re.sub(version_pattern, '', banner).strip()
        
        # Split by common separators
        parts = re.split(r'[/\s]+', banner_no_version)
        
        if len(parts) >= 2:
            vendor = parts[0]
            product = parts[1]
        elif len(parts) == 1:
            vendor = ''
            product = parts[0]
        else:
            vendor = ''
            product = banner_no_version
        
        return (vendor, product, version)

