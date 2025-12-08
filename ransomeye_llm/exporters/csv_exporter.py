# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/exporters/csv_exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Flattens data for CSV export

import os
import csv
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CSVExporter:
    """
    Exports reports to CSV format.
    """
    
    def __init__(self):
        """Initialize CSV exporter."""
        pass
    
    def export(self, report_data: Dict[str, Any], output_path: str = None) -> Path:
        """
        Export report to CSV.
        
        Args:
            report_data: Report data dictionary
            output_path: Optional output path
            
        Returns:
            Path to generated CSV file
        """
        if output_path is None:
            job_id = report_data.get('job_id', 'report')
            output_dir = Path(os.environ.get('REPORT_STORAGE_DIR', '/home/ransomeye/rebuild/ransomeye_llm/storage/reports'))
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{job_id}.csv"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Flatten data
        rows = self._flatten_data(report_data)
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        logger.info(f"CSV report generated: {output_path}")
        return output_path
    
    def _flatten_data(self, report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Flatten report data into CSV rows.
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            List of dictionaries for CSV rows
        """
        rows = []
        
        # Main report row
        main_row = {
            'incident_id': report_data.get('incident_id', ''),
            'generated_at': report_data.get('generated_at', ''),
            'audience': report_data.get('audience', ''),
            'summary': report_data.get('summary', '').replace('\n', ' ').replace('\r', '')
        }
        rows.append(main_row)
        
        # IOCs rows
        context = report_data.get('context', {})
        iocs = context.get('iocs', {})
        
        for ioc_type, ioc_values in iocs.items():
            for ioc_value in ioc_values:
                rows.append({
                    'type': 'ioc',
                    'ioc_type': ioc_type,
                    'ioc_value': ioc_value,
                    'incident_id': report_data.get('incident_id', '')
                })
        
        # SHAP values rows
        shap_values = context.get('shap_values', {})
        for feature, value in shap_values.items():
            rows.append({
                'type': 'shap',
                'feature': feature,
                'value': value,
                'importance': abs(value) * 100,
                'incident_id': report_data.get('incident_id', '')
            })
        
        # Alerts rows
        alerts = context.get('alerts', [])
        for alert in alerts:
            rows.append({
                'type': 'alert',
                'alert_id': alert.get('alert_id', ''),
                'alert_type': alert.get('alert_type', ''),
                'source': alert.get('source', ''),
                'target': alert.get('target', ''),
                'severity': alert.get('severity', ''),
                'timestamp': alert.get('timestamp', ''),
                'incident_id': report_data.get('incident_id', '')
            })
        
        return rows

