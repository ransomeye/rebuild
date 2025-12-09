# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/narrative/story_builder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Fetches linked data (CVE -> CWE -> Mitigation) and renders narrative stories using Jinja2

import os
import sys
from pathlib import Path
from typing import Optional, Dict
from jinja2 import Environment, FileSystemLoader, Template

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schema.knowledge_graph import get_session, Vulnerability, Weakness, Mitigation, Tactic


class StoryBuilder:
    """Builds narrative stories from threat intelligence data."""
    
    def __init__(self):
        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / 'templates'
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False
        )
        self.template = self.env.get_template('incident_story.j2')
    
    def fetch_vulnerability_data(self, cve_id: str, host_id: str = "unknown") -> Dict:
        """Fetch all linked data for a CVE."""
        session = get_session()
        
        try:
            # Get vulnerability
            vuln = session.query(Vulnerability).filter(
                Vulnerability.cve_id == cve_id
            ).first()
            
            if not vuln:
                return {
                    'cve_id': cve_id,
                    'host_id': host_id,
                    'weakness_name': 'Unknown',
                    'cwe_id': 'N/A',
                    'tactic_name': 'Unknown',
                    'mitigation_action': 'Review vulnerability details and apply patches'
                }
            
            # Get weakness (CWE)
            weakness_name = 'Unknown'
            cwe_id = 'N/A'
            if vuln.cwe_id:
                weakness = session.query(Weakness).filter(
                    Weakness.cwe_id == vuln.cwe_id
                ).first()
                if weakness:
                    weakness_name = weakness.name
                    cwe_id = weakness.cwe_id
            
            # Get mitigation (CISA KEV)
            mitigation_action = 'Review vulnerability details and apply patches'
            mitigations = session.query(Mitigation).filter(
                Mitigation.cve_id == cve_id
            ).all()
            if mitigations:
                # Use first mitigation's required action
                mitigation_action = mitigations[0].required_action
            
            # Get tactic (try to find from attack patterns linked to weakness)
            tactic_name = 'Unknown'
            if vuln.cwe_id:
                # Query for attack patterns linked to this CWE
                from sqlalchemy import text
                result = session.execute(text("""
                    SELECT DISTINCT t.name
                    FROM tactics t
                    JOIN tactic_attack_pattern tap ON t.mitre_id = tap.mitre_id
                    JOIN weakness_attack_pattern wap ON tap.capec_id = wap.capec_id
                    WHERE wap.cwe_id = :cwe_id
                    LIMIT 1
                """), {'cwe_id': vuln.cwe_id})
                row = result.fetchone()
                if row:
                    tactic_name = row[0]
            
            return {
                'cve_id': cve_id,
                'host_id': host_id,
                'weakness_name': weakness_name,
                'cwe_id': cwe_id,
                'tactic_name': tactic_name,
                'mitigation_action': mitigation_action
            }
        
        finally:
            session.close()
    
    def build_story(self, cve_id: str, host_id: str = "unknown") -> str:
        """Build narrative story for a CVE."""
        data = self.fetch_vulnerability_data(cve_id, host_id)
        return self.template.render(**data)
    
    def build_story_from_data(self, data: Dict) -> str:
        """Build story from provided data dictionary."""
        return self.template.render(**data)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate narrative story from CVE')
    parser.add_argument('cve_id', type=str, help='CVE ID (e.g., CVE-2021-44228)')
    parser.add_argument('--host-id', type=str, default='unknown', help='Host identifier')
    
    args = parser.parse_args()
    
    builder = StoryBuilder()
    story = builder.build_story(args.cve_id, args.host_id)
    
    print(story)
    sys.exit(0)


if __name__ == "__main__":
    main()

