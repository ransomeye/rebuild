# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/multi_agent/agents/summarizer_agent.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Summarizer agent that formats the final response

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_agent import BaseAgent, AgentState
from ..message_bus import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SummarizerAgent(BaseAgent):
    """
    Summarizer agent that formats the final response.
    Combines reasoning, verification, and context into a coherent answer.
    """
    
    def __init__(
        self,
        agent_name: str,
        message_bus
    ):
        """
        Initialize summarizer agent.
        
        Args:
            agent_name: Agent name
            message_bus: Message bus instance
        """
        super().__init__(
            agent_name=agent_name,
            message_bus=message_bus,
            description="Formats final response from agent outputs"
        )
    
    async def process(
        self,
        message: Message,
        state: AgentState
    ) -> tuple[Optional[Message], AgentState]:
        """
        Process summarization request.
        
        Args:
            message: Incoming message with components to summarize
            state: Current conversation state
            
        Returns:
            Tuple of (output_message, updated_state)
        """
        try:
            # Gather all components
            reasoning = state.context.get('reasoned_answer', '')
            verification = state.context.get('verification', {})
            context_summary = self._summarize_context(state.context.get('retrieved_context', []))
            
            # Format final answer
            final_answer = await self._format_answer(
                query=state.user_query,
                reasoning=reasoning,
                verification=verification,
                context_summary=context_summary
            )
            
            # Update state
            state.final_answer = final_answer
            state.intermediate_results['summarizer_output'] = final_answer
            
            # Create response message
            response_message = Message(
                sender=self.agent_name,
                receiver="orchestrator",
                message_type="final_answer",
                payload={
                    'answer': final_answer,
                    'query': state.user_query,
                    'verification': verification
                },
                correlation_id=message.correlation_id or message.message_id
            )
            
            logger.info(f"Summarizer formatted final answer for query: {state.user_query[:50]}...")
            return response_message, state
            
        except Exception as e:
            logger.error(f"Error in summarizer agent: {e}")
            state.metadata['summarizer_error'] = str(e)
            # Provide fallback answer
            state.final_answer = f"Error formatting answer: {str(e)}"
            return None, state
    
    async def _format_answer(
        self,
        query: str,
        reasoning: str,
        verification: Dict[str, Any],
        context_summary: str
    ) -> str:
        """
        Format final answer from components.
        
        Args:
            query: Original query
            reasoning: Reasoning output
            verification: Verification result
            context_summary: Summary of context
            
        Returns:
            Formatted answer string
        """
        # Build answer
        answer_parts = []
        
        # Add main answer
        if reasoning:
            answer_parts.append(reasoning)
        else:
            answer_parts.append("Based on the available information, I cannot provide a complete answer at this time.")
        
        # Add verification note if needed
        if verification:
            is_valid = verification.get('is_valid', True)
            confidence = verification.get('confidence', 1.0)
            
            if not is_valid or confidence < 0.7:
                answer_parts.append(f"\n[Note: Answer confidence is {confidence:.0%}. Please verify against source data.]")
        
        # Add context summary if available
        if context_summary:
            answer_parts.append(f"\n[Context: {context_summary}]")
        
        # Combine
        final_answer = "\n".join(answer_parts)
        
        # Add footer
        footer = "\n\n© RansomEye.Tech | Support: Gagan@RansomEye.Tech"
        final_answer += footer
        
        return final_answer
    
    def _summarize_context(self, context: List[Any]) -> str:
        """
        Summarize retrieved context.
        
        Args:
            context: List of context items
            
        Returns:
            Summary string
        """
        if not context:
            return "No context retrieved"
        
        count = len(context)
        sources = set()
        
        for item in context:
            if hasattr(item, 'source'):
                sources.add(item.source)
            elif isinstance(item, dict):
                sources.add(item.get('source', 'unknown'))
        
        source_str = ', '.join(sources) if sources else 'unknown'
        return f"Retrieved {count} relevant items from {source_str}"

