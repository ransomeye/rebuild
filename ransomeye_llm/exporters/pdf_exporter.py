# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/exporters/pdf_exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates professional PDF reports using reportlab

import os
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("ReportLab not available, PDF export will not work")

from ..loaders.shap_injector import SHAPInjector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFExporter:
    """
    Exports reports to PDF format using ReportLab.
    """
    
    def __init__(self):
        """Initialize PDF exporter."""
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not available, PDF export disabled")
        self.shap_injector = SHAPInjector()
    
    def export(self, report_data: Dict[str, Any], output_path: str = None) -> Path:
        """
        Export report to PDF.
        
        Args:
            report_data: Report data dictionary
            output_path: Optional output path
            
        Returns:
            Path to generated PDF file
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab not available, cannot generate PDF")
        
        if output_path is None:
            job_id = report_data.get('job_id', 'report')
            output_dir = Path(os.environ.get('REPORT_STORAGE_DIR', '/home/ransomeye/rebuild/ransomeye_llm/storage/reports'))
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{job_id}.pdf"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build story (content)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph("Incident Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Incident ID
        incident_id = report_data.get('incident_id', 'Unknown')
        story.append(Paragraph(f"<b>Incident ID:</b> {incident_id}", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        # Generated date
        generated_at = report_data.get('generated_at', datetime.utcnow().isoformat())
        story.append(Paragraph(f"<b>Generated:</b> {generated_at}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Summary
        summary = report_data.get('summary', 'No summary available.')
        story.append(Paragraph("<b>Summary</b>", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        # Split summary into paragraphs
        for para in summary.split('\n\n'):
            if para.strip():
                story.append(Paragraph(para.strip(), styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
        
        story.append(PageBreak())
        
        # IOCs Table
        context = report_data.get('context', {})
        iocs = context.get('iocs', {})
        
        if iocs:
            story.append(Paragraph("<b>Indicators of Compromise</b>", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            # Build IOC table
            ioc_data = [['Type', 'Values']]
            for ioc_type, ioc_values in iocs.items():
                if ioc_values:
                    values_str = ', '.join(str(v) for v in ioc_values[:10])  # Limit to 10
                    if len(ioc_values) > 10:
                        values_str += f" ... ({len(ioc_values)} total)"
                    ioc_data.append([ioc_type.upper(), values_str])
            
            if len(ioc_data) > 1:
                ioc_table = Table(ioc_data, colWidths=[2*inch, 4.5*inch])
                ioc_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(ioc_table)
                story.append(Spacer(1, 0.2*inch))
        
        # SHAP Values Table
        shap_values = context.get('shap_values', {})
        if shap_values:
            story.append(Paragraph("<b>AI Feature Importance (SHAP Values)</b>", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            shap_rows = self.shap_injector.format_shap_for_table(shap_values, limit=10)
            if shap_rows:
                shap_data = [['Feature', 'Importance %']]
                for row in shap_rows:
                    shap_data.append([
                        row['feature'],
                        f"{row['importance']:.2f}%"
                    ])
                
                shap_table = Table(shap_data, colWidths=[4*inch, 2.5*inch])
                shap_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(shap_table)
                story.append(Spacer(1, 0.2*inch))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF report generated: {output_path}")
        return output_path

