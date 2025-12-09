# Path and File Name : /home/ransomeye/rebuild/ransomeye_dpi_probe/main.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Main entry point that orchestrates capture daemon, uploader, and classifier

import os
import sys
import signal
import logging
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_dpi_probe.engine.capture_daemon import CaptureDaemon
from ransomeye_dpi_probe.transport.uploader import ChunkUploader
from ransomeye_dpi_probe.transport.signed_receipt_store import SignedReceiptStore
from ransomeye_dpi_probe.ml.asset_classifier import AssetClassifier
from ransomeye_dpi_probe.ml.incremental_trainer import IncrementalTrainer
from ransomeye_dpi_probe.metrics.exporter import MetricsExporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            os.environ.get('LOG_DIR', '/var/log/ransomeye-probe') + '/probe.log'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProbeMain:
    """Main orchestrator for DPI Probe."""
    
    def __init__(self):
        """Initialize probe components."""
        logger.info("Initializing RansomEye DPI Probe...")
        
        # Initialize components
        self.capture_daemon = CaptureDaemon()
        
        # Initialize receipt store
        receipt_store = SignedReceiptStore(
            store_dir=os.environ.get('RECEIPT_STORE_DIR', '/var/lib/ransomeye-probe/receipts'),
            server_public_key_path=os.environ.get('SERVER_PUBLIC_KEY_PATH', '/etc/ransomeye-probe/certs/server.pub')
        )
        
        # Initialize uploader
        buffer_dir = os.environ.get('BUFFER_DIR', '/var/lib/ransomeye-probe/buffer')
        self.uploader = ChunkUploader(buffer_dir, receipt_store)
        
        # Initialize classifier
        model_dir = os.environ.get('MODEL_DIR', '/home/ransomeye/rebuild/models')
        self.classifier = AssetClassifier(model_path=model_dir)
        
        # Initialize incremental trainer
        feedback_dir = os.environ.get('FEEDBACK_DIR', '/var/lib/ransomeye-probe/feedback')
        self.trainer = IncrementalTrainer(self.classifier, feedback_dir)
        
        # Initialize metrics exporter
        self.metrics = MetricsExporter(self.capture_daemon, self.uploader)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Probe initialization complete")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start all probe components."""
        logger.info("Starting RansomEye DPI Probe...")
        
        # Start metrics exporter
        metrics_port = int(os.environ.get('PROBE_METRICS_PORT', '9092'))
        self.metrics.start(port=metrics_port)
        
        # Start uploader
        self.uploader.start()
        
        # Start incremental trainer
        self.trainer.start()
        
        # Start capture daemon (blocks)
        self.capture_daemon.start()
        
        logger.info("All probe components started")
    
    def stop(self):
        """Stop all probe components."""
        logger.info("Stopping RansomEye DPI Probe...")
        
        # Stop capture daemon
        self.capture_daemon.stop()
        
        # Stop trainer
        self.trainer.stop()
        
        # Stop uploader
        self.uploader.stop()
        
        # Stop metrics
        self.metrics.stop()
        
        logger.info("Probe shutdown complete")


def main():
    """Main entry point."""
    probe = ProbeMain()
    
    try:
        probe.start()
        
        # Keep running
        import time
        while probe.capture_daemon.running:
            time.sleep(1)
            
            # Print stats periodically
            stats = probe.capture_daemon.get_stats()
            logger.info(f"Stats: {stats['packets_captured']} packets, "
                       f"{stats['active_flows']} flows, "
                       f"{stats['packets_dropped']} dropped")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        probe.stop()


if __name__ == '__main__':
    main()

