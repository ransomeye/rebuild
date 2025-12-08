# Path and File Name : /home/ransomeye/rebuild/ransomeye_net_scanner/cve/nvd_loader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Utility to read NVD 2.0 JSON dump and load CPE, CVE ID, CVSS into local SQLite

import os
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NVDLoader:
    """
    Loads NVD JSON data into local SQLite database.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize NVD loader.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path or os.environ.get(
            'NVD_DB_PATH',
            '/home/ransomeye/rebuild/ransomeye_net_scanner/data/nvd.db'
        ))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create CVE table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cves (
                cve_id TEXT PRIMARY KEY,
                cpe TEXT,
                description TEXT,
                cvss_v3_score REAL,
                cvss_v2_score REAL,
                published_date TEXT,
                severity TEXT
            )
        ''')
        
        # Create CPE table for faster matching
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cpes (
                cpe TEXT PRIMARY KEY,
                vendor TEXT,
                product TEXT,
                version TEXT,
                cve_ids TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cpe ON cpes(cpe)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vendor_product ON cpes(vendor, product)')
        
        conn.commit()
        conn.close()
        logger.info(f"NVD database initialized: {self.db_path}")
    
    def load_nvd_json(self, json_file: Path):
        """
        Load NVD 2.0 JSON file into database.
        
        Args:
            json_file: Path to NVD JSON file
        """
        json_file = Path(json_file)
        
        if not json_file.exists():
            logger.error(f"NVD JSON file not found: {json_file}")
            return
        
        logger.info(f"Loading NVD data from: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Process CVE items
        items = data.get('CVE_Items', [])
        loaded_count = 0
        
        for item in items:
            cve_id = item.get('cve', {}).get('CVE_data_meta', {}).get('ID', '')
            if not cve_id:
                continue
            
            # Extract description
            descriptions = item.get('cve', {}).get('description', {}).get('description_data', [])
            description = descriptions[0].get('value', '') if descriptions else ''
            
            # Extract CVSS scores
            impact = item.get('impact', {})
            cvss_v3 = impact.get('baseMetricV3', {}).get('cvssV3', {})
            cvss_v2 = impact.get('baseMetricV2', {}).get('cvssV2', {})
            
            cvss_v3_score = cvss_v3.get('baseScore', 0.0)
            cvss_v2_score = cvss_v2.get('baseScore', 0.0)
            
            # Determine severity
            severity = 'UNKNOWN'
            if cvss_v3_score >= 9.0:
                severity = 'CRITICAL'
            elif cvss_v3_score >= 7.0:
                severity = 'HIGH'
            elif cvss_v3_score >= 4.0:
                severity = 'MEDIUM'
            elif cvss_v3_score > 0:
                severity = 'LOW'
            
            # Extract CPE configurations
            configurations = item.get('configurations', {}).get('nodes', [])
            cpes = []
            
            for config in configurations:
                cpe_matches = config.get('cpe_match', [])
                for cpe_match in cpe_matches:
                    cpe_string = cpe_match.get('cpe23Uri', '')
                    if cpe_string:
                        cpes.append(cpe_string)
            
            # Insert CVE
            cursor.execute('''
                INSERT OR REPLACE INTO cves 
                (cve_id, description, cvss_v3_score, cvss_v2_score, severity)
                VALUES (?, ?, ?, ?, ?)
            ''', (cve_id, description, cvss_v3_score, cvss_v2_score, severity))
            
            # Insert CPEs
            for cpe in cpes:
                # Parse CPE
                parts = cpe.split(':')
                if len(parts) >= 5:
                    vendor = parts[3] if len(parts) > 3 else ''
                    product = parts[4] if len(parts) > 4 else ''
                    version = parts[5] if len(parts) > 5 else ''
                    
                    # Get existing CVE IDs for this CPE
                    cursor.execute('SELECT cve_ids FROM cpes WHERE cpe = ?', (cpe,))
                    result = cursor.fetchone()
                    existing_cves = result[0] if result else ''
                    cve_list = existing_cves.split(',') if existing_cves else []
                    if cve_id not in cve_list:
                        cve_list.append(cve_id)
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO cpes 
                        (cpe, vendor, product, version, cve_ids)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (cpe, vendor, product, version, ','.join(cve_list)))
            
            loaded_count += 1
            
            if loaded_count % 1000 == 0:
                conn.commit()
                logger.info(f"Loaded {loaded_count} CVEs...")
        
        conn.commit()
        conn.close()
        
        logger.info(f"NVD data loaded: {loaded_count} CVEs from {json_file}")

