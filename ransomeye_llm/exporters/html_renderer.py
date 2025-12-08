# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/exporters/html_renderer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates clean HTML report string

import logging
from typing import Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HTMLRenderer:
    """
    Renders reports as HTML.
    """
    
    def __init__(self):
        """Initialize HTML renderer."""
        pass
    
    def render(self, report_data: Dict[str, Any]) -> str:
        """
        Render report as HTML.
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            HTML string
        """
        incident_id = report_data.get('incident_id', 'Unknown')
        summary = report_data.get('summary', 'No summary available.')
        generated_at = report_data.get('generated_at', datetime.utcnow().isoformat())
        context = report_data.get('context', {})
        
        html_parts = []
        
        # HTML header
        html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Incident Report - """ + incident_id + """</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .metadata {
            background-color: #f9f9f9;
            padding: 15px;
            border-left: 4px solid #4CAF50;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .summary {
            background-color: #e8f5e9;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .ioc-section {
            margin: 20px 0;
        }
        .shap-section {
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">""")
        
        # Title
        html_parts.append(f"<h1>Incident Report</h1>")
        
        # Metadata
        html_parts.append("""<div class="metadata">
            <p><strong>Incident ID:</strong> """ + incident_id + """</p>
            <p><strong>Generated:</strong> """ + generated_at + """</p>
        </div>""")
        
        # Summary
        html_parts.append("""<div class="summary">
            <h2>Summary</h2>""")
        
        # Format summary (preserve paragraphs)
        summary_html = summary.replace('\n\n', '</p><p>').replace('\n', '<br>')
        html_parts.append(f"<p>{summary_html}</p>")
        html_parts.append("</div>")
        
        # IOCs
        iocs = context.get('iocs', {})
        if iocs:
            html_parts.append("""<div class="ioc-section">
            <h2>Indicators of Compromise</h2>
            <table>
                <tr>
                    <th>Type</th>
                    <th>Values</th>
                </tr>""")
            
            for ioc_type, ioc_values in iocs.items():
                if ioc_values:
                    values_str = ', '.join(str(v) for v in ioc_values[:20])
                    if len(ioc_values) > 20:
                        values_str += f" ... ({len(ioc_values)} total)"
                    html_parts.append(f"""
                <tr>
                    <td><strong>{ioc_type.upper()}</strong></td>
                    <td>{values_str}</td>
                </tr>""")
            
            html_parts.append("""            </table>
        </div>""")
        
        # SHAP Values
        shap_values = context.get('shap_values', {})
        if shap_values:
            html_parts.append("""<div class="shap-section">
            <h2>AI Feature Importance (SHAP Values)</h2>
            <table>
                <tr>
                    <th>Feature</th>
                    <th>Importance %</th>
                </tr>""")
            
            # Sort by importance
            sorted_shap = sorted(
                shap_values.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:10]
            
            for feature, value in sorted_shap:
                importance = abs(value) * 100
                html_parts.append(f"""
                <tr>
                    <td>{feature}</td>
                    <td>{importance:.2f}%</td>
                </tr>""")
            
            html_parts.append("""            </table>
        </div>""")
        
        # Footer
        html_parts.append("""    </div>
</body>
</html>""")
        
        html_content = '\n'.join(html_parts)
        logger.info("HTML report generated")
        return html_content

