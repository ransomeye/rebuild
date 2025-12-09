# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/multi_agent/agents/planner_agent.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Planner agent that breaks complex queries into sub-tasks

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_agent import BaseAgent, AgentState
from ..message_bus import Message

# Try to import LLM runner
try:
    from ransomeye_llm_behavior.llm_core.llm_runner import LLMRunner
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Planner agent that breaks complex queries into a list of sub-tasks.
    Uses LLM to analyze the query and generate a task plan.
    """
    
    def __init__(
        self,
        agent_name: str,
        message_bus,
        llm_runner: Optional[Any] = None
    ):
        """
        Initialize planner agent.
        
        Args:
            agent_name: Agent name
            message_bus: Message bus instance
            llm_runner: Optional LLM runner instance
        """
        super().__init__(
            agent_name=agent_name,
            message_bus=message_bus,
            description="Breaks complex queries into sub-tasks"
        )
        self.llm_runner = llm_runner
        if not self.llm_runner and LLM_AVAILABLE:
            model_path = os.environ.get('LLM_MODEL_PATH')
            if model_path:
                self.llm_runner = LLMRunner(model_path=model_path)
    
    async def process(
        self,
        message: Message,
        state: AgentState
    ) -> tuple[Optional[Message], AgentState]:
        """
        Process query and generate task plan.
        
        Args:
            message: Incoming message with user query
            state: Current conversation state
            
        Returns:
            Tuple of (output_message, updated_state)
        """
        try:
            user_query = message.payload.get('query', state.user_query)
            
            # Generate task plan using LLM or rule-based fallback
            task_plan = await self._generate_task_plan(user_query)
            
            # Update state
            state.context['task_plan'] = task_plan
            state.intermediate_results['planner_output'] = task_plan
            
            # Create response message
            response_message = Message(
                sender=self.agent_name,
                receiver="orchestrator",
                message_type="task_plan",
                payload={
                    'task_plan': task_plan,
                    'query': user_query
                },
                correlation_id=message.correlation_id or message.message_id
            )
            
            logger.info(f"Planner generated {len(task_plan)} tasks for query: {user_query[:50]}...")
            return response_message, state
            
        except Exception as e:
            logger.error(f"Error in planner agent: {e}")
            state.metadata['planner_error'] = str(e)
            return None, state
    
    async def _generate_task_plan(self, query: str) -> List[Dict[str, Any]]:
        """
        Generate task plan from query.
        
        Args:
            query: User query
            
        Returns:
            List of task dictionaries with 'task', 'agent', 'priority'
        """
        # Use LLM if available
        if self.llm_runner and self.llm_runner.is_available():
            return await self._llm_plan(query)
        else:
            return await self._rule_based_plan(query)
    
    async def _llm_plan(self, query: str) -> List[Dict[str, Any]]:
        """Generate plan using LLM."""
        prompt = f"""Analyze the following security operations query and break it down into specific sub-tasks.
Each sub-task should be assigned to an appropriate agent: 'retriever', 'reasoner', 'verifier', or 'summarizer'.

Query: {query}

Respond in JSON format with a list of tasks, each with:
- "task": description of the task
- "agent": which agent should handle it ("retriever", "reasoner", "verifier", "summarizer")
- "priority": integer (1=highest, 5=lowest)

Example format:
[
  {{"task": "Retrieve relevant logs and threat intelligence", "agent": "retriever", "priority": 1}},
  {{"task": "Analyze the correlation between events", "agent": "reasoner", "priority": 2}},
  {{"task": "Verify the analysis against known patterns", "agent": "verifier", "priority": 3}}
]

JSON response:"""
        
        try:
            response = self.llm_runner.generate(
                prompt=prompt,
                max_tokens=512,
                temperature=0.3,
                deterministic=False
            )
            
            # Parse JSON from response
            import json
            import re
            
            text = response.get('text', '')
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                task_plan = json.loads(json_match.group())
                return task_plan
            else:
                logger.warning("Could not parse JSON from LLM response, using rule-based fallback")
                return await self._rule_based_plan(query)
                
        except Exception as e:
            logger.error(f"Error in LLM planning: {e}")
            return await self._rule_based_plan(query)
    
    async def _rule_based_plan(self, query: str) -> List[Dict[str, Any]]:
        """Generate plan using rule-based heuristics."""
        query_lower = query.lower()
        tasks = []
        
        # Check for retrieval needs
        if any(keyword in query_lower for keyword in ['find', 'search', 'retrieve', 'get', 'show', 'list']):
            tasks.append({
                'task': 'Retrieve relevant information from knowledge base',
                'agent': 'retriever',
                'priority': 1
            })
        
        # Check for reasoning needs
        if any(keyword in query_lower for keyword in ['analyze', 'explain', 'why', 'how', 'correlate', 'compare']):
            tasks.append({
                'task': 'Perform chain-of-thought reasoning',
                'agent': 'reasoner',
                'priority': 2
            })
        
        # Always verify
        tasks.append({
            'task': 'Verify answer against context',
            'agent': 'verifier',
            'priority': 3
        })
        
        # Always summarize
        tasks.append({
            'task': 'Format final response',
            'agent': 'summarizer',
            'priority': 4
        })
        
        return tasks

