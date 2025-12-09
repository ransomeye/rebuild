# Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/windows_service/ransomeye_agent_service.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Windows Service wrapper using pywin32 ServiceFramework for SCM integration

import os
import sys
import time
import logging
from pathlib import Path

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logging.warning("pywin32 not available, service mode disabled")

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.agent_main import AgentMain

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
                        'RansomEye', 'logs', 'agent_service.log')
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


if WIN32_AVAILABLE:
    class RansomEyeAgentService(win32serviceutil.ServiceFramework):
        """Windows Service wrapper for RansomEye Agent."""
        
        _svc_name_ = "RansomEyeAgent"
        _svc_display_name_ = "RansomEye Security Agent"
        _svc_description_ = "RansomEye Enterprise Security Agent - Threat Detection and Telemetry Collection"
        
        def __init__(self, args):
            """Initialize Windows Service."""
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.agent = None
            logger.info("RansomEye Agent Service initialized")
        
        def SvcStop(self):
            """Handle service stop request from SCM."""
            logger.info("Service stop requested")
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            
            if self.agent:
                self.agent.stop()
            
            win32event.SetEvent(self.stop_event)
            logger.info("Service stop signal sent")
        
        def SvcDoRun(self):
            """Main service execution loop."""
            try:
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STARTED,
                    (self._svc_name_, '')
                )
                
                logger.info("Starting RansomEye Agent Service...")
                
                # Initialize and start agent
                self.agent = AgentMain()
                self.agent.setup_components()
                self.agent.running = True
                
                # Start agent threads
                self.agent._start_threads()
                
                logger.info("RansomEye Agent Service started successfully")
                
                # Wait for stop event
                win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
                
            except Exception as e:
                logger.error(f"Service error: {e}", exc_info=True)
                servicemanager.LogErrorMsg(f"Service error: {e}")
            finally:
                if self.agent:
                    self.agent.stop()
                
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STOPPED,
                    (self._svc_name_, '')
                )
                logger.info("RansomEye Agent Service stopped")


def main():
    """Main entry point for service installation/removal/execution."""
    if not WIN32_AVAILABLE:
        logger.error("pywin32 not available. Install with: pip install pywin32")
        sys.exit(1)
    
    if len(sys.argv) == 1:
        # Running as service
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(RansomEyeAgentService)
            servicemanager.StartServiceCtrlDispatcher()
        except win32service.error as details:
            if details[0] == win32service.ERROR_FAILED_SERVICE_CONTROLLER_CONNECT:
                # Not running as service, run in console mode
                logger.info("Not running as service, starting in console mode...")
                agent = AgentMain()
                agent.setup_components()
                agent.start()
            else:
                logger.error(f"Service error: {details}")
                sys.exit(1)
    else:
        # Handle service commands (install, remove, start, stop, etc.)
        win32serviceutil.HandleCommandLine(RansomEyeAgentService)


if __name__ == "__main__":
    main()

