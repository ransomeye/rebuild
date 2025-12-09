# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/multi_agent/orchestrator.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Multi-agent orchestrator that coordinates agents and maintains conversation state

import os
import sys
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .message_bus import MessageBus, Message
from .agents.base_agent import AgentState
from .agents.planner_agent import PlannerAgent
from .agents.retriever_agent import RetrieverAgent
from .agents.reasoner_agent import ReasonerAgent
from .agents.verifier_agent import VerifierAgent
from .agents.summarizer_agent import SummarizerAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Multi-agent orchestrator that coordinates agent execution.
    Takes user query -> Calls Planner -> Iterates Agents -> Returns Final Answer.
    """
    
    def __init__(
        self,
        message_bus: Optional[MessageBus] = None,
        llm_runner: Optional[Any] = None,
        retriever: Optional[Any] = None
    ):
        """
        Initialize orchestrator.
        
        Args:
            message_bus: Optional message bus instance
            llm_runner: Optional LLM runner instance
            retriever: Optional retriever instance
        """
        self.message_bus = message_bus or MessageBus()
        self.llm_runner = llm_runner
        self.retriever = retriever
        
        # Initialize agents
        self.agents: Dict[str, Any] = {}
        self._initialize_agents()
        
        # Conversation tracking
        self.conversations: Dict[str, AgentState] = {}
    
    def _initialize_agents(self):
        """Initialize all agents."""
        # Planner
        self.agents['planner'] = PlannerAgent(
            agent_name='planner',
            message_bus=self.message_bus,
            llm_runner=self.llm_runner
        )
        
        # Retriever
        self.agents['retriever'] = RetrieverAgent(
            agent_name='retriever',
            message_bus=self.message_bus,
            retriever=self.retriever
        )
        
        # Reasoner
        self.agents['reasoner'] = ReasonerAgent(
            agent_name='reasoner',
            message_bus=self.message_bus,
            llm_runner=self.llm_runner
        )
        
        # Verifier
        self.agents['verifier'] = VerifierAgent(
            agent_name='verifier',
            message_bus=self.message_bus
        )
        
        # Summarizer
        self.agents['summarizer'] = SummarizerAgent(
            agent_name='summarizer',
            message_bus=self.message_bus
        )
        
        logger.info(f"Initialized {len(self.agents)} agents")
    
    async def process_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent pipeline.
        
        Args:
            query: User query
            conversation_id: Optional conversation ID for tracking
            user_id: Optional user ID
            
        Returns:
            Dictionary with answer and metadata
        """
        # Create or get conversation state
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        state = AgentState(
            conversation_id=conversation_id,
            user_query=query,
            metadata={'user_id': user_id, 'start_time': datetime.utcnow()}
        )
        self.conversations[conversation_id] = state
        
        try:
            # Step 1: Planner - Generate task plan
            logger.info(f"Step 1: Planning for query: {query[:50]}...")
            plan_message = Message(
                sender="orchestrator",
                receiver="planner",
                message_type="query",
                payload={'query': query},
                correlation_id=conversation_id
            )
            
            planner_response, state = await self.agents['planner'].process(plan_message, state)
            task_plan = state.context.get('task_plan', [])
            
            if not task_plan:
                logger.warning("Planner returned empty task plan, using default")
                task_plan = [
                    {'task': 'Retrieve context', 'agent': 'retriever', 'priority': 1},
                    {'task': 'Reason about query', 'agent': 'reasoner', 'priority': 2},
                    {'task': 'Verify answer', 'agent': 'verifier', 'priority': 3},
                    {'task': 'Format response', 'agent': 'summarizer', 'priority': 4}
                ]
            
            # Step 2: Execute tasks in priority order
            sorted_tasks = sorted(task_plan, key=lambda x: x.get('priority', 5))
            
            for task in sorted_tasks:
                agent_name = task.get('agent', '').lower()
                task_desc = task.get('task', '')
                
                if agent_name not in self.agents:
                    logger.warning(f"Unknown agent: {agent_name}, skipping")
                    continue
                
                logger.info(f"Step: Executing {task_desc} with {agent_name} agent")
                
                # Create task message
                task_message = Message(
                    sender="orchestrator",
                    receiver=agent_name,
                    message_type="task",
                    payload={
                        'query': query,
                        'task': task_desc,
                        'context': state.context,
                        'intermediate_results': state.intermediate_results
                    },
                    correlation_id=conversation_id,
                    priority=task.get('priority', 5)
                )
                
                # Process with agent
                agent_response, state = await self.agents[agent_name].process(task_message, state)
                
                # Check if verification failed and needs correction
                if agent_name == 'verifier' and state.metadata.get('needs_correction', False):
                    logger.warning("Verification failed, attempting correction")
                    # Re-run reasoner with correction hint
                    correction_message = Message(
                        sender="orchestrator",
                        receiver="reasoner",
                        message_type="correction",
                        payload={
                            'query': query,
                            'previous_answer': state.context.get('reasoned_answer', ''),
                            'issues': state.metadata.get('verification_issues', [])
                        },
                        correlation_id=conversation_id
                    )
                    _, state = await self.agents['reasoner'].process(correction_message, state)
                    # Re-verify
                    verify_message = Message(
                        sender="orchestrator",
                        receiver="verifier",
                        message_type="task",
                        payload={
                            'answer': state.context.get('reasoned_answer', ''),
                            'context': state.context.get('retrieved_context', [])
                        },
                        correlation_id=conversation_id
                    )
                    _, state = await self.agents['verifier'].process(verify_message, state)
            
            # Step 3: Get final answer
            final_answer = state.final_answer
            if not final_answer:
                # Fallback: use reasoned answer
                final_answer = state.context.get('reasoned_answer', 'No answer generated')
            
            # Update metadata
            state.metadata['end_time'] = datetime.utcnow()
            state.metadata['success'] = True
            
            result = {
                'conversation_id': conversation_id,
                'query': query,
                'answer': final_answer,
                'verification': state.context.get('verification', {}),
                'metadata': state.metadata,
                'intermediate_results': state.intermediate_results
            }
            
            logger.info(f"Orchestrator completed query: {query[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            state.metadata['error'] = str(e)
            state.metadata['success'] = False
            return {
                'conversation_id': conversation_id,
                'query': query,
                'answer': f"Error processing query: {str(e)}",
                'error': str(e),
                'metadata': state.metadata
            }
    
    async def start_agents(self):
        """Start all agents."""
        for agent in self.agents.values():
            await agent.start()
        logger.info("All agents started")
    
    async def stop_agents(self):
        """Stop all agents."""
        for agent in self.agents.values():
            await agent.stop()
        logger.info("All agents stopped")
    
    def get_conversation_state(self, conversation_id: str) -> Optional[AgentState]:
        """Get conversation state by ID."""
        return self.conversations.get(conversation_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            'active_conversations': len(self.conversations),
            'agents': {name: agent.get_agent_info() for name, agent in self.agents.items()},
            'message_bus_stats': self.message_bus.get_queue_stats()
        }

