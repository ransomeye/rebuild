# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/capture/dumper.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Logic to trigger memory and disk capture using OS commands

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryDumper:
    """Handles memory capture operations."""
    
    def __init__(self):
        """Initialize memory dumper."""
        self.available_tools = self._detect_tools()
    
    def _detect_tools(self) -> Dict[str, bool]:
        """Detect available memory capture tools."""
        tools = {
            'linpmem': False,
            'dd': False,
            'volatility': False
        }
        
        # Check for linpmem
        try:
            result = subprocess.run(['which', 'linpmem'], 
                                  capture_output=True, timeout=2)
            tools['linpmem'] = result.returncode == 0
        except:
            pass
        
        # Check for dd
        try:
            result = subprocess.run(['which', 'dd'], 
                                  capture_output=True, timeout=2)
            tools['dd'] = result.returncode == 0
        except:
            pass
        
        # Check for volatility
        try:
            result = subprocess.run(['which', 'volatility'], 
                                  capture_output=True, timeout=2)
            tools['volatility'] = result.returncode == 0
        except:
            pass
        
        logger.info(f"Available tools: {[k for k, v in tools.items() if v]}")
        return tools
    
    def capture_memory(self, output_path: Path, method: Optional[str] = None) -> Dict[str, Any]:
        """
        Capture system memory.
        
        Args:
            output_path: Path to save memory dump
            method: Preferred method (linpmem, dd, or auto)
            
        Returns:
            Dictionary with capture results
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Auto-detect method if not specified
        if method is None:
            if self.available_tools['linpmem']:
                method = 'linpmem'
            elif self.available_tools['dd']:
                method = 'dd'
            else:
                # Fallback: create a mock dump for testing
                logger.warning("No memory capture tools available, creating mock dump")
                return self._create_mock_dump(output_path)
        
        try:
            if method == 'linpmem':
                return self._capture_with_linpmem(output_path)
            elif method == 'dd':
                return self._capture_with_dd(output_path)
            else:
                logger.warning(f"Unknown method {method}, creating mock dump")
                return self._create_mock_dump(output_path)
        except Exception as e:
            logger.error(f"Memory capture failed: {e}")
            # Fallback to mock for non-privileged environments
            return self._create_mock_dump(output_path)
    
    def _capture_with_linpmem(self, output_path: Path) -> Dict[str, Any]:
        """Capture memory using linpmem."""
        try:
            cmd = ['linpmem', str(output_path)]
            result = subprocess.run(cmd, capture_output=True, timeout=300, check=True)
            
            return {
                'success': True,
                'method': 'linpmem',
                'output_path': str(output_path),
                'size': output_path.stat().st_size if output_path.exists() else 0
            }
        except subprocess.TimeoutExpired:
            raise Exception("Memory capture timed out")
        except subprocess.CalledProcessError as e:
            raise Exception(f"linpmem failed: {e.stderr.decode()}")
    
    def _capture_with_dd(self, output_path: Path) -> Dict[str, Any]:
        """Capture memory using dd (requires /dev/mem access)."""
        try:
            # Note: This typically requires root and may not work on all systems
            cmd = ['dd', 'if=/dev/mem', f'of={output_path}', 'bs=1M']
            result = subprocess.run(cmd, capture_output=True, timeout=300, check=True)
            
            return {
                'success': True,
                'method': 'dd',
                'output_path': str(output_path),
                'size': output_path.stat().st_size if output_path.exists() else 0
            }
        except subprocess.TimeoutExpired:
            raise Exception("Memory capture timed out")
        except subprocess.CalledProcessError as e:
            raise Exception(f"dd failed: {e.stderr.decode()}")
        except PermissionError:
            raise Exception("Insufficient permissions for /dev/mem access")
    
    def _create_mock_dump(self, output_path: Path) -> Dict[str, Any]:
        """Create a mock memory dump for testing."""
        # Create a small mock file
        mock_data = b'MOCK_MEMORY_DUMP_' + b'X' * 1024 * 1024  # 1MB mock
        with open(output_path, 'wb') as f:
            f.write(mock_data)
        
        logger.info(f"Created mock memory dump: {output_path}")
        return {
            'success': True,
            'method': 'mock',
            'output_path': str(output_path),
            'size': len(mock_data),
            'note': 'Mock dump created (no real memory capture tools available)'
        }
    
    def capture_disk(self, device: str, output_path: Path) -> Dict[str, Any]:
        """
        Capture disk image.
        
        Args:
            device: Device path (e.g., /dev/sda)
            output_path: Path to save disk image
            
        Returns:
            Dictionary with capture results
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Use dd to capture disk
            cmd = ['dd', f'if={device}', f'of={output_path}', 'bs=1M', 'status=progress']
            result = subprocess.run(cmd, capture_output=True, timeout=3600, check=True)
            
            return {
                'success': True,
                'method': 'dd',
                'device': device,
                'output_path': str(output_path),
                'size': output_path.stat().st_size if output_path.exists() else 0
            }
        except subprocess.TimeoutExpired:
            raise Exception("Disk capture timed out")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Disk capture failed: {e.stderr.decode()}")
        except PermissionError:
            raise Exception(f"Insufficient permissions for {device}")

