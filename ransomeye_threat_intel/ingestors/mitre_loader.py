# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/ingestors/mitre_loader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Parses MITRE ATT&CK (JSON/STIX), CAPEC (XML), and CWE (XML) data

import os
import sys
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schema.knowledge_graph import (
    get_session, Weakness, AttackPattern, Tactic,
    weakness_attack_pattern, tactic_attack_pattern
)


class MITRELoader:
    """Loads MITRE ATT&CK, CAPEC, and CWE data."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            rebuild_root = Path(os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild'))
            self.data_dir = rebuild_root / 'ransomeye_threat_intel' / 'data'
        else:
            self.data_dir = Path(data_dir)
    
    def load_attack(self, file_path: Path) -> int:
        """Load MITRE ATT&CK JSON (STIX format)."""
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return 0
        
        print(f"Loading: {file_path.name}")
        
        session = get_session()
        count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            objects = data.get('objects', [])
            print(f"  Found {len(objects)} STIX objects")
            
            for obj in objects:
                try:
                    obj_type = obj.get('type', '')
                    
                    # Handle tactics (x-mitre-tactic)
                    if obj_type == 'x-mitre-tactic':
                        mitre_id = obj.get('id', '')
                        name = obj.get('name', '')
                        description = obj.get('description', '')
                        external_id = obj.get('x_mitre_shortname', '')
                        
                        if mitre_id:
                            stmt = insert(Tactic).values(
                                mitre_id=mitre_id,
                                name=name,
                                description=description,
                                external_id=external_id,
                                updated_at=datetime.utcnow()
                            )
                            
                            stmt = stmt.on_conflict_do_update(
                                index_elements=['mitre_id'],
                                set_=dict(
                                    name=stmt.excluded.name,
                                    description=stmt.excluded.description,
                                    external_id=stmt.excluded.external_id,
                                    updated_at=stmt.excluded.updated_at
                                )
                            )
                            
                            session.execute(stmt)
                            count += 1
                
                except Exception as e:
                    print(f"  Error processing STIX object: {e}")
                    continue
            
            session.commit()
            print(f"  ✓ Loaded {count} tactics")
            
        except Exception as e:
            session.rollback()
            print(f"  ✗ Error loading {file_path.name}: {e}")
            raise
        finally:
            session.close()
        
        return count
    
    def load_capec(self, file_path: Path) -> int:
        """Load MITRE CAPEC XML."""
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return 0
        
        print(f"Loading: {file_path.name}")
        
        session = get_session()
        count = 0
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Find namespace
            ns = {'capec': root.tag.split('}')[0].strip('{') if '}' in root.tag else ''}
            
            attack_patterns = root.findall('.//capec:Attack_Pattern', ns) or root.findall('.//Attack_Pattern')
            
            print(f"  Found {len(attack_patterns)} attack patterns")
            
            for pattern in attack_patterns:
                try:
                    capec_id = pattern.get('ID') or pattern.findtext('ID', '')
                    name = pattern.findtext('Name', '')
                    description = pattern.findtext('Description', '')
                    
                    # Extract step-by-step logic
                    execution_flows = pattern.findall('.//Execution_Flow')
                    step_logic = []
                    for flow in execution_flows:
                        steps = flow.findall('.//Step')
                        for step in steps:
                            step_text = step.findtext('Description', '')
                            if step_text:
                                step_logic.append(step_text)
                    
                    step_by_step_logic = '\n'.join(step_logic) if step_logic else None
                    
                    # Extract likelihood and severity
                    likelihood = pattern.findtext('Likelihood_Of_Attack', '')
                    severity = pattern.findtext('Typical_Severity', '')
                    
                    if capec_id:
                        stmt = insert(AttackPattern).values(
                            capec_id=capec_id,
                            name=name,
                            step_by_step_logic=step_by_step_logic,
                            description=description,
                            likelihood_of_attack=likelihood,
                            typical_severity=severity,
                            updated_at=datetime.utcnow()
                        )
                        
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['capec_id'],
                            set_=dict(
                                name=stmt.excluded.name,
                                step_by_step_logic=stmt.excluded.step_by_step_logic,
                                description=stmt.excluded.description,
                                likelihood_of_attack=stmt.excluded.likelihood_of_attack,
                                typical_severity=stmt.excluded.typical_severity,
                                updated_at=stmt.excluded.updated_at
                            )
                        )
                        
                        session.execute(stmt)
                        count += 1
                
                except Exception as e:
                    print(f"  Error processing CAPEC pattern: {e}")
                    continue
            
            session.commit()
            print(f"  ✓ Loaded {count} attack patterns")
            
        except Exception as e:
            session.rollback()
            print(f"  ✗ Error loading {file_path.name}: {e}")
            raise
        finally:
            session.close()
        
        return count
    
    def load_cwe(self, file_path: Path) -> int:
        """Load MITRE CWE XML (may be in zip)."""
        # Handle zip file
        if file_path.suffix == '.zip':
            zip_path = file_path
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Find XML file
                xml_files = [f for f in z.namelist() if f.endswith('.xml')]
                if not xml_files:
                    print(f"No XML file found in {zip_path}")
                    return 0
                
                # Extract to temp location
                temp_dir = self.data_dir / 'temp'
                temp_dir.mkdir(exist_ok=True)
                xml_file = temp_dir / xml_files[0]
                z.extract(xml_files[0], temp_dir)
                file_path = xml_file
        
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return 0
        
        print(f"Loading: {file_path.name}")
        
        session = get_session()
        count = 0
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Find namespace
            ns = {'cwe': root.tag.split('}')[0].strip('{') if '}' in root.tag else ''}
            
            weaknesses = root.findall('.//cwe:Weakness', ns) or root.findall('.//Weakness')
            
            print(f"  Found {len(weaknesses)} weaknesses")
            
            for weakness in weaknesses:
                try:
                    cwe_id = weakness.get('ID') or weakness.get('ID', '')
                    name = weakness.findtext('Name', '')
                    description = weakness.findtext('Description', '')
                    abstraction = weakness.get('Abstraction', '')
                    status = weakness.get('Status', '')
                    
                    if cwe_id:
                        stmt = insert(Weakness).values(
                            cwe_id=cwe_id,
                            name=name,
                            description=description,
                            abstraction=abstraction,
                            status=status,
                            updated_at=datetime.utcnow()
                        )
                        
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['cwe_id'],
                            set_=dict(
                                name=stmt.excluded.name,
                                description=stmt.excluded.description,
                                abstraction=stmt.excluded.abstraction,
                                status=stmt.excluded.status,
                                updated_at=stmt.excluded.updated_at
                            )
                        )
                        
                        session.execute(stmt)
                        count += 1
                
                except Exception as e:
                    print(f"  Error processing CWE: {e}")
                    continue
            
            session.commit()
            print(f"  ✓ Loaded {count} weaknesses")
            
        except Exception as e:
            session.rollback()
            print(f"  ✗ Error loading {file_path.name}: {e}")
            raise
        finally:
            session.close()
        
        return count
    
    def load_all(self) -> dict:
        """Load all MITRE data."""
        results = {}
        
        # ATT&CK
        attack_file = self.data_dir / 'enterprise-attack.json'
        if attack_file.exists():
            results['attack'] = self.load_attack(attack_file)
        
        # CAPEC
        capec_file = self.data_dir / 'capec_latest.xml'
        if capec_file.exists():
            results['capec'] = self.load_capec(capec_file)
        
        # CWE
        cwe_file = self.data_dir / 'cwec_latest.xml.zip'
        if not cwe_file.exists():
            cwe_file = self.data_dir / 'cwec_latest.xml'
        if cwe_file.exists():
            results['cwe'] = self.load_cwe(cwe_file)
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load MITRE data (ATT&CK, CAPEC, CWE)')
    parser.add_argument('--attack', action='store_true', help='Load ATT&CK only')
    parser.add_argument('--capec', action='store_true', help='Load CAPEC only')
    parser.add_argument('--cwe', action='store_true', help='Load CWE only')
    parser.add_argument('--data-dir', type=str, help='Data directory path')
    
    args = parser.parse_args()
    
    loader = MITRELoader(data_dir=args.data_dir)
    
    if args.attack:
        attack_file = loader.data_dir / 'enterprise-attack.json'
        count = loader.load_attack(attack_file)
        print(f"\n✓ Loaded {count} tactics")
    elif args.capec:
        capec_file = loader.data_dir / 'capec_latest.xml'
        count = loader.load_capec(capec_file)
        print(f"\n✓ Loaded {count} attack patterns")
    elif args.cwe:
        cwe_file = loader.data_dir / 'cwec_latest.xml.zip'
        if not cwe_file.exists():
            cwe_file = loader.data_dir / 'cwec_latest.xml'
        count = loader.load_cwe(cwe_file)
        print(f"\n✓ Loaded {count} weaknesses")
    else:
        results = loader.load_all()
        print(f"\n✓ Loaded:")
        for key, count in results.items():
            print(f"  {key}: {count}")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

