# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant/llm/prompt_builder.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Constructs RAG prompt with context and question

from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptBuilder:
    """
    Builds RAG prompts with context and question.
    """
    
    def __init__(self):
        """Initialize prompt builder."""
        pass
    
    def build_rag_prompt(self, question: str, context_docs: List[Dict[str, Any]]) -> str:
        """
        Build RAG prompt with context and question.
        
        Args:
            question: User question
            context_docs: List of retrieved documents
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # Instruction
        prompt_parts.append("Answer the question based ONLY on the following context.")
        prompt_parts.append("If the context does not contain enough information to answer, say so.")
        prompt_parts.append("Do not make up information that is not in the context.")
        prompt_parts.append("")
        
        # Context
        prompt_parts.append("Context:")
        for i, doc in enumerate(context_docs, 1):
            doc_text = doc.get('text', '')
            prompt_parts.append(f"[Document {i}]")
            prompt_parts.append(doc_text)
            prompt_parts.append("")
        
        # Question
        prompt_parts.append("Question:")
        prompt_parts.append(question)
        prompt_parts.append("")
        prompt_parts.append("Answer:")
        
        return "\n".join(prompt_parts)

