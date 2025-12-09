# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/tools/import_benchmark.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool to import standard benchmark formats (placeholder logic for XML parsing structure)

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..rules.loader import RulesLoader
from ..rules.validator import RulesValidator
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BenchmarkImporter:
    """
    Imports compliance benchmarks from standard formats.
    Note: This is a placeholder structure - actual CIS/NIST benchmarks are copyrighted.
    Tests generate synthetic compliance rules at runtime.
    """
    
    def __init__(self):
        """Initialize benchmark importer."""
        self.rules_loader = RulesLoader()
        self.validator = RulesValidator()
    
    def parse_xml_benchmark(self, xml_path: str) -> Dict[str, Any]:
        """
        Parse XML benchmark file (placeholder structure).
        
        Args:
            xml_path: Path to XML benchmark file
            
        Returns:
            Parsed benchmark dictionary
        """
        # Placeholder: In production, would parse XML structure
        # For now, return empty structure
        logger.warning("XML benchmark parsing is a placeholder - use YAML policies instead")
        
        return {
            'name': 'synthetic_benchmark',
            'description': 'Synthetic benchmark for testing',
            'rules': []
        }
    
    def convert_to_policy_yaml(self, benchmark: Dict[str, Any], output_path: str):
        """
        Convert benchmark to policy YAML format.
        
        Args:
            benchmark: Benchmark dictionary
            output_path: Output YAML file path
        """
        policy_yaml = {
            'name': benchmark.get('name', 'imported_benchmark'),
            'description': benchmark.get('description', 'Imported benchmark'),
            'rules': benchmark.get('rules', [])
        }
        
        # Validate policy
        is_valid, errors = self.validator.validate_policy(policy_yaml)
        if not is_valid:
            logger.error(f"Policy validation failed: {errors}")
            raise ValueError(f"Invalid policy: {errors}")
        
        # Write YAML
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(policy_yaml, f, default_flow_style=False)
        
        logger.info(f"Policy YAML written to: {output_path}")

def generate_synthetic_policy(output_path: str):
    """
    Generate synthetic compliance policy for testing.
    
    Args:
        output_path: Output YAML file path
    """
    synthetic_policy = {
        'name': 'synthetic_security_policy',
        'description': 'Synthetic security compliance policy for testing (not a real CIS/NIST benchmark)',
        'rules': [
            {
                'rule_id': 'rule_001',
                'rule_name': 'Kernel Version Check',
                'severity': 'high',
                'check': {
                    'field': 'kernel_version',
                    'operator': 'neq',
                    'value': ''
                },
                'remediation': {
                    'description': 'Ensure kernel version is specified',
                    'command': 'uname -r'
                },
                'weight': 5.0
            },
            {
                'rule_id': 'rule_002',
                'rule_name': 'Open Ports Limit',
                'severity': 'medium',
                'check': {
                    'field': 'open_ports',
                    'operator': 'lt',
                    'value': 20
                },
                'remediation': {
                    'description': 'Review and close unnecessary open ports',
                    'command': 'netstat -tuln'
                },
                'weight': 2.0
            },
            {
                'rule_id': 'rule_003',
                'rule_name': 'SSH Service Check',
                'severity': 'critical',
                'check': {
                    'field': 'services',
                    'operator': 'contains',
                    'value': 'sshd'
                },
                'remediation': {
                    'description': 'Ensure SSH service is running',
                    'command': 'systemctl status sshd'
                },
                'weight': 10.0
            }
        ]
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(synthetic_policy, f, default_flow_style=False)
    
    logger.info(f"Synthetic policy generated: {output_path}")

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Import compliance benchmarks')
    parser.add_argument('--input', type=str, help='Input benchmark file path')
    parser.add_argument('--output', type=str, help='Output YAML policy path')
    parser.add_argument('--generate-synthetic', action='store_true',
                       help='Generate synthetic policy for testing')
    
    args = parser.parse_args()
    
    if args.generate_synthetic:
        output = args.output or '/home/ransomeye/rebuild/ransomeye_hnmp_engine/policies/synthetic_policy.yaml'
        generate_synthetic_policy(output)
    elif args.input and args.output:
        importer = BenchmarkImporter()
        benchmark = importer.parse_xml_benchmark(args.input)
        importer.convert_to_policy_yaml(benchmark, args.output)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

