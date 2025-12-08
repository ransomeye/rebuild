# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/cli/export_feedback.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI to trigger feedback bundle export

import argparse
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_assistant.feedback.feedback_collector import FeedbackCollector
from ransomeye_assistant.feedback.bundle_exporter import BundleExporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def export_feedback(output_path: Path, limit: int = 1000):
    """
    Export feedback data as signed bundle.
    
    Args:
        output_path: Output bundle path
        limit: Maximum number of feedback records to export
    """
    # Initialize components
    feedback_collector = FeedbackCollector()
    bundle_exporter = BundleExporter()
    
    # Get feedback data
    logger.info(f"Collecting feedback data (limit: {limit})...")
    feedback_data = feedback_collector.get_feedback_data(limit=limit)
    
    if not feedback_data:
        logger.warning("No feedback data to export")
        return
    
    # Export bundle
    logger.info(f"Exporting {len(feedback_data)} feedback records...")
    bundle_path = bundle_exporter.export_bundle(feedback_data, output_path)
    
    logger.info(f"Feedback bundle exported: {bundle_path}")
    logger.info(f"Bundle contains {len(feedback_data)} feedback records")

def main():
    parser = argparse.ArgumentParser(description='Export feedback as signed training bundle')
    parser.add_argument('--output', type=str, required=True,
                       help='Output bundle path (.tar.gz)')
    parser.add_argument('--limit', type=int, default=1000,
                       help='Maximum number of feedback records to export')
    
    args = parser.parse_args()
    
    try:
        export_feedback(Path(args.output), limit=args.limit)
        return 0
    except Exception as e:
        logger.error(f"Error exporting feedback: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())

