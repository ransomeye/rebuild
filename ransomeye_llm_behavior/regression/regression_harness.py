# Path and File Name : /home/ransomeye/rebuild/ransomeye_llm_behavior/regression/regression_harness.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Regression harness that generates synthetic test cases, runs pipeline deterministically, and compares against golden artifacts

import os
import random
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .golden_manager import GoldenManager
from .prompt_snapshot import PromptSnapshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegressionHarness:
    """
    Regression harness for golden master testing.
    Generates synthetic test cases, runs pipeline deterministically, and verifies outputs.
    """
    
    def __init__(
        self,
        golden_manager: Optional[GoldenManager] = None,
        prompt_snapshot: Optional[PromptSnapshot] = None
    ):
        """
        Initialize regression harness.
        
        Args:
            golden_manager: Golden manager instance
            prompt_snapshot: Prompt snapshot tracker
        """
        self.golden_manager = golden_manager or GoldenManager()
        self.prompt_snapshot = prompt_snapshot or PromptSnapshot()
    
    def generate_test_case(self, test_id: str = None) -> Dict:
        """
        Generate synthetic test case.
        
        Args:
            test_id: Optional test ID (generated if None)
            
        Returns:
            Test case dictionary
        """
        if test_id is None:
            test_id = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate synthetic query
        queries = [
            "Summarize the network traffic patterns observed during the incident",
            "Describe the key indicators of compromise found in the forensic analysis",
            "Explain the attack timeline and kill chain progression",
            "Identify the primary threat actor techniques and tactics",
            "Analyze the data exfiltration patterns and methods"
        ]
        
        # Generate synthetic context
        context_chunks = []
        for i in range(3):
            context_chunks.append({
                'text': f"Context chunk {i+1}: Synthetic forensic data showing suspicious activity patterns.",
                'score': 0.8 - (i * 0.1),
                'source': 'hybrid'
            })
        
        test_case = {
            'test_id': test_id,
            'query': random.choice(queries),
            'context': {
                'chunks': context_chunks,
                'total_length': sum(len(c['text']) for c in context_chunks),
                'num_chunks': len(context_chunks)
            },
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'synthetic': True
            }
        }
        
        return test_case
    
    def run_test(
        self,
        test_case: Dict,
        llm_runner,
        context_injector,
        deterministic: bool = True
    ) -> Dict:
        """
        Run test case through pipeline.
        
        Args:
            test_case: Test case dictionary
            llm_runner: LLM runner instance
            context_injector: Context injector instance
            deterministic: Whether to run in deterministic mode
            
        Returns:
            Test results
        """
        test_id = test_case['test_id']
        query = test_case['query']
        context = test_case.get('context', {})
        
        # Inject context
        context_result = context_injector.inject_context(
            query=query,
            top_k=5,
            max_context_length=2000
        )
        
        # Build prompt
        prompt = self._build_prompt(query, context_result.get('context', ''))
        
        # Run LLM (deterministic)
        llm_result = llm_runner.generate(
            prompt=prompt,
            max_tokens=512,
            deterministic=deterministic,
            seed=42 if deterministic else None
        )
        
        output = llm_result.get('text', '')
        
        return {
            'test_id': test_id,
            'input': {
                'query': query,
                'context': context
            },
            'output': output,
            'prompt': prompt,
            'deterministic': deterministic,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Build prompt from query and context."""
        if context:
            return f"Context:\n{context}\n\nQuery: {query}\n\nSummary:"
        else:
            return f"Query: {query}\n\nSummary:"
    
    def create_golden(self, test_result: Dict) -> str:
        """
        Create golden artifact from test result.
        
        Args:
            test_result: Test result dictionary
            
        Returns:
            Path to golden file
        """
        return self.golden_manager.save_golden(
            test_id=test_result['test_id'],
            input_data=test_result['input'],
            expected_output=test_result['output'],
            metadata={
                'deterministic': test_result.get('deterministic', True),
                'created_at': test_result.get('timestamp')
            }
        )
    
    def run_regression_suite(
        self,
        llm_runner,
        context_injector,
        num_tests: int = 10,
        create_goldens: bool = False
    ) -> Dict:
        """
        Run full regression test suite.
        
        Args:
            llm_runner: LLM runner instance
            context_injector: Context injector instance
            num_tests: Number of tests to run
            create_goldens: Whether to create new goldens
            
        Returns:
            Regression results
        """
        results = {
            'total_tests': num_tests,
            'passed': 0,
            'failed': 0,
            'drift_detected': 0,
            'tests': []
        }
        
        # Generate and run tests
        for i in range(num_tests):
            test_id = f"regression_test_{i+1}"
            
            # Generate test case
            test_case = self.generate_test_case(test_id)
            
            # Run test
            test_result = self.run_test(
                test_case=test_case,
                llm_runner=llm_runner,
                context_injector=context_injector,
                deterministic=True
            )
            
            # Verify against golden
            if create_goldens:
                # Create new golden
                self.create_golden(test_result)
                verification = {'valid': True, 'match': True, 'drift_detected': False}
            else:
                # Verify against existing golden
                verification = self.golden_manager.verify_output(
                    test_id=test_id,
                    actual_output=test_result['output']
                )
            
            # Record result
            test_record = {
                'test_id': test_id,
                'passed': verification.get('match', False),
                'drift_detected': verification.get('drift_detected', False),
                'verification': verification
            }
            
            results['tests'].append(test_record)
            
            if test_record['passed']:
                results['passed'] += 1
            else:
                results['failed'] += 1
                if test_record['drift_detected']:
                    results['drift_detected'] += 1
        
        logger.info(f"Regression suite completed: {results['passed']}/{results['total_tests']} passed")
        
        return results

