# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm/tools/test_local_generation.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to run generation on dummy input without starting server

import argparse
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_llm.orchestration.summary_orchestrator import SummaryOrchestrator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_dummy_context():
    """Create dummy context for testing."""
    return {
        'incident_id': 'test-incident-001',
        'alerts': [
            {
                'alert_id': 'alert-001',
                'alert_type': 'Brute Force',
                'source': '192.168.1.100',
                'target': '192.168.1.50',
                'severity': 'high',
                'timestamp': '2024-01-15T10:30:00Z',
                'metadata': {},
                'matches': []
            },
            {
                'alert_id': 'alert-002',
                'alert_type': 'Suspicious Activity',
                'source': '192.168.1.100',
                'target': '192.168.1.50',
                'severity': 'medium',
                'timestamp': '2024-01-15T10:35:00Z',
                'metadata': {},
                'matches': []
            }
        ],
        'timeline': {
            'incident_id': 'test-incident-001',
            'events': [
                {
                    'timestamp': '2024-01-15T10:30:00Z',
                    'alert_type': 'Brute Force',
                    'source': '192.168.1.100',
                    'target': '192.168.1.50',
                    'severity': 'high'
                }
            ],
            'start_time': '2024-01-15T10:30:00Z',
            'end_time': '2024-01-15T10:35:00Z'
        },
        'iocs': {
            'ips': ['192.168.1.100', '192.168.1.50'],
            'domains': [],
            'hashes': [],
            'files': []
        },
        'shap_values': {
            'packet_size': 0.85,
            'src_port': 0.72,
            'duration': 0.65,
            'bytes_sent': 0.58
        }
    }

async def test_generation(audience: str = "executive"):
    """
    Test summary generation with dummy data.
    
    Args:
        audience: Target audience (executive, manager, analyst)
    """
    logger.info(f"Testing summary generation for audience: {audience}")
    
    # Create orchestrator
    orchestrator = SummaryOrchestrator()
    
    # Create dummy context
    context = create_dummy_context()
    
    # Manually test components
    logger.info("Testing SHAP injector...")
    from ransomeye_llm.loaders.shap_injector import SHAPInjector
    shap_injector = SHAPInjector()
    shap_text = shap_injector.format_shap(context['shap_values'])
    logger.info(f"SHAP text: {shap_text[:200]}...")
    
    logger.info("Testing prompt builder...")
    from ransomeye_llm.orchestration.prompt_builder import PromptBuilder
    prompt_builder = PromptBuilder()
    prompt = prompt_builder.build_prompt(context, audience)
    logger.info(f"Prompt: {prompt[:200]}...")
    
    logger.info("Testing LLM generation...")
    from ransomeye_llm.llm_runner.llm_infer import LLMInferenceEngine
    llm_engine = LLMInferenceEngine()
    result = llm_engine.generate_summary(context, audience)
    logger.info(f"Generated summary: {result['text'][:500]}...")
    logger.info(f"Model used: {result.get('model_used', False)}")
    logger.info(f"Fallback: {result.get('fallback', False)}")
    
    logger.info("✓ Test generation completed successfully")

def main():
    parser = argparse.ArgumentParser(description='Test local LLM generation')
    parser.add_argument('--audience', type=str, default='executive',
                       choices=['executive', 'manager', 'analyst'],
                       help='Target audience for summary')
    
    args = parser.parse_args()
    
    try:
        asyncio.run(test_generation(args.audience))
        return 0
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())

