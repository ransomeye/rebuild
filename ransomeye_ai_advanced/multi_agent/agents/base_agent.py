# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/multi_agent/agents/base_agent.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Abstract base class defining agent interface with process(message) method

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

from ..message_bus import Message, MessageBus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """State object passed between agents."""
    conversation_id: str
    user_query: str
    context: Dict[str, Any] = None
    intermediate_results: Dict[str, Any] = None
    final_answer: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.intermediate_results is None:
            self.intermediate_results = {}
        if self.metadata is None:
            self.metadata = {}


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system.
    Each agent must implement the process() method.
    """
    
    def __init__(
        self,
        agent_name: str,
        message_bus: MessageBus,
        description: str = ""
    ):
        """
        Initialize base agent.
        
        Args:
            agent_name: Unique name for this agent
            message_bus: Message bus instance for communication
            description: Human-readable description of agent's purpose
        """
        self.agent_name = agent_name
        self.message_bus = message_bus
        self.description = description
        self.is_active = False
    
    @abstractmethod
    async def process(
        self,
        message: Message,
        state: AgentState
    ) -> tuple[Optional[Message], AgentState]:
        """
        Process a message and update state.
        
        Args:
            message: Incoming message
            state: Current conversation state
            
        Returns:
            Tuple of (output_message, updated_state)
            output_message can be None if agent doesn't need to send a message
        """
        pass
    
    async def send_message(
        self,
        receiver: str,
        message_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        priority: int = 0
    ) -> bool:
        """
        Helper method to send a message via the bus.
        
        Args:
            receiver: Target agent name
            message_type: Type of message
            payload: Message payload
            correlation_id: Optional correlation ID
            priority: Message priority
            
        Returns:
            True if sent successfully
        """
        message = Message(
            sender=self.agent_name,
            receiver=receiver,
            message_type=message_type,
            payload=payload,
            correlation_id=correlation_id,
            priority=priority
        )
        return await self.message_bus.publish(message, target_agent=receiver)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about this agent."""
        return {
            'name': self.agent_name,
            'description': self.description,
            'is_active': self.is_active
        }
    
    async def start(self):
        """Start the agent (override if needed)."""
        self.is_active = True
        logger.info(f"Agent {self.agent_name} started")
    
    async def stop(self):
        """Stop the agent (override if needed)."""
        self.is_active = False
        logger.info(f"Agent {self.agent_name} stopped")

