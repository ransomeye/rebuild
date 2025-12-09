# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/ingestors/nvd_loader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Loads NVD CVE data from JSON.gz files and upserts to database

import os
import sys
import gzip
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schema.knowledge_graph import get_session, Vulnerability


class NVDLoader:
    """Loads NVD CVE data from JSON.gz files."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            rebuild_root = Path(os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild'))
            self.data_dir = rebuild_root / 'ransomeye_threat_intel' / 'data'
        else:
            self.data_dir = Path(data_dir)
    
    def parse_cvss_v3(self, metrics: dict):
        """Extract CVSS v3 score and severity."""
        if 'cvssV3_0' in metrics:
            cvss = metrics['cvssV3_0']
            score = cvss.get('baseScore')
            severity = cvss.get('baseSeverity')
            return score, severity
        elif 'cvssV3_1' in metrics:
            cvss = metrics['cvssV3_1']
            score = cvss.get('baseScore')
            severity = cvss.get('baseSeverity')
            return score, severity
        return None, None
    
    def parse_cvss_v2(self, metrics: dict) -> Optional[float]:
        """Extract CVSS v2 score."""
        if 'cvssV2' in metrics:
            return metrics['cvssV2'].get('baseScore')
        return None
    
    def extract_cwe_id(self, cve_item: dict) -> Optional[str]:
        """Extract CWE ID from CVE item."""
        try:
            problem_types = cve_item.get('cve', {}).get('problemType', {}).get('problemTypeData', [])
            for problem in problem_types:
                descriptions = problem.get('description', [])
                for desc in descriptions:
                    value = desc.get('value', '')
                    if value.startswith('CWE-'):
                        return value
        except Exception:
            pass
        return None
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse ISO date string."""
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return None
    
    def load_file(self, file_path: Path) -> int:
        """Load a single NVD JSON.gz file."""
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return 0
        
        print(f"Loading: {file_path.name}")
        
        session = get_session()
        count = 0
        
        try:
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            cve_items = data.get('CVE_Items', [])
            print(f"  Found {len(cve_items)} CVEs")
            
            for cve_item in cve_items:
                try:
                    cve_data = cve_item.get('cve', {})
                    cve_id = cve_data.get('CVE_data_meta', {}).get('ID')
                    
                    if not cve_id:
                        continue
                    
                    # Extract description
                    descriptions = cve_data.get('description', {}).get('description_data', [])
                    description = descriptions[0].get('value', '') if descriptions else None
                    
                    # Extract metrics
                    impact = cve_item.get('impact', {})
                    metrics = impact.get('baseMetricV3', {}) or impact.get('baseMetricV2', {})
                    
                    # Get CVSS scores
                    cvss_v3_score, severity = self.parse_cvss_v3(impact)
                    cvss_v2_score = self.parse_cvss_v2(impact)
                    
                    if not severity and cvss_v2_score:
                        # Map v2 score to severity
                        if cvss_v2_score >= 7.0:
                            severity = 'HIGH'
                        elif cvss_v2_score >= 4.0:
                            severity = 'MEDIUM'
                        else:
                            severity = 'LOW'
                    
                    # Extract dates
                    published_date = self.parse_date(cve_item.get('publishedDate', ''))
                    modified_date = self.parse_date(cve_item.get('lastModifiedDate', ''))
                    
                    # Extract CWE
                    cwe_id = self.extract_cwe_id(cve_item)
                    
                    # Upsert vulnerability
                    stmt = insert(Vulnerability).values(
                        cve_id=cve_id,
                        description=description,
                        severity=severity,
                        cvss_v3_score=cvss_v3_score,
                        cvss_v2_score=cvss_v2_score,
                        published_date=published_date,
                        modified_date=modified_date,
                        cwe_id=cwe_id,
                        updated_at=datetime.utcnow()
                    )
                    
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['cve_id'],
                        set_=dict(
                            description=stmt.excluded.description,
                            severity=stmt.excluded.severity,
                            cvss_v3_score=stmt.excluded.cvss_v3_score,
                            cvss_v2_score=stmt.excluded.cvss_v2_score,
                            published_date=stmt.excluded.published_date,
                            modified_date=stmt.excluded.modified_date,
                            cwe_id=stmt.excluded.cwe_id,
                            updated_at=stmt.excluded.updated_at
                        )
                    )
                    
                    session.execute(stmt)
                    count += 1
                    
                    if count % 1000 == 0:
                        session.commit()
                        print(f"  Processed {count} CVEs...")
                
                except Exception as e:
                    print(f"  Error processing CVE: {e}")
                    continue
            
            session.commit()
            print(f"  ✓ Loaded {count} CVEs from {file_path.name}")
            
        except Exception as e:
            session.rollback()
            print(f"  ✗ Error loading {file_path.name}: {e}")
            raise
        finally:
            session.close()
        
        return count
    
    def load_all(self) -> int:
        """Load all NVD files in data directory."""
        nvd_files = sorted(self.data_dir.glob('nvdcve-2.0-*.json.gz'))
        
        if not nvd_files:
            print(f"No NVD files found in {self.data_dir}")
            return 0
        
        print(f"Found {len(nvd_files)} NVD files")
        print("")
        
        total = 0
        for nvd_file in nvd_files:
            count = self.load_file(nvd_file)
            total += count
        
        print(f"\n✓ Total CVEs loaded: {total}")
        return total


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load NVD CVE data from JSON.gz files')
    parser.add_argument('--file', type=str, help='Load specific file')
    parser.add_argument('--data-dir', type=str, help='Data directory path')
    
    args = parser.parse_args()
    
    loader = NVDLoader(data_dir=args.data_dir)
    
    if args.file:
        count = loader.load_file(Path(args.file))
        print(f"\n✓ Loaded {count} CVEs")
    else:
        total = loader.load_all()
        print(f"\n✓ Total: {total} CVEs")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

