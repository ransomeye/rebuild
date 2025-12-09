# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/validator/pdf_signer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates PDF reports using ReportLab and cryptographically signs them using RSA

import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus.flowables import Image
from reportlab.pdfgen import canvas
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFSigner:
    """Generates and signs PDF validation reports."""
    
    def __init__(self):
        """Initialize PDF signer with signing key path."""
        self.sign_key_path = os.environ.get(
            'VALIDATOR_SIGN_KEY_PATH',
            '/home/ransomeye/rebuild/ransomeye_global_validator/keys/sign_key.pem'
        )
        self.private_key = None
        self._load_private_key()
        logger.info("PDF signer initialized")
    
    def _load_private_key(self):
        """Load RSA private key for signing."""
        try:
            key_path = Path(self.sign_key_path)
            if key_path.exists():
                with open(key_path, 'rb') as f:
                    self.private_key = RSA.import_key(f.read())
                logger.info(f"Private key loaded from {self.sign_key_path}")
            else:
                logger.warning(f"Signing key not found at {self.sign_key_path}, PDFs will not be signed")
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
    
    def generate_pdf(self, run_data: Dict[str, Any], output_path: str) -> str:
        """
        Generate PDF validation report.
        
        Args:
            run_data: Validation run data
            output_path: Output file path
            
        Returns:
            Path to generated PDF
        """
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("RansomEye Global Validator Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Run metadata
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666')
        )
        
        run_id = run_data.get('run_id', 'unknown')
        timestamp = run_data.get('start_time', datetime.utcnow().isoformat())
        story.append(Paragraph(f"<b>Run ID:</b> {run_id}", metadata_style))
        story.append(Paragraph(f"<b>Timestamp:</b> {timestamp}", metadata_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Summary section
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12
        )
        story.append(Paragraph("Validation Summary", summary_style))
        
        summary_data = run_data.get('summary', {})
        total_scenarios = summary_data.get('total_scenarios', 0)
        passed_scenarios = summary_data.get('passed_scenarios', 0)
        failed_scenarios = summary_data.get('failed_scenarios', 0)
        overall_status = "PASSED" if failed_scenarios == 0 else "FAILED"
        
        summary_table_data = [
            ['Metric', 'Value'],
            ['Overall Status', overall_status],
            ['Total Scenarios', str(total_scenarios)],
            ['Passed', str(passed_scenarios)],
            ['Failed', str(failed_scenarios)],
            ['Success Rate', f"{(passed_scenarios/total_scenarios*100) if total_scenarios > 0 else 0:.1f}%"]
        ]
        
        summary_table = Table(summary_table_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Scenario details
        story.append(Paragraph("Scenario Details", summary_style))
        
        scenarios = run_data.get('scenarios', [])
        for scenario in scenarios:
            scenario_name = scenario.get('name', 'Unknown')
            scenario_status = scenario.get('status', 'UNKNOWN')
            status_color = colors.green if scenario_status == 'PASSED' else colors.red
            
            story.append(Paragraph(f"<b>{scenario_name}</b> - {scenario_status}", 
                                 ParagraphStyle('ScenarioTitle', parent=styles['Normal'], 
                                               fontSize=12, textColor=status_color)))
            
            steps = scenario.get('steps', [])
            if steps:
                step_data = [['Step', 'Status', 'Latency (ms)', 'Details']]
                for step in steps:
                    step_name = step.get('name', 'Unknown')
                    step_status = step.get('status', 'UNKNOWN')
                    latency = step.get('latency_ms', 0)
                    details = step.get('details', '')
                    
                    step_data.append([
                        step_name,
                        step_status,
                        f"{latency:.2f}" if latency else "N/A",
                        details[:50] + "..." if len(details) > 50 else details
                    ])
                
                step_table = Table(step_data, colWidths=[2*inch, 1*inch, 1*inch, 2*inch])
                step_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                ]))
                story.append(step_table)
                story.append(Spacer(1, 0.2*inch))
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#999999'),
            alignment=1
        )
        story.append(Paragraph("© RansomEye.Tech | Support: Gagan@RansomEye.Tech", footer_style))
        story.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()}", footer_style))
        
        # Build PDF
        doc.build(story)
        
        # Sign PDF if key is available
        if self.private_key:
            self._sign_pdf(output_path)
        
        logger.info(f"PDF report generated: {output_path}")
        return output_path
    
    def _sign_pdf(self, pdf_path: str):
        """
        Cryptographically sign PDF file.
        
        Args:
            pdf_path: Path to PDF file
        """
        try:
            # Read PDF content
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            # Create hash
            pdf_hash = SHA256.new(pdf_content)
            
            # Sign hash
            signature = pkcs1_15.new(self.private_key).sign(pdf_hash)
            
            # Save signature to separate file
            sig_path = pdf_path + '.sig'
            with open(sig_path, 'wb') as f:
                f.write(signature)
            
            # Save signature metadata
            sig_meta_path = pdf_path + '.sig.meta'
            with open(sig_meta_path, 'w') as f:
                f.write(f"PDF_HASH_SHA256={pdf_hash.hexdigest()}\n")
                f.write(f"SIGNATURE_LENGTH={len(signature)}\n")
                f.write(f"SIGNED_AT={datetime.utcnow().isoformat()}\n")
            
            logger.info(f"PDF signed: {pdf_path} (signature: {sig_path})")
        
        except Exception as e:
            logger.error(f"Failed to sign PDF: {e}")

