# Path and File Name : /home/ransomeye/rebuild/ransomeye_delivery_assurance/tools/run_final_audit.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main entrypoint CLI that orchestrates all auditors and generates signed handover report

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auditors.structure_auditor import StructureAuditor
from auditors.content_auditor import ContentAuditor
from auditors.installer_auditor import InstallerAuditor
from tools.scan_for_forbidden import ForbiddenPatternScanner
from reporting.report_generator import ReportGenerator
from reporting.signer import ReportSigner


class FinalAuditOrchestrator:
    """Orchestrates all audit components."""
    
    def __init__(self, rebuild_root: str):
        self.rebuild_root = Path(rebuild_root)
        self.results = {
            'project_root': str(self.rebuild_root),
            'audit_version': '1.0.0',
            'timestamp': datetime.now().isoformat(),
            'categories': {},
            'summary': {
                'total_checks': 0,
                'passed_checks': 0,
                'failed_checks': 0,
                'warning_count': 0
            },
            'overall_status': 'UNKNOWN'
        }
        
    def run_structure_audit(self) -> bool:
        """Run structure audit."""
        print("=" * 60)
        print("Running Structure Audit...")
        print("=" * 60)
        
        auditor = StructureAuditor(str(self.rebuild_root))
        passed, results = auditor.run_audit()
        
        self.results['categories']['Structure'] = results
        self.results['summary']['total_checks'] += results.get('passed_count', 0) + results.get('error_count', 0)
        self.results['summary']['passed_checks'] += results.get('passed_count', 0)
        self.results['summary']['failed_checks'] += results.get('error_count', 0)
        self.results['summary']['warning_count'] += results.get('warning_count', 0)
        
        print(f"Structure Audit: {'PASSED' if passed else 'FAILED'}")
        print(f"  Errors: {results.get('error_count', 0)}")
        print(f"  Warnings: {results.get('warning_count', 0)}")
        print(f"  Passed: {results.get('passed_count', 0)}")
        
        return passed
    
    def run_content_audit(self) -> bool:
        """Run content audit."""
        print("\n" + "=" * 60)
        print("Running Content Audit...")
        print("=" * 60)
        
        auditor = ContentAuditor(str(self.rebuild_root))
        passed, results = auditor.run_audit()
        
        self.results['categories']['Content'] = results
        self.results['summary']['total_checks'] += results.get('files_checked', 0)
        self.results['summary']['passed_checks'] += results.get('passed_count', 0)
        self.results['summary']['failed_checks'] += results.get('error_count', 0)
        self.results['summary']['warning_count'] += results.get('warning_count', 0)
        
        print(f"Content Audit: {'PASSED' if passed else 'FAILED'}")
        print(f"  Files checked: {results.get('files_checked', 0)}")
        print(f"  Errors: {results.get('error_count', 0)}")
        print(f"  Passed: {results.get('passed_count', 0)}")
        
        return passed
    
    def run_installer_audit(self) -> bool:
        """Run installer audit."""
        print("\n" + "=" * 60)
        print("Running Installer Audit...")
        print("=" * 60)
        
        auditor = InstallerAuditor(str(self.rebuild_root))
        passed, results = auditor.run_audit()
        
        self.results['categories']['Installer'] = results
        self.results['summary']['total_checks'] += results.get('passed_count', 0) + results.get('error_count', 0)
        self.results['summary']['passed_checks'] += results.get('passed_count', 0)
        self.results['summary']['failed_checks'] += results.get('error_count', 0)
        self.results['summary']['warning_count'] += results.get('warning_count', 0)
        
        print(f"Installer Audit: {'PASSED' if passed else 'FAILED'}")
        print(f"  Errors: {results.get('error_count', 0)}")
        print(f"  Warnings: {results.get('warning_count', 0)}")
        print(f"  Passed: {results.get('passed_count', 0)}")
        
        return passed
    
    def run_security_scan(self) -> bool:
        """Run security/forbidden pattern scan."""
        print("\n" + "=" * 60)
        print("Running Security Scan...")
        print("=" * 60)
        
        scanner = ForbiddenPatternScanner(str(self.rebuild_root))
        passed, results = scanner.run_scan()
        
        self.results['categories']['Security'] = results
        self.results['summary']['total_checks'] += results.get('files_scanned', 0)
        self.results['summary']['passed_checks'] += results.get('passed_count', 0)
        self.results['summary']['failed_checks'] += results.get('error_count', 0)
        self.results['summary']['warning_count'] += results.get('warning_count', 0)
        
        print(f"Security Scan: {'PASSED' if passed else 'FAILED'}")
        print(f"  Files scanned: {results.get('files_scanned', 0)}")
        print(f"  Errors: {results.get('error_count', 0)}")
        print(f"  Warnings: {results.get('warning_count', 0)}")
        print(f"  Passed: {results.get('passed_count', 0)}")
        
        return passed
    
    def generate_report(self, output_dir: Path) -> Path:
        """Generate PDF report."""
        print("\n" + "=" * 60)
        print("Generating Handover Report...")
        print("=" * 60)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / "final_handover_report.pdf"
        
        generator = ReportGenerator(str(pdf_path))
        generated_path = generator.generate_report(self.results)
        
        print(f"Report generated: {generated_path}")
        return Path(generated_path)
    
    def sign_report(self, pdf_path: Path) -> tuple[str, str]:
        """Sign the PDF report."""
        print("\n" + "=" * 60)
        print("Signing Handover Report...")
        print("=" * 60)
        
        signer = ReportSigner()
        signature, file_hash = signer.sign_file(pdf_path)
        sig_file = signer.create_signature_file(pdf_path, signature, file_hash)
        
        print(f"Report signed: {pdf_path}")
        print(f"Signature file: {sig_file}")
        print(f"Hash: {file_hash}")
        
        return signature, file_hash
    
    def save_results_json(self, output_dir: Path) -> Path:
        """Save audit results as JSON."""
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "audit_results.json"
        
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        return json_path
    
    def run_full_audit(self, output_dir: str = None, sign: bool = True) -> bool:
        """Run complete audit pipeline."""
        if output_dir is None:
            output_dir = self.rebuild_root / "logs" / "delivery_assurance"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run all audits
        audit_results = []
        audit_results.append(("Structure", self.run_structure_audit()))
        audit_results.append(("Content", self.run_content_audit()))
        audit_results.append(("Installer", self.run_installer_audit()))
        audit_results.append(("Security", self.run_security_scan()))
        
        # Determine overall status
        all_passed = all(result[1] for result in audit_results)
        self.results['overall_status'] = 'PASSED' if all_passed else 'FAILED'
        
        # Generate report
        pdf_path = self.generate_report(output_dir)
        
        # Sign report
        if sign:
            signature, file_hash = self.sign_report(pdf_path)
            self.results['signature'] = signature
            self.results['file_hash'] = file_hash
        
        # Save JSON results
        json_path = self.save_results_json(output_dir)
        
        # Print summary
        print("\n" + "=" * 60)
        print("AUDIT SUMMARY")
        print("=" * 60)
        print(f"Overall Status: {self.results['overall_status']}")
        print(f"Total Checks: {self.results['summary']['total_checks']}")
        print(f"Passed: {self.results['summary']['passed_checks']}")
        print(f"Failed: {self.results['summary']['failed_checks']}")
        print(f"Warnings: {self.results['summary']['warning_count']}")
        print(f"\nReport: {pdf_path}")
        print(f"Results JSON: {json_path}")
        
        return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run final delivery assurance audit for RansomEye'
    )
    parser.add_argument(
        '--root',
        type=str,
        default=os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild'),
        help='Root directory of RansomEye project'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory for reports (default: <root>/logs/delivery_assurance)'
    )
    parser.add_argument(
        '--no-sign',
        action='store_true',
        help='Skip PDF signing'
    )
    parser.add_argument(
        '--category',
        type=str,
        choices=['structure', 'content', 'installer', 'security', 'all'],
        default='all',
        help='Run specific audit category only'
    )
    
    args = parser.parse_args()
    
    orchestrator = FinalAuditOrchestrator(args.root)
    
    if args.category == 'all':
        passed = orchestrator.run_full_audit(
            output_dir=args.output,
            sign=not args.no_sign
        )
    else:
        # Run single category
        category_map = {
            'structure': orchestrator.run_structure_audit,
            'content': orchestrator.run_content_audit,
            'installer': orchestrator.run_installer_audit,
            'security': orchestrator.run_security_scan
        }
        passed = category_map[args.category]()
    
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

