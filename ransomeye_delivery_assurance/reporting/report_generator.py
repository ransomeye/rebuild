# Path and File Name : /home/ransomeye/rebuild/ransomeye_delivery_assurance/reporting/report_generator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Aggregates audit results and generates final_handover_report.pdf using reportlab

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class ReportGenerator:
    """Generates PDF handover reports from audit results."""
    
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Helper function to add or update a style
        def add_or_update_style(style_name, parent_name, **kwargs):
            """Add style if it doesn't exist, or update it if it does."""
            if style_name in self.styles.byName:
                # Style exists, update its attributes
                existing_style = self.styles[style_name]
                for key, value in kwargs.items():
                    setattr(existing_style, key, value)
            else:
                # Style doesn't exist, add it
                parent = self.styles[parent_name] if parent_name else None
                new_style = ParagraphStyle(
                    name=style_name,
                    parent=parent,
                    **kwargs
                )
                self.styles.add(new_style)
        
        # Title style (may already exist in sample stylesheet)
        add_or_update_style(
            'Title',
            'Heading1',
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Heading2 style (may already exist in sample stylesheet)
        add_or_update_style(
            'Heading2',
            'Heading2',
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Body style (custom, likely doesn't exist)
        add_or_update_style(
            'Body',
            'BodyText',
            fontSize=10,
            spaceAfter=6
        )
        
        # Footer style (custom, likely doesn't exist)
        add_or_update_style(
            'Footer',
            'Normal',
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
    
    def generate_report(self, audit_results: Dict) -> str:
        """Generate PDF report from audit results."""
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Title page
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph("RansomEye Delivery Assurance", self.styles['Title']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Final Handover Report", self.styles['Heading2']))
        story.append(Spacer(1, 0.5*inch))
        
        # Metadata
        metadata = [
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')],
            ['Project Root:', audit_results.get('project_root', 'N/A')],
            ['Audit Version:', audit_results.get('audit_version', '1.0.0')],
        ]
        
        metadata_table = Table(metadata, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(metadata_table)
        story.append(PageBreak())
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles['Heading2']))
        
        summary_data = audit_results.get('summary', {})
        total_checks = summary_data.get('total_checks', 0)
        passed_checks = summary_data.get('passed_checks', 0)
        failed_checks = summary_data.get('failed_checks', 0)
        warning_count = summary_data.get('warning_count', 0)
        
        pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        summary_text = f"""
        This report presents the results of the comprehensive delivery assurance audit
        for the RansomEye platform. The audit verifies architectural compliance, code
        quality, security hygiene, and deliverable completeness.
        
        <b>Overall Status:</b> {'PASSED' if failed_checks == 0 else 'FAILED'}
        <b>Total Checks:</b> {total_checks}
        <b>Passed:</b> {passed_checks}
        <b>Failed:</b> {failed_checks}
        <b>Warnings:</b> {warning_count}
        <b>Pass Rate:</b> {pass_rate:.1f}%
        """
        
        story.append(Paragraph(summary_text, self.styles['Body']))
        story.append(Spacer(1, 0.2*inch))
        
        # Summary Table
        summary_table_data = [
            ['Audit Category', 'Status', 'Passed', 'Failed', 'Warnings'],
        ]
        
        for category, results in audit_results.get('categories', {}).items():
            status = 'PASS' if results.get('error_count', 0) == 0 else 'FAIL'
            status_color = colors.green if status == 'PASS' else colors.red
            summary_table_data.append([
                category,
                status,
                str(results.get('passed_count', 0)),
                str(results.get('error_count', 0)),
                str(results.get('warning_count', 0))
            ])
        
        summary_table = Table(summary_table_data, colWidths=[2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(summary_table)
        story.append(PageBreak())
        
        # Detailed Results by Category
        for category, results in audit_results.get('categories', {}).items():
            story.append(Paragraph(f"{category} Details", self.styles['Heading2']))
            
            # Errors
            if results.get('errors'):
                story.append(Paragraph("<b>Errors:</b>", self.styles['Body']))
                for error in results['errors'][:50]:  # Limit to first 50
                    story.append(Paragraph(f"• {error}", self.styles['Body']))
                if len(results['errors']) > 50:
                    story.append(Paragraph(
                        f"... and {len(results['errors']) - 50} more errors",
                        self.styles['Body']
                    ))
                story.append(Spacer(1, 0.1*inch))
            
            # Warnings
            if results.get('warnings'):
                story.append(Paragraph("<b>Warnings:</b>", self.styles['Body']))
                for warning in results['warnings'][:20]:  # Limit to first 20
                    story.append(Paragraph(f"• {warning}", self.styles['Body']))
                if len(results['warnings']) > 20:
                    story.append(Paragraph(
                        f"... and {len(results['warnings']) - 20} more warnings",
                        self.styles['Body']
                    ))
                story.append(Spacer(1, 0.1*inch))
            
            # Passed (summary only)
            if results.get('passed'):
                passed_count = len(results['passed'])
                story.append(Paragraph(
                    f"<b>Passed Checks:</b> {passed_count}",
                    self.styles['Body']
                ))
            
            story.append(PageBreak())
        
        # Footer
        footer_text = "© RansomEye.Tech | Support: Gagan@RansomEye.Tech"
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(footer_text, self.styles['Footer']))
        
        # Build PDF
        doc.build(story)
        
        return str(self.output_path)


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 3:
        print("Usage: report_generator.py <audit_results.json> <output.pdf>")
        sys.exit(1)
    
    results_path = sys.argv[1]
    output_path = sys.argv[2]
    
    with open(results_path, 'r') as f:
        audit_results = json.load(f)
    
    generator = ReportGenerator(output_path)
    pdf_path = generator.generate_report(audit_results)
    print(f"Report generated: {pdf_path}")

