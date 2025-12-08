# Path and File Name : /home/ransomeye/rebuild/ransomeye_install/install_validator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Post-installation validation script that checks service health and generates PDF report

import argparse
import socket
import time
import sys
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def check_port_open(host, port, timeout=30):
    """Check if a port is open and accepting connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def check_http_response(host, port, path="/health", timeout=5):
    """Check if HTTP endpoint responds."""
    try:
        import urllib.request
        url = f"http://{host}:{port}{path}"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'RansomEye-Validator/1.0')
        response = urllib.request.urlopen(req, timeout=timeout)
        return response.getcode() == 200
    except Exception:
        return False

def generate_pdf_report(output_path, port, checks_passed):
    """Generate PDF installation report."""
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12
    )
    
    # Title
    story.append(Paragraph("RansomEye Core Engine", title_style))
    story.append(Paragraph("Installation Validation Report", styles['Heading2']))
    story.append(Spacer(1, 0.3*inch))
    
    # Report metadata
    report_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    story.append(Paragraph(f"<b>Report Generated:</b> {report_time}", styles['Normal']))
    story.append(Paragraph(f"<b>Core API Port:</b> {port}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Validation results
    story.append(Paragraph("Validation Results", heading_style))
    
    results_data = [
        ['Check', 'Status', 'Details'],
        ['Service Port Availability', 'PASS' if checks_passed['port_open'] else 'FAIL', 
         f'Port {port} is {"accessible" if checks_passed["port_open"] else "not accessible"}'],
        ['HTTP Health Endpoint', 'PASS' if checks_passed['http_ok'] else 'FAIL',
         'Health endpoint responded' if checks_passed['http_ok'] else 'Health endpoint did not respond'],
        ['Service Startup', 'PASS' if checks_passed['port_open'] else 'FAIL',
         'Service started successfully' if checks_passed['port_open'] else 'Service failed to start'],
    ]
    
    table = Table(results_data, colWidths=[3*inch, 1.5*inch, 3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    # Overall status
    overall_status = "SUCCESS" if all(checks_passed.values()) else "FAILED"
    status_color = colors.green if overall_status == "SUCCESS" else colors.red
    story.append(Paragraph(f"<b>Overall Installation Status:</b> <font color='{status_color.hex()}'> {overall_status}</font>", 
                           styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("© RansomEye.Tech | Support: Gagan@RansomEye.Tech", 
                           ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)))
    
    # Build PDF
    doc.build(story)
    return True

def main():
    parser = argparse.ArgumentParser(description='Validate RansomEye Core installation')
    parser.add_argument('--port', type=int, default=8080, help='Core API port to check')
    parser.add_argument('--host', type=str, default='localhost', help='Host to check')
    parser.add_argument('--output', type=str, required=True, help='Output PDF file path')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout in seconds for service startup')
    
    args = parser.parse_args()
    
    print(f"Validating RansomEye Core installation on {args.host}:{args.port}...")
    print(f"Timeout: {args.timeout} seconds")
    print("")
    
    checks_passed = {
        'port_open': False,
        'http_ok': False
    }
    
    # Check if port is open
    print(f"[1/2] Checking if port {args.port} is accessible...")
    checks_passed['port_open'] = check_port_open(args.host, args.port, timeout=args.timeout)
    if checks_passed['port_open']:
        print(f"✓ Port {args.port} is accessible")
    else:
        print(f"✗ Port {args.port} is not accessible after {args.timeout} seconds")
    
    # Check HTTP health endpoint
    if checks_passed['port_open']:
        print(f"[2/2] Checking HTTP health endpoint...")
        checks_passed['http_ok'] = check_http_response(args.host, args.port, path="/health", timeout=5)
        if checks_passed['http_ok']:
            print("✓ Health endpoint responded")
        else:
            print("⚠ Health endpoint did not respond (service may be starting)")
    
    # Generate PDF report
    print("")
    print(f"Generating PDF report: {args.output}")
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    try:
        generate_pdf_report(args.output, args.port, checks_passed)
        print("✓ PDF report generated successfully")
    except Exception as e:
        print(f"✗ Failed to generate PDF report: {e}")
        sys.exit(1)
    
    # Exit with appropriate code
    if all(checks_passed.values()):
        print("")
        print("Installation validation: SUCCESS")
        sys.exit(0)
    else:
        print("")
        print("Installation validation: FAILED (see report for details)")
        sys.exit(1)

if __name__ == "__main__":
    main()

