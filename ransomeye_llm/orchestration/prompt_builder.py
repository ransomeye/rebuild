# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/orchestration/prompt_builder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Builds prompts from context using Jinja2 templates

import os
import sys
from pathlib import Path
from typing import Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    logging.warning("Jinja2 not available, using simple string formatting")

from ..orchestration.prompt_templates import get_template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptBuilder:
    """
    Builds prompts from context using Jinja2 templates.
    """
    
    def __init__(self):
        """Initialize prompt builder."""
        self.templates_dir = Path(__file__).parent / "prompt_templates"
        
        if JINJA2_AVAILABLE:
            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=False
            )
        else:
            self.env = None
    
    def build_prompt(self, context: Dict[str, Any], audience: str = "executive") -> str:
        """
        Build prompt from context for specified audience.
        
        Args:
            context: Context dictionary with incident data
            audience: Target audience (executive, manager, analyst)
            
        Returns:
            Formatted prompt string
        """
        try:
            if JINJA2_AVAILABLE and self.env:
                # Try to load template
                template_name = f"{audience}.j2"
                try:
                    template = self.env.get_template(template_name)
                    return template.render(**context)
                except TemplateNotFound:
                    logger.warning(f"Template {template_name} not found, using fallback")
                    return self._build_fallback_prompt(context, audience)
            else:
                # Fallback to simple formatting
                return self._build_fallback_prompt(context, audience)
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            return self._build_fallback_prompt(context, audience)
    
    def _build_fallback_prompt(self, context: Dict[str, Any], audience: str) -> str:
        """
        Build prompt using fallback method (no Jinja2).
        
        Args:
            context: Context dictionary
            audience: Target audience
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # Add header
        prompt_parts.append(f"Generate a {audience} summary for the following incident:")
        prompt_parts.append("")
        
        # Add incident ID
        if 'incident_id' in context:
            prompt_parts.append(f"Incident ID: {context['incident_id']}")
        
        # Add alerts
        if 'alerts' in context:
            alert_count = len(context['alerts'])
            prompt_parts.append(f"Total Alerts: {alert_count}")
            if alert_count > 0:
                prompt_parts.append("\nKey Alerts:")
                for alert in context['alerts'][:5]:  # First 5 alerts
                    alert_type = alert.get('alert_type', 'Unknown')
                    severity = alert.get('severity', 'medium')
                    prompt_parts.append(f"  - {alert_type} (Severity: {severity})")
        
        # Add timeline
        if 'timeline' in context:
            timeline = context['timeline']
            if 'events' in timeline:
                event_count = len(timeline['events'])
                prompt_parts.append(f"\nTimeline Events: {event_count}")
                if 'start_time' in timeline:
                    prompt_parts.append(f"Start Time: {timeline['start_time']}")
                if 'end_time' in timeline:
                    prompt_parts.append(f"End Time: {timeline['end_time']}")
        
        # Add SHAP values
        if 'shap_text' in context:
            prompt_parts.append("\nAI Analysis:")
            prompt_parts.append(context['shap_text'])
        
        # Add IOCs
        if 'iocs' in context:
            iocs = context['iocs']
            prompt_parts.append("\nIndicators of Compromise:")
            for ioc_type, ioc_values in iocs.items():
                if ioc_values:
                    prompt_parts.append(f"  {ioc_type}: {', '.join(ioc_values[:5])}")
        
        # Add instruction based on audience
        prompt_parts.append("")
        if audience == "executive":
            prompt_parts.append("Generate a brief executive summary focusing on business impact and recommended actions.")
        elif audience == "manager":
            prompt_parts.append("Generate a manager-level summary with timeline, key events, and operational impact.")
        elif audience == "analyst":
            prompt_parts.append("Generate a technical analyst summary with detailed IOCs, SHAP analysis, and technical recommendations.")
        
        return "\n".join(prompt_parts)

