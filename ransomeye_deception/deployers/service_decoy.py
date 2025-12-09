# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/deployers/service_decoy.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Spawns low-interaction listeners that bind ports and send fake banners

import os
import sys
import socket
import asyncio
import signal
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceDecoy:
    """
    Service decoy deployer.
    Creates low-interaction network listeners with fake banners.
    """
    
    def __init__(self):
        """Initialize service decoy deployer."""
        self.active_servers = {}  # decoy_id -> {server, task, port, host}
        self.banners = {
            22: "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5\r\n",
            80: "HTTP/1.1 200 OK\r\nServer: Apache/2.4.41\r\n",
            443: "HTTP/1.1 200 OK\r\nServer: nginx/1.18.0\r\n",
            3306: "5.7.33-log\x00\x00\x00\x00",  # MySQL banner
            5432: "E\x00\x00\x00\x0a\x00\x00\x00\x00",  # PostgreSQL
            8080: "HTTP/1.1 200 OK\r\nServer: Tomcat/9.0.41\r\n",
            8443: "HTTP/1.1 200 OK\r\nServer: Jetty/9.4.38\r\n",
            3389: "\x03\x00\x00\x13\x0e\xe0\x00\x00\x00\x00\x00\x01\x00\x08\x00\x03\x00\x00\x00",  # RDP
            5900: "RFB 003.008\n"  # VNC
        }
        
        logger.info("Service decoy deployer initialized")
    
    def _get_banner(self, port: int) -> bytes:
        """Get banner for port."""
        banner = self.banners.get(port, b"Welcome\r\n")
        if isinstance(banner, str):
            return banner.encode('utf-8')
        return banner
    
    async def _handle_client(self, reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter, decoy_id: str, port: int):
        """
        Handle client connection.
        
        Args:
            reader: Stream reader
            writer: Stream writer
            decoy_id: Decoy ID
            port: Port number
        """
        try:
            # Get client address
            addr = writer.get_extra_info('peername')
            client_ip = addr[0] if addr else 'unknown'
            
            logger.info(f"Service decoy {decoy_id} connection from {client_ip}:{port}")
            
            # Send banner
            banner = self._get_banner(port)
            writer.write(banner)
            await writer.drain()
            
            # Wait briefly for any data
            try:
                data = await asyncio.wait_for(reader.read(1024), timeout=2.0)
                if data:
                    logger.info(f"Service decoy {decoy_id} received data: {data[:100]}")
            except asyncio.TimeoutError:
                pass
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            # Record connection event (will be picked up by monitor)
            await self._on_connection(decoy_id, client_ip, port)
            
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
    
    async def _on_connection(self, decoy_id: str, client_ip: str, port: int):
        """Callback for connection events."""
        # This will be handled by monitor/decoy_monitor.py
        # In production, this would trigger the monitor's record_connection method
        pass
    
    async def _run_server(self, decoy_id: str, host: str, port: int):
        """
        Run async server.
        
        Args:
            decoy_id: Decoy ID
            host: Host to bind to
            port: Port to bind to
        """
        try:
            server = await asyncio.start_server(
                lambda r, w: self._handle_client(r, w, decoy_id, port),
                host=host,
                port=port
            )
            
            logger.info(f"Service decoy {decoy_id} listening on {host}:{port}")
            
            # Store server
            self.active_servers[decoy_id]['server'] = server
            
            # Serve forever
            async with server:
                await server.serve_forever()
                
        except Exception as e:
            logger.error(f"Error running server for {decoy_id}: {e}")
            raise
    
    async def provision(self, decoy_id: str, location: str,
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Provision a service decoy.
        
        Args:
            decoy_id: Unique decoy ID
            location: Host:Port format (e.g., "0.0.0.0:2222")
            metadata: Optional metadata
            
        Returns:
            Provision result
        """
        try:
            # Parse location
            if ':' in location:
                host, port_str = location.rsplit(':', 1)
                port = int(port_str)
            else:
                host = '0.0.0.0'
                port = int(location)
            
            # Check if port is available
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                sock.close()
            except OSError as e:
                raise RuntimeError(f"Port {port} is not available: {e}")
            
            # Create server task
            self.active_servers[decoy_id] = {
                'host': host,
                'port': port,
                'task': None,
                'server': None
            }
            
            # Start server in background
            task = asyncio.create_task(self._run_server(decoy_id, host, port))
            self.active_servers[decoy_id]['task'] = task
            
            # Wait a bit to ensure server started
            await asyncio.sleep(0.5)
            
            logger.info(f"Service decoy provisioned: {host}:{port}")
            
            return {
                'decoy_id': decoy_id,
                'type': 'service',
                'host': host,
                'port': port,
                'banner': self.banners.get(port, 'default').decode('utf-8', errors='ignore')[:50]
            }
            
        except Exception as e:
            logger.error(f"Error provisioning service decoy: {e}")
            # Cleanup on error
            if decoy_id in self.active_servers:
                await self.deprovision(decoy_id, {})
            raise
    
    async def verify(self, decoy_id: str, provision_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify service decoy is active.
        
        Args:
            decoy_id: Decoy ID
            provision_result: Provision result
            
        Returns:
            Verification result
        """
        try:
            if decoy_id not in self.active_servers:
                return {
                    'verified': False,
                    'error': 'Decoy not found in active servers'
                }
            
            host = provision_result['host']
            port = provision_result['port']
            
            # Try to connect to verify it's listening
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=2.0
                )
                writer.close()
                await writer.wait_closed()
                
                return {
                    'verified': True,
                    'host': host,
                    'port': port
                }
            except (ConnectionRefusedError, asyncio.TimeoutError):
                return {
                    'verified': False,
                    'error': 'Service not listening'
                }
            
        except Exception as e:
            return {
                'verified': False,
                'error': str(e)
            }
    
    async def deprovision(self, decoy_id: str, provision_result: Dict[str, Any]):
        """
        Deprovision service decoy.
        
        Args:
            decoy_id: Decoy ID
            provision_result: Provision result
        """
        try:
            if decoy_id not in self.active_servers:
                return
            
            server_info = self.active_servers[decoy_id]
            
            # Stop server
            if server_info.get('server'):
                server_info['server'].close()
                await server_info['server'].wait_closed()
            
            # Cancel task
            if server_info.get('task'):
                server_info['task'].cancel()
                try:
                    await server_info['task']
                except asyncio.CancelledError:
                    pass
            
            logger.info(f"Service decoy deprovisioned: {decoy_id}")
            
            del self.active_servers[decoy_id]
            
        except Exception as e:
            logger.error(f"Error deprovisioning service decoy: {e}")
            raise

