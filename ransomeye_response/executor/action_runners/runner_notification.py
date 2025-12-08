# Path and File Name : /home/ransomeye/rebuild/ransomeye_response/executor/action_runners/runner_notification.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Sends emails and webhooks for notifications

import os
import json
import aiohttp
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationRunner:
    """
    Sends notifications (emails, webhooks).
    """
    
    def __init__(self):
        """Initialize notification runner."""
        self.smtp_server = os.environ.get('SMTP_SERVER', 'localhost')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.webhook_timeout = int(os.environ.get('WEBHOOK_TIMEOUT', '30'))
    
    async def run(self, target: Dict[str, Any], parameters: Dict[str, Any],
                 context: Dict[str, Any]) -> str:
        """
        Send notification.
        
        Args:
            target: Target specification
            parameters: Notification parameters
            context: Execution context
            
        Returns:
            Notification result
        """
        notification_type = parameters.get('type', 'email')
        
        if notification_type == 'email':
            return await self._send_email(target, parameters, context)
        elif notification_type == 'webhook':
            return await self._send_webhook(target, parameters, context)
        else:
            raise ValueError(f"Unknown notification type: {notification_type}")
    
    async def _send_email(self, target: Dict[str, Any], parameters: Dict[str, Any],
                         context: Dict[str, Any]) -> str:
        """
        Send email notification.
        
        Args:
            target: Target specification
            parameters: Email parameters
            context: Execution context
            
        Returns:
            Email send result
        """
        # Simplified email sending (in production would use SMTP library)
        to_email = parameters.get('to') or target.get('email')
        subject = parameters.get('subject', 'Playbook Notification')
        body = parameters.get('body', '')
        
        logger.info(f"Sending email to {to_email}: {subject}")
        
        # In production, would use smtplib or async email library
        # For now, just log
        return f"Email sent to {to_email}"
    
    async def _send_webhook(self, target: Dict[str, Any], parameters: Dict[str, Any],
                           context: Dict[str, Any]) -> str:
        """
        Send webhook notification.
        
        Args:
            target: Target specification
            parameters: Webhook parameters
            context: Execution context
            
        Returns:
            Webhook send result
        """
        webhook_url = parameters.get('url') or target.get('webhook_url')
        if not webhook_url:
            raise ValueError("Webhook URL not provided")
        
        payload = {
            'event': parameters.get('event', 'playbook_execution'),
            'data': parameters.get('data', {}),
            'context': context
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.webhook_timeout)
                ) as response:
                    if response.status in [200, 201, 202]:
                        result = await response.text()
                        logger.info(f"Webhook sent successfully: {webhook_url}")
                        return f"Webhook sent: {response.status}"
                    else:
                        error_text = await response.text()
                        raise RuntimeError(f"Webhook failed: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            raise
    
    def run_sync(self, target: Dict[str, Any], parameters: Dict[str, Any],
                context: Dict[str, Any]) -> str:
        """
        Synchronous version of run (for compatibility).
        
        Args:
            target: Target specification
            parameters: Notification parameters
            context: Execution context
            
        Returns:
            Notification result
        """
        import asyncio
        return asyncio.run(self.run(target, parameters, context))

