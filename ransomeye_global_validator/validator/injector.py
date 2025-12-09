# Path and File Name : /home/ransomeye/rebuild/ransomeye_global_validator/validator/injector.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: HTTP client for injecting synthetic payloads into Core APIs

import os
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Injector:
    """HTTP client for injecting synthetic payloads into Core APIs."""
    
    def __init__(self):
        """Initialize injector with API URLs from environment."""
        self.alert_engine_url = os.environ.get(
            'ALERT_ENGINE_URL',
            'http://localhost:8004'
        )
        self.killchain_url = os.environ.get(
            'KILLCHAIN_API_URL',
            'http://localhost:8005'
        )
        self.forensic_api_url = os.environ.get(
            'FORENSIC_API_URL',
            'http://localhost:8006'
        )
        self.timeout = aiohttp.ClientTimeout(total=30)
        logger.info(f"Injector initialized - Alert: {self.alert_engine_url}, KillChain: {self.killchain_url}")
    
    async def inject_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject alert into Alert Engine API.
        
        Args:
            alert_data: Alert payload
            
        Returns:
            Response with alert_id and status
            
        Raises:
            Exception: If injection fails
        """
        url = f"{self.alert_engine_url}/alerts/ingest"
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                start_time = datetime.utcnow()
                async with session.post(url, json=alert_data) as response:
                    latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Alert injected successfully: {result.get('alert_id')} (latency: {latency_ms:.2f}ms)")
                        return {
                            "success": True,
                            "alert_id": result.get("alert_id"),
                            "status": result.get("status"),
                            "is_duplicate": result.get("is_duplicate", False),
                            "matches": result.get("matches", []),
                            "latency_ms": latency_ms,
                            "response": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Alert injection failed: {response.status} - {error_text}")
                        raise Exception(f"Alert API returned {response.status}: {error_text}")
        
        except asyncio.TimeoutError:
            logger.error("Alert injection timed out")
            raise Exception("Alert injection timed out after 30 seconds")
        except Exception as e:
            logger.error(f"Alert injection error: {e}")
            raise
    
    async def inject_multiple_alerts(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Inject multiple alerts concurrently.
        
        Args:
            alerts: List of alert payloads
            
        Returns:
            List of injection results
        """
        tasks = [self.inject_alert(alert) for alert in alerts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "alert_index": i
                })
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r.get("success", False))
        logger.info(f"Injected {success_count}/{len(alerts)} alerts successfully")
        return processed_results
    
    async def build_timeline(self, incident_id: str, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build timeline via KillChain API.
        
        Args:
            incident_id: Incident identifier
            alerts: List of alert data
            
        Returns:
            Timeline build result
        """
        url = f"{self.killchain_url}/timeline/build"
        
        # Convert alerts to AlertData format
        alert_payload = [
            {
                "source": alert.get("source"),
                "alert_type": alert.get("alert_type"),
                "target": alert.get("target"),
                "severity": alert.get("severity", "medium"),
                "timestamp": alert.get("timestamp"),
                "metadata": alert.get("metadata", {})
            }
            for alert in alerts
        ]
        
        payload = {
            "incident_id": incident_id,
            "alerts": alert_payload
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                start_time = datetime.utcnow()
                async with session.post(url, json=payload) as response:
                    latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Timeline built successfully: {result.get('timeline_id')} (latency: {latency_ms:.2f}ms)")
                        return {
                            "success": True,
                            "timeline_id": result.get("timeline_id"),
                            "incident_id": result.get("incident_id"),
                            "latency_ms": latency_ms,
                            "response": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Timeline build failed: {response.status} - {error_text}")
                        raise Exception(f"KillChain API returned {response.status}: {error_text}")
        
        except asyncio.TimeoutError:
            logger.error("Timeline build timed out")
            raise Exception("Timeline build timed out after 30 seconds")
        except Exception as e:
            logger.error(f"Timeline build error: {e}")
            raise
    
    async def check_health(self, service: str) -> bool:
        """
        Check health of a service.
        
        Args:
            service: Service name (alert_engine, killchain, forensic)
            
        Returns:
            True if healthy, False otherwise
        """
        url_map = {
            "alert_engine": f"{self.alert_engine_url}/health",
            "killchain": f"{self.killchain_url}/health",
            "forensic": f"{self.forensic_api_url}/health"
        }
        
        url = url_map.get(service)
        if not url:
            logger.error(f"Unknown service: {service}")
            return False
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("status") == "healthy"
                    return False
        except Exception as e:
            logger.error(f"Health check failed for {service}: {e}")
            return False

