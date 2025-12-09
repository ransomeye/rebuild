# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/multi_agent/message_bus.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: In-memory asyncio.Queue based message bus for agent-to-agent communication

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Message structure for agent communication."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: str = ""
    message_type: str = ""  # 'task', 'result', 'query', 'response', 'error'
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None  # For tracking related messages
    priority: int = 0  # Higher = more urgent


class MessageBus:
    """
    In-memory message bus using asyncio.Queue for agent-to-agent communication.
    Supports topic-based routing and priority queues.
    """
    
    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize message bus.
        
        Args:
            max_queue_size: Maximum messages per queue before blocking
        """
        self.max_queue_size = max_queue_size
        # Main message queue
        self.main_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        # Topic-based queues
        self.topic_queues: Dict[str, asyncio.Queue] = {}
        # Agent-specific queues
        self.agent_queues: Dict[str, asyncio.Queue] = {}
        # Message history (for debugging)
        self.message_history: List[Message] = []
        self.max_history = 1000
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def publish(
        self,
        message: Message,
        topic: Optional[str] = None,
        target_agent: Optional[str] = None
    ) -> bool:
        """
        Publish a message to the bus.
        
        Args:
            message: Message to publish
            topic: Optional topic name for topic-based routing
            target_agent: Optional specific agent to route to
            
        Returns:
            True if published successfully
        """
        try:
            # Add to history
            async with self._lock:
                self.message_history.append(message)
                if len(self.message_history) > self.max_history:
                    self.message_history.pop(0)
            
            # Route to target agent queue if specified
            if target_agent:
                if target_agent not in self.agent_queues:
                    self.agent_queues[target_agent] = asyncio.Queue(maxsize=self.max_queue_size)
                await self.agent_queues[target_agent].put(message)
                logger.debug(f"Published message {message.message_id} to agent {target_agent}")
                return True
            
            # Route to topic queue if specified
            if topic:
                if topic not in self.topic_queues:
                    self.topic_queues[topic] = asyncio.Queue(maxsize=self.max_queue_size)
                await self.topic_queues[topic].put(message)
                logger.debug(f"Published message {message.message_id} to topic {topic}")
                return True
            
            # Default: add to main queue
            await self.main_queue.put(message)
            logger.debug(f"Published message {message.message_id} to main queue")
            return True
            
        except asyncio.QueueFull:
            logger.error(f"Queue full, cannot publish message {message.message_id}")
            return False
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False
    
    async def subscribe(
        self,
        agent_name: str,
        topic: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Optional[Message]:
        """
        Subscribe to messages (blocking).
        
        Args:
            agent_name: Name of subscribing agent
            topic: Optional topic to subscribe to
            timeout: Optional timeout in seconds
            
        Returns:
            Message or None if timeout
        """
        try:
            # Check agent-specific queue first
            if agent_name in self.agent_queues:
                queue = self.agent_queues[agent_name]
            elif topic and topic in self.topic_queues:
                queue = self.topic_queues[topic]
            else:
                queue = self.main_queue
            
            if timeout:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
            else:
                message = await queue.get()
            
            logger.debug(f"Agent {agent_name} received message {message.message_id}")
            return message
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout waiting for message for agent {agent_name}")
            return None
        except Exception as e:
            logger.error(f"Error subscribing to messages: {e}")
            return None
    
    async def get_messages_by_correlation(
        self,
        correlation_id: str
    ) -> List[Message]:
        """
        Get all messages with a specific correlation ID.
        
        Args:
            correlation_id: Correlation ID to search for
            
        Returns:
            List of matching messages
        """
        async with self._lock:
            return [
                msg for msg in self.message_history
                if msg.correlation_id == correlation_id
            ]
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about queue sizes."""
        stats = {
            'main_queue_size': self.main_queue.qsize(),
            'topic_queues': {
                topic: queue.qsize()
                for topic, queue in self.topic_queues.items()
            },
            'agent_queues': {
                agent: queue.qsize()
                for agent, queue in self.agent_queues.items()
            },
            'history_size': len(self.message_history)
        }
        return stats
    
    def clear_history(self):
        """Clear message history."""
        self.message_history.clear()
        logger.info("Message history cleared")

