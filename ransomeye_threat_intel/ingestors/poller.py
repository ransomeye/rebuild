# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/ingestors/poller.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Scheduler for fetching feeds at TI_POLL_INTERVAL_SEC

import os
import asyncio
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
import logging

from .misp_ingestor import MISPIngestor
from .api_ingestor import APIIngestor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeedPoller:
    """
    Scheduler for polling threat intelligence feeds at configured intervals.
    """
    
    def __init__(
        self,
        poll_interval: Optional[int] = None,
        callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None
    ):
        """
        Initialize feed poller.
        
        Args:
            poll_interval: Poll interval in seconds (from TI_POLL_INTERVAL_SEC env var)
            callback: Callback function to process ingested IOCs
        """
        self.poll_interval = poll_interval or int(os.environ.get('TI_POLL_INTERVAL_SEC', 3600))
        self.callback = callback
        self.is_running = False
        self.feeds: List[Dict[str, Any]] = []
        
        # Initialize ingestors
        self.misp_ingestor = MISPIngestor()
        self.api_ingestor = APIIngestor()
    
    def add_feed(
        self,
        feed_type: str,
        feed_config: Dict[str, Any]
    ):
        """
        Add a feed to poll.
        
        Args:
            feed_type: Type of feed ('misp', 'api', 'malwarebazaar', 'ransomware_live')
            feed_config: Feed configuration
        """
        feed = {
            'type': feed_type,
            'config': feed_config,
            'last_poll': None,
            'enabled': True
        }
        self.feeds.append(feed)
        logger.info(f"Added feed: {feed_type}")
    
    async def poll_feed(self, feed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Poll a single feed.
        
        Args:
            feed: Feed configuration
            
        Returns:
            List of ingested IOCs
        """
        if not feed.get('enabled', True):
            return []
        
        feed_type = feed['type']
        config = feed['config']
        
        try:
            iocs = []
            
            if feed_type == 'misp':
                # Poll MISP
                filters = config.get('filters', {})
                iocs = self.misp_ingestor.fetch_from_misp(filters)
            
            elif feed_type == 'api':
                # Poll generic API
                url = config.get('url', '')
                format_type = config.get('format', 'json')
                if format_type == 'json':
                    iocs = self.api_ingestor.ingest_json(url)
                elif format_type == 'csv':
                    iocs = self.api_ingestor.ingest_csv(url)
            
            elif feed_type == 'malwarebazaar':
                # Poll MalwareBazaar
                iocs = self.api_ingestor.ingest_malwarebazaar()
            
            elif feed_type == 'ransomware_live':
                # Poll Ransomware.live
                iocs = self.api_ingestor.ingest_ransomware_live()
            
            elif feed_type == 'stix_file':
                # Poll STIX file
                file_path = config.get('file_path', '')
                if file_path:
                    iocs = self.misp_ingestor.ingest_stix_file(file_path)
            
            feed['last_poll'] = datetime.utcnow().isoformat()
            logger.info(f"Polled {feed_type}: {len(iocs)} IOCs")
            
            return iocs
            
        except Exception as e:
            logger.error(f"Error polling feed {feed_type}: {e}")
            return []
    
    async def poll_all_feeds(self) -> List[Dict[str, Any]]:
        """
        Poll all enabled feeds.
        
        Returns:
            List of all ingested IOCs
        """
        all_iocs = []
        
        for feed in self.feeds:
            iocs = await self.poll_feed(feed)
            all_iocs.extend(iocs)
        
        # Call callback if provided
        if self.callback and all_iocs:
            try:
                self.callback(all_iocs)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
        
        return all_iocs
    
    async def poll_loop(self):
        """
        Main polling loop.
        """
        self.is_running = True
        logger.info(f"Starting poll loop with interval {self.poll_interval}s")
        
        while self.is_running:
            try:
                await self.poll_all_feeds()
            except Exception as e:
                logger.error(f"Error in poll loop: {e}")
            
            # Wait for next poll
            await asyncio.sleep(self.poll_interval)
    
    def start(self):
        """Start polling in background."""
        if not self.is_running:
            asyncio.create_task(self.poll_loop())
            logger.info("Poll loop started")
    
    def stop(self):
        """Stop polling."""
        self.is_running = False
        logger.info("Poll loop stopped")
    
    def get_feed_status(self) -> List[Dict[str, Any]]:
        """Get status of all feeds."""
        return [
            {
                'type': feed['type'],
                'enabled': feed.get('enabled', True),
                'last_poll': feed.get('last_poll'),
                'config': feed.get('config', {})
            }
            for feed in self.feeds
        ]

