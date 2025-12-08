# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/executor/action_runners/runner_agent_call.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Sends commands to agents with mTLS and HMAC-signed headers

import os
import json
import hmac
import hashlib
import base64
import ssl
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentCallRunner:
    """
    Sends commands to agents using mTLS and HMAC signing.
    """
    
    def __init__(self):
        """Initialize agent call runner."""
        self.hmac_secret_path = Path(os.environ.get(
            'HMAC_SECRET_PATH',
            '/home/ransomeye/rebuild/certs/hmac_secret.key'
        ))
        self.hmac_secret = self._load_hmac_secret()
        
        # mTLS configuration
        self.client_cert_path = Path(os.environ.get(
            'CLIENT_CERT_PATH',
            '/home/ransomeye/rebuild/certs/client_cert.pem'
        ))
        self.client_key_path = Path(os.environ.get(
            'CLIENT_KEY_PATH',
            '/home/ransomeye/rebuild/certs/client_key.pem'
        ))
        self.ca_cert_path = Path(os.environ.get(
            'CA_CERT_PATH',
            '/home/ransomeye/rebuild/certs/ca_cert.pem'
        ))
    
    def _load_hmac_secret(self) -> Optional[bytes]:
        """Load HMAC secret."""
        if not self.hmac_secret_path.exists():
            logger.warning(f"HMAC secret not found: {self.hmac_secret_path}")
            return None
        
        try:
            with open(self.hmac_secret_path, 'rb') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load HMAC secret: {e}")
            return None
    
    def _generate_hmac_signature(self, payload: bytes) -> str:
        """
        Generate HMAC signature for payload.
        
        Args:
            payload: Request payload bytes
            
        Returns:
            Base64-encoded HMAC signature
        """
        if not self.hmac_secret:
            raise ValueError("HMAC secret not loaded")
        
        signature = hmac.new(
            self.hmac_secret,
            payload,
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    async def run(self, target: Dict[str, Any], parameters: Dict[str, Any],
                 context: Dict[str, Any]) -> str:
        """
        Send command to agent.
        
        Args:
            target: Target specification (agent_id or tags)
            parameters: Command parameters
            context: Execution context
            
        Returns:
            Agent response
        """
        # Resolve agent endpoint from target
        agent_id = target.get('agent_id')
        if not agent_id:
            # Resolve from tags (simplified - in production would query agent registry)
            raise ValueError("agent_id required for agent calls")
        
        # Get agent endpoint (simplified - in production would query agent registry)
        agent_endpoint = os.environ.get(
            'AGENT_BASE_URL',
            f'https://agent-{agent_id}:8443'
        )
        
        # Prepare payload
        payload = {
            'command': parameters.get('command'),
            'parameters': parameters,
            'context': context
        }
        payload_json = json.dumps(payload, sort_keys=True)
        payload_bytes = payload_json.encode('utf-8')
        
        # Generate HMAC signature
        signature = self._generate_hmac_signature(payload_bytes)
        
        # Prepare mTLS context
        ssl_context = None
        if self.client_cert_path.exists() and self.client_key_path.exists():
            ssl_context = ssl.create_default_context()
            ssl_context.load_cert_chain(
                str(self.client_cert_path),
                str(self.client_key_path)
            )
            if self.ca_cert_path.exists():
                ssl_context.load_verify_locations(str(self.ca_cert_path))
                ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        # Send request
        url = f"{agent_endpoint}/api/v1/execute"
        headers = {
            'Content-Type': 'application/json',
            'X-Agent-Signature': signature
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=payload_bytes,
                    headers=headers,
                    ssl=ssl_context
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Agent command executed successfully: {agent_id}")
                        return json.dumps(result)
                    else:
                        error_text = await response.text()
                        raise RuntimeError(f"Agent call failed: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Agent call error: {e}")
            raise
    
    def run_sync(self, target: Dict[str, Any], parameters: Dict[str, Any],
                context: Dict[str, Any]) -> str:
        """
        Synchronous version of run (for compatibility).
        
        Args:
            target: Target specification
            parameters: Command parameters
            context: Execution context
            
        Returns:
            Agent response
        """
        import asyncio
        return asyncio.run(self.run(target, parameters, context))

