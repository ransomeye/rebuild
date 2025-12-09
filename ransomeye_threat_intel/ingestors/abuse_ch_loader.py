# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/ingestors/abuse_ch_loader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Ingests MalwareBazaar (CSV) and ThreatFox (JSON) using streaming to avoid RAM overflow

import os
import sys
import csv
import json
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schema.knowledge_graph import get_session, IOC


class AbuseCHLoader:
    """Loads Abuse.ch data (MalwareBazaar and ThreatFox) with streaming."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            rebuild_root = Path(os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild'))
            self.data_dir = rebuild_root / 'ransomeye_threat_intel' / 'data'
        else:
            self.data_dir = Path(data_dir)
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string."""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except Exception:
                return None
    
    def load_malwarebazaar(self, file_path: Path, chunk_size: int = 10000) -> int:
        """Load MalwareBazaar CSV with streaming."""
        # Handle zip file
        if file_path.suffix == '.zip':
            zip_path = file_path
            with zipfile.ZipFile(zip_path, 'r') as z:
                csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                if not csv_files:
                    print(f"No CSV file found in {zip_path}")
                    return 0
                
                # Extract to temp location
                temp_dir = self.data_dir / 'temp'
                temp_dir.mkdir(exist_ok=True)
                csv_file = temp_dir / csv_files[0]
                z.extract(csv_files[0], temp_dir)
                file_path = csv_file
        
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return 0
        
        print(f"Loading: {file_path.name} (streaming mode)")
        
        session = get_session()
        count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                
                batch = []
                for row in reader:
                    try:
                        sha256_hash = row.get('sha256_hash', '').strip()
                        if not sha256_hash:
                            continue
                        
                        malware_family = row.get('signature', '') or row.get('malware_family', '')
                        first_seen = self.parse_date(row.get('first_seen', ''))
                        tags = row.get('tags', '')
                        
                        # Calculate maliciousness score (default 0.8 for MalwareBazaar entries)
                        maliciousness_score = 0.8
                        
                        stmt = insert(IOC).values(
                            value=sha256_hash,
                            type='hash',
                            maliciousness_score=maliciousness_score,
                            malware_family=malware_family,
                            first_seen=first_seen,
                            source='malwarebazaar',
                            tags=tags,
                            updated_at=datetime.utcnow()
                        )
                        
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['value', 'type'],
                            set_=dict(
                                maliciousness_score=stmt.excluded.maliciousness_score,
                                malware_family=stmt.excluded.malware_family,
                                first_seen=stmt.excluded.first_seen,
                                last_seen=datetime.utcnow(),
                                source=stmt.excluded.source,
                                tags=stmt.excluded.tags,
                                updated_at=stmt.excluded.updated_at
                            )
                        )
                        
                        batch.append(stmt)
                        
                        if len(batch) >= chunk_size:
                            for b in batch:
                                session.execute(b)
                            session.commit()
                            count += len(batch)
                            print(f"  Processed {count} IOCs...")
                            batch = []
                    
                    except Exception as e:
                        print(f"  Error processing row: {e}")
                        continue
                
                # Process remaining batch
                if batch:
                    for b in batch:
                        session.execute(b)
                    session.commit()
                    count += len(batch)
            
            print(f"  ✓ Loaded {count} IOCs from MalwareBazaar")
            
        except Exception as e:
            session.rollback()
            print(f"  ✗ Error loading {file_path.name}: {e}")
            raise
        finally:
            session.close()
        
        return count
    
    def load_threatfox(self, file_path: Path) -> int:
        """Load ThreatFox JSON."""
        # Handle zip file
        if file_path.suffix == '.zip':
            zip_path = file_path
            with zipfile.ZipFile(zip_path, 'r') as z:
                json_files = [f for f in z.namelist() if f.endswith('.json')]
                if not json_files:
                    print(f"No JSON file found in {zip_path}")
                    return 0
                
                # Extract to temp location
                temp_dir = self.data_dir / 'temp'
                temp_dir.mkdir(exist_ok=True)
                json_file = temp_dir / json_files[0]
                z.extract(json_files[0], temp_dir)
                file_path = json_file
        
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return 0
        
        print(f"Loading: {file_path.name}")
        
        session = get_session()
        count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            iocs = data if isinstance(data, list) else data.get('data', [])
            print(f"  Found {len(iocs)} IOCs")
            
            for ioc in iocs:
                try:
                    ioc_value = ioc.get('ioc_value', '').strip()
                    ioc_type_str = ioc.get('ioc_type', '').lower()
                    
                    if not ioc_value:
                        continue
                    
                    # Map ThreatFox types to our types
                    type_map = {
                        'ip:port': 'ip',
                        'domain': 'domain',
                        'url': 'url',
                        'md5': 'hash',
                        'sha256': 'hash',
                        'sha1': 'hash',
                    }
                    
                    ioc_type = type_map.get(ioc_type_str, 'ip')
                    
                    malware_family = ioc.get('malware', '')
                    threat_type = ioc.get('threat_type', '')
                    tags = json.dumps([threat_type]) if threat_type else None
                    
                    first_seen = self.parse_date(ioc.get('first_seen', ''))
                    last_seen = self.parse_date(ioc.get('last_seen', ''))
                    
                    # Calculate maliciousness score
                    maliciousness_score = 0.9 if threat_type else 0.7
                    
                    stmt = insert(IOC).values(
                        value=ioc_value,
                        type=ioc_type,
                        maliciousness_score=maliciousness_score,
                        malware_family=malware_family,
                        first_seen=first_seen,
                        last_seen=last_seen,
                        source='threatfox',
                        tags=tags,
                        updated_at=datetime.utcnow()
                    )
                    
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['value', 'type'],
                        set_=dict(
                            maliciousness_score=stmt.excluded.maliciousness_score,
                            malware_family=stmt.excluded.malware_family,
                            first_seen=stmt.excluded.first_seen,
                            last_seen=stmt.excluded.last_seen,
                            source=stmt.excluded.source,
                            tags=stmt.excluded.tags,
                            updated_at=stmt.excluded.updated_at
                        )
                    )
                    
                    session.execute(stmt)
                    count += 1
                    
                    if count % 1000 == 0:
                        session.commit()
                        print(f"  Processed {count} IOCs...")
                
                except Exception as e:
                    print(f"  Error processing IOC: {e}")
                    continue
            
            session.commit()
            print(f"  ✓ Loaded {count} IOCs from ThreatFox")
            
        except Exception as e:
            session.rollback()
            print(f"  ✗ Error loading {file_path.name}: {e}")
            raise
        finally:
            session.close()
        
        return count
    
    def load_all(self) -> dict:
        """Load all Abuse.ch data."""
        results = {}
        
        # MalwareBazaar
        mb_file = self.data_dir / 'full.csv.zip'
        if mb_file.exists():
            results['malwarebazaar'] = self.load_malwarebazaar(mb_file)
        
        # ThreatFox
        tf_file = self.data_dir / 'threatfox_full.json.zip'
        if tf_file.exists():
            results['threatfox'] = self.load_threatfox(tf_file)
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load Abuse.ch data (MalwareBazaar, ThreatFox)')
    parser.add_argument('--malwarebazaar', action='store_true', help='Load MalwareBazaar only')
    parser.add_argument('--threatfox', action='store_true', help='Load ThreatFox only')
    parser.add_argument('--data-dir', type=str, help='Data directory path')
    parser.add_argument('--chunk-size', type=int, default=10000, help='Chunk size for streaming')
    
    args = parser.parse_args()
    
    loader = AbuseCHLoader(data_dir=args.data_dir)
    
    if args.malwarebazaar:
        mb_file = loader.data_dir / 'full.csv.zip'
        count = loader.load_malwarebazaar(mb_file, chunk_size=args.chunk_size)
        print(f"\n✓ Loaded {count} IOCs from MalwareBazaar")
    elif args.threatfox:
        tf_file = loader.data_dir / 'threatfox_full.json.zip'
        count = loader.load_threatfox(tf_file)
        print(f"\n✓ Loaded {count} IOCs from ThreatFox")
    else:
        results = loader.load_all()
        print(f"\n✓ Loaded:")
        for key, count in results.items():
            print(f"  {key}: {count}")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

