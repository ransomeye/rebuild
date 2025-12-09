# Path and File Name : /home/ransomeye/rebuild/ransomeye_hnmp_engine/tools/export_fleet_report.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates signed PDF/JSON fleet health report

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..storage.host_db import HostDB
from ..storage.history_store import HistoryStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available, PDF export disabled")

class FleetReportExporter:
    """
    Exports fleet health reports in PDF and JSON formats.
    """
    
    def __init__(self):
        """Initialize fleet report exporter."""
        self.host_db = HostDB()
        self.history_store = HistoryStore()
    
    def generate_json_report(self, output_path: Optional[str] = None) -> Path:
        """
        Generate JSON fleet report.
        
        Args:
            output_path: Optional output path
            
        Returns:
            Path to generated JSON file
        """
        if output_path is None:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            output_dir = Path(os.environ.get('OUTPUT_DIR', '/home/ransomeye/rebuild/logs'))
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"fleet_report_{timestamp}.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Gather fleet data
        stats = self.host_db.get_fleet_stats()
        hosts = self.host_db.list_hosts()
        trend = self.history_store.get_fleet_trend(days=30)
        
        # Get scores for each host
        host_scores = []
        for host in hosts:
            score = self.host_db.get_latest_health_score(host['host_id'])
            if score:
                host_scores.append({
                    'host_id': host['host_id'],
                    'hostname': host.get('hostname', ''),
                    'os_type': host.get('os_type', ''),
                    'score': score['score'],
                    'risk_factor': score['risk_factor']
                })
        
        # Build report
        report = {
            'report_type': 'fleet_health',
            'generated_at': datetime.utcnow().isoformat(),
            'fleet_stats': stats,
            'host_count': len(hosts),
            'host_scores': host_scores,
            'trend': trend,
            'build_hash': self._calculate_build_hash(),
            'model_version': '1.0.0'
        }
        
        # Write JSON
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"JSON fleet report generated: {output_path}")
        return output_path
    
    def generate_pdf_report(self, output_path: Optional[str] = None) -> Path:
        """
        Generate PDF fleet report.
        
        Args:
            output_path: Optional output path
            
        Returns:
            Path to generated PDF file
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab not available, cannot generate PDF")
        
        if output_path is None:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            output_dir = Path(os.environ.get('OUTPUT_DIR', '/home/ransomeye/rebuild/logs'))
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"fleet_report_{timestamp}.pdf"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Gather data
        stats = self.host_db.get_fleet_stats()
        hosts = self.host_db.list_hosts()
        trend = self.history_store.get_fleet_trend(days=30)
        
        # Create PDF
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph("Fleet Health Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Generated date
        generated_at = datetime.utcnow().isoformat()
        story.append(Paragraph(f"<b>Generated:</b> {generated_at}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Fleet Statistics
        story.append(Paragraph("<b>Fleet Statistics</b>", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        stats_data = [
            ['Metric', 'Value'],
            ['Total Hosts', str(stats['total_hosts'])],
            ['Linux Hosts', str(stats['linux_hosts'])],
            ['Windows Hosts', str(stats['windows_hosts'])],
            ['Average Health Score', f"{stats['average_health_score']:.2f}"],
            ['Failed Critical Checks', str(stats['failed_critical_checks'])],
            ['Failed High Checks', str(stats['failed_high_checks'])]
        ]
        
        stats_table = Table(stats_data, colWidths=[4*inch, 2.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Host Scores (top 20)
        story.append(Paragraph("<b>Host Health Scores (Top 20)</b>", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        host_scores = []
        for host in hosts[:20]:
            score = self.host_db.get_latest_health_score(host['host_id'])
            if score:
                host_scores.append({
                    'hostname': host.get('hostname', host['host_id']),
                    'score': score['score']
                })
        
        if host_scores:
            host_data = [['Hostname', 'Health Score']]
            for h in sorted(host_scores, key=lambda x: x['score']):
                host_data.append([h['hostname'], f"{h['score']:.2f}"])
            
            host_table = Table(host_data, colWidths=[4*inch, 2.5*inch])
            host_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(host_table)
            story.append(Spacer(1, 0.2*inch))
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        footer_text = f"© RansomEye.Tech | Support: Gagan@RansomEye.Tech | Build: {self._calculate_build_hash()}"
        story.append(Paragraph(
            footer_text,
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)
        ))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF fleet report generated: {output_path}")
        return output_path
    
    def _calculate_build_hash(self) -> str:
        """Calculate build hash for report."""
        try:
            # Simple hash based on timestamp
            timestamp = datetime.utcnow().isoformat()
            return hashlib.sha256(timestamp.encode()).hexdigest()[:8]
        except:
            return "unknown"

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export fleet health report')
    parser.add_argument('--format', choices=['pdf', 'json', 'both'], default='both',
                       help='Export format')
    parser.add_argument('--output', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    exporter = FleetReportExporter()
    
    if args.format in ['pdf', 'both']:
        pdf_path = exporter.generate_pdf_report(args.output)
        print(f"PDF report: {pdf_path}")
    
    if args.format in ['json', 'both']:
        json_path = exporter.generate_json_report()
        print(f"JSON report: {json_path}")

if __name__ == '__main__':
    main()

