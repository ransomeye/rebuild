# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/multi_agent/agents/reasoner_agent.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Reasoner agent that executes Chain-of-Thought logic using LLM

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


class ReasonerAgent(BaseAgent):
    """
    Reasoner agent that performs chain-of-thought reasoning.
    Uses LLM to analyze context and generate reasoned conclusions.
    """
    
    def __init__(
        self,
        agent_name: str,
        message_bus,
        llm_runner: Optional[Any] = None
    ):
        """
        Initialize reasoner agent.
        
        Args:
            agent_name: Agent name
            message_bus: Message bus instance
            llm_runner: Optional LLM runner instance
        """
        super().__init__(
            agent_name=agent_name,
            message_bus=message_bus,
            description="Performs chain-of-thought reasoning"
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
        Process reasoning request with chain-of-thought.
        
        Args:
            message: Incoming message with context
            state: Current conversation state
            
        Returns:
            Tuple of (output_message, updated_state)
        """
        try:
            query = message.payload.get('query', state.user_query)
            context = message.payload.get('context', state.context.get('retrieved_context', []))
            
            # Perform chain-of-thought reasoning
            reasoning_result = await self._chain_of_thought(query, context)
            
            # Update state
            state.context['reasoning_steps'] = reasoning_result.get('steps', [])
            state.intermediate_results['reasoner_output'] = reasoning_result
            state.context['reasoned_answer'] = reasoning_result.get('answer', '')
            
            # Create response message
            response_message = Message(
                sender=self.agent_name,
                receiver="orchestrator",
                message_type="reasoning_result",
                payload={
                    'reasoning': reasoning_result,
                    'query': query
                },
                correlation_id=message.correlation_id or message.message_id
            )
            
            logger.info(f"Reasoner completed chain-of-thought for query: {query[:50]}...")
            return response_message, state
            
        except Exception as e:
            logger.error(f"Error in reasoner agent: {e}")
            state.metadata['reasoner_error'] = str(e)
            return None, state
    
    async def _chain_of_thought(
        self,
        query: str,
        context: List[Any]
    ) -> Dict[str, Any]:
        """
        Perform chain-of-thought reasoning.
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            Dictionary with reasoning steps and final answer
        """
        # Format context
        context_text = self._format_context(context)
        
        # Build chain-of-thought prompt
        prompt = f"""You are a security operations analyst. Analyze the following query using chain-of-thought reasoning.

Query: {query}

Context:
{context_text}

Think step by step:
1. What is the user asking?
2. What relevant information do we have from the context?
3. What are the key facts or patterns?
4. What are the possible interpretations?
5. What is the most likely answer based on the evidence?

Provide your reasoning in the following format:
Step 1: [Your first step]
Step 2: [Your second step]
...
Final Answer: [Your conclusion]

Reasoning:"""
        
        if self.llm_runner and self.llm_runner.is_available():
            response = self.llm_runner.generate(
                prompt=prompt,
                max_tokens=1024,
                temperature=0.5,
                deterministic=False
            )
            reasoning_text = response.get('text', '')
        else:
            # Fallback reasoning
            reasoning_text = f"""Step 1: Analyzing query: {query}
Step 2: Reviewing {len(context)} context items
Step 3: Identifying key patterns
Step 4: Synthesizing information
Final Answer: Based on the provided context, the analysis suggests [placeholder - LLM required for full reasoning]"""
        
        # Parse reasoning steps
        steps = self._parse_reasoning_steps(reasoning_text)
        answer = self._extract_final_answer(reasoning_text)
        
        return {
            'steps': steps,
            'answer': answer,
            'full_reasoning': reasoning_text,
            'context_used': len(context)
        }
    
    def _format_context(self, context: List[Any]) -> str:
        """Format context for prompt."""
        if not context:
            return "No context available."
        
        formatted = []
        for i, item in enumerate(context[:10], 1):  # Limit to top 10
            if hasattr(item, 'text'):
                text = item.text
                score = getattr(item, 'score', 0.0)
            elif isinstance(item, dict):
                text = item.get('text', '')
                score = item.get('score', 0.0)
            else:
                text = str(item)
                score = 0.0
            
            formatted.append(f"[{i}] (score: {score:.2f}) {text[:200]}...")
        
        return "\n".join(formatted)
    
    def _parse_reasoning_steps(self, reasoning_text: str) -> List[str]:
        """Parse reasoning steps from text."""
        steps = []
        lines = reasoning_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('Step ') or line.startswith('step '):
                steps.append(line)
            elif line and not line.startswith('Final Answer'):
                # Include other reasoning lines
                if len(steps) > 0 or ':' in line:
                    steps.append(line)
        
        return steps if steps else [reasoning_text[:500]]
    
    def _extract_final_answer(self, reasoning_text: str) -> str:
        """Extract final answer from reasoning text."""
        # Look for "Final Answer:" marker
        if 'Final Answer:' in reasoning_text:
            parts = reasoning_text.split('Final Answer:', 1)
            if len(parts) > 1:
                return parts[1].strip()
        
        # Fallback: return last paragraph
        paragraphs = reasoning_text.split('\n\n')
        if paragraphs:
            return paragraphs[-1].strip()
        
        return reasoning_text[:200]

