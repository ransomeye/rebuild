# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/orchestration/summary_orchestrator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Controller that orchestrates summary generation pipeline

import os
import sys
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..llm_runner.llm_infer import LLMInferenceEngine
from ..llm_runner.safety_filters import SafetyFilters
from ..loaders.context_loader import ContextLoader
from ..loaders.shap_injector import SHAPInjector
from ..orchestration.prompt_builder import PromptBuilder
from ..exporters.pdf_exporter import PDFExporter
from ..exporters.html_renderer import HTMLRenderer
from ..exporters.csv_exporter import CSVExporter
from ..signer.sign_report import ReportSigner
from ..storage.summary_store import SummaryStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummaryOrchestrator:
    """
    Orchestrates the complete summary generation pipeline.
    """
    
    def __init__(self):
        """Initialize orchestrator with all components."""
        self.llm_engine = LLMInferenceEngine()
        self.safety_filters = SafetyFilters()
        self.context_loader = ContextLoader()
        self.shap_injector = SHAPInjector()
        self.prompt_builder = PromptBuilder()
        self.pdf_exporter = PDFExporter()
        self.html_renderer = HTMLRenderer()
        self.csv_exporter = CSVExporter()
        self.report_signer = ReportSigner()
        self.summary_store = SummaryStore()
        
        # Job status tracking
        self.jobs: Dict[str, Dict[str, Any]] = {}
    
    async def generate_summary(self, incident_id: str, audience: str = "executive") -> str:
        """
        Generate summary for an incident.
        
        Args:
            incident_id: Incident identifier
            audience: Target audience (executive, manager, analyst)
            
        Returns:
            Job ID for tracking
        """
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        self.jobs[job_id] = {
            'job_id': job_id,
            'incident_id': incident_id,
            'audience': audience,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'progress': 0
        }
        
        # Run generation in background
        asyncio.create_task(self._generate_summary_async(job_id, incident_id, audience))
        
        return job_id
    
    async def _generate_summary_async(self, job_id: str, incident_id: str, audience: str):
        """
        Async summary generation task.
        
        Args:
            job_id: Job identifier
            incident_id: Incident identifier
            audience: Target audience
        """
        try:
            self.jobs[job_id]['status'] = 'loading_context'
            self.jobs[job_id]['progress'] = 10
            
            # Step 1: Load context
            logger.info(f"Loading context for incident {incident_id}")
            context = await self.context_loader.load_context(incident_id)
            
            self.jobs[job_id]['status'] = 'processing_shap'
            self.jobs[job_id]['progress'] = 30
            
            # Step 2: Inject SHAP values
            if 'shap_values' in context:
                context['shap_text'] = self.shap_injector.format_shap(context['shap_values'])
            
            self.jobs[job_id]['status'] = 'building_prompt'
            self.jobs[job_id]['progress'] = 40
            
            # Step 3: Build prompt
            prompt = self.prompt_builder.build_prompt(context, audience)
            
            self.jobs[job_id]['status'] = 'generating_summary'
            self.jobs[job_id]['progress'] = 60
            
            # Step 4: Generate summary with LLM
            llm_result = self.llm_engine.generate_summary(context, audience)
            raw_summary = llm_result['text']
            
            # Step 5: Sanitize output
            sanitized_summary = self.safety_filters.sanitize_output(raw_summary)
            
            self.jobs[job_id]['status'] = 'exporting_reports'
            self.jobs[job_id]['progress'] = 80
            
            # Step 6: Export reports
            report_data = {
                'incident_id': incident_id,
                'audience': audience,
                'summary': sanitized_summary,
                'context': context,
                'llm_metadata': llm_result,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Generate PDF
            pdf_path = self.pdf_exporter.export(report_data)
            
            # Generate HTML
            html_content = self.html_renderer.render(report_data)
            html_path = self.summary_store.save_html(job_id, html_content)
            
            # Generate CSV
            csv_path = self.csv_exporter.export(report_data)
            
            self.jobs[job_id]['status'] = 'signing_report'
            self.jobs[job_id]['progress'] = 90
            
            # Step 7: Sign report
            manifest_path, signature_path = self.report_signer.sign_report(
                pdf_path, job_id
            )
            
            # Step 8: Store all files
            stored_paths = self.summary_store.store_report(
                job_id=job_id,
                pdf_path=pdf_path,
                html_path=html_path,
                csv_path=csv_path,
                manifest_path=manifest_path,
                signature_path=signature_path,
                metadata=report_data
            )
            
            self.jobs[job_id]['status'] = 'completed'
            self.jobs[job_id]['progress'] = 100
            self.jobs[job_id]['report_paths'] = stored_paths
            self.jobs[job_id]['completed_at'] = datetime.utcnow().isoformat()
            
            logger.info(f"Summary generation completed for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error generating summary for job {job_id}: {e}", exc_info=True)
            self.jobs[job_id]['status'] = 'failed'
            self.jobs[job_id]['error'] = str(e)
            self.jobs[job_id]['failed_at'] = datetime.utcnow().isoformat()
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status dictionary or None
        """
        return self.jobs.get(job_id)
    
    def list_jobs(self, limit: int = 100) -> list:
        """
        List all jobs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        jobs_list = list(self.jobs.values())
        jobs_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return jobs_list[:limit]

