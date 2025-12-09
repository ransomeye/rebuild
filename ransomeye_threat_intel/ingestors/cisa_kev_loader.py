# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/ingestors/cisa_kev_loader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Ingests CISA Known Exploited Vulnerabilities JSON and links to CVEs

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schema.knowledge_graph import get_session, Mitigation


class CISAKEVLoader:
    """Loads CISA Known Exploited Vulnerabilities."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            rebuild_root = Path(os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild'))
            self.data_dir = rebuild_root / 'ransomeye_threat_intel' / 'data'
        else:
            self.data_dir = Path(data_dir)
    
    def parse_date(self, date_str: str) -> datetime:
        """Parse date string."""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return datetime.utcnow()
    
    def load_file(self, file_path: Path) -> int:
        """Load CISA KEV JSON file."""
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return 0
        
        print(f"Loading: {file_path.name}")
        
        session = get_session()
        count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            vulnerabilities = data.get('vulnerabilities', [])
            print(f"  Found {len(vulnerabilities)} KEV entries")
            
            for vuln in vulnerabilities:
                try:
                    cve_id = vuln.get('cveID')
                    if not cve_id:
                        continue
                    
                    required_action = vuln.get('requiredAction', 'Apply updates')
                    vendor_project = vuln.get('vendorProject', '')
                    product = vuln.get('product', '')
                    
                    # Parse dates
                    added_date_str = vuln.get('dateAdded', '')
                    due_date_str = vuln.get('dueDate', '')
                    
                    added_date = self.parse_date(added_date_str) if added_date_str else None
                    due_date = self.parse_date(due_date_str) if due_date_str else None
                    
                    # Upsert mitigation
                    stmt = insert(Mitigation).values(
                        cve_id=cve_id,
                        required_action=required_action,
                        vendor_project=vendor_project,
                        product=product,
                        added_date=added_date,
                        due_date=due_date,
                        updated_at=datetime.utcnow()
                    )
                    
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['cve_id', 'required_action'],
                        set_=dict(
                            vendor_project=stmt.excluded.vendor_project,
                            product=stmt.excluded.product,
                            added_date=stmt.excluded.added_date,
                            due_date=stmt.excluded.due_date,
                            updated_at=stmt.excluded.updated_at
                        )
                    )
                    
                    session.execute(stmt)
                    count += 1
                
                except Exception as e:
                    print(f"  Error processing KEV entry: {e}")
                    continue
            
            session.commit()
            print(f"  ✓ Loaded {count} KEV entries")
            
        except Exception as e:
            session.rollback()
            print(f"  ✗ Error loading {file_path.name}: {e}")
            raise
        finally:
            session.close()
        
        return count
    
    def load(self) -> int:
        """Load CISA KEV data."""
        file_path = self.data_dir / 'known_exploited_vulnerabilities.json'
        return self.load_file(file_path)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load CISA KEV data')
    parser.add_argument('--file', type=str, help='Load specific file')
    parser.add_argument('--data-dir', type=str, help='Data directory path')
    
    args = parser.parse_args()
    
    loader = CISAKEVLoader(data_dir=args.data_dir)
    
    if args.file:
        count = loader.load_file(Path(args.file))
    else:
        count = loader.load()
    
    print(f"\n✓ Loaded {count} KEV entries")
    sys.exit(0)


if __name__ == "__main__":
    main()

