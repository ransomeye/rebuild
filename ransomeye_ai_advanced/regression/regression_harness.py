# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/regression/regression_harness.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Golden Master test engine that runs deterministic queries and compares output hashes

import os
import sys
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .golden_manager import GoldenManager
from ..multi_agent.orchestrator import MultiAgentOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegressionHarness:
    """
    Regression test harness using Golden Master pattern.
    Runs deterministic queries and compares outputs against reference.
    """
    
    def __init__(
        self,
        orchestrator: Optional[MultiAgentOrchestrator] = None,
        golden_manager: Optional[GoldenManager] = None
    ):
        """
        Initialize regression harness.
        
        Args:
            orchestrator: Multi-agent orchestrator instance
            golden_manager: Golden manager instance
        """
        self.orchestrator = orchestrator
        self.golden_manager = golden_manager or GoldenManager()
        
        # Test queries (deterministic)
        self.test_queries = [
            "What is the status of the security system?",
            "Show me recent authentication failures",
            "Analyze network traffic patterns",
            "What threats were detected in the last hour?",
            "Summarize the latest security incidents"
        ]
    
    async def run_test(
        self,
        query: str,
        create_golden: bool = False
    ) -> Dict[str, Any]:
        """
        Run a single regression test.
        
        Args:
            query: Test query
            create_golden: If True, create golden master instead of comparing
            
        Returns:
            Test result
        """
        if not self.orchestrator:
            return {
                'success': False,
                'error': 'Orchestrator not initialized'
            }
        
        try:
            # Run query
            result = await self.orchestrator.process_query(query)
            
            # Extract output for comparison
            output = {
                'answer': result.get('answer', ''),
                'verification': result.get('verification', {}),
                'metadata': result.get('metadata', {})
            }
            
            # Hash the answer for deterministic comparison
            answer_hash = hashlib.sha256(result.get('answer', '').encode()).hexdigest()
            output['answer_hash'] = answer_hash
            
            if create_golden:
                # Save as golden master
                self.golden_manager.save_golden(
                    query=query,
                    expected_output=output,
                    metadata={'created_by': 'regression_harness'}
                )
                return {
                    'success': True,
                    'action': 'golden_created',
                    'query': query,
                    'output_hash': answer_hash
                }
            else:
                # Compare against golden master
                comparison = self.golden_manager.compare_output(query, output)
                
                return {
                    'success': comparison['match'],
                    'action': 'compared',
                    'query': query,
                    'match': comparison['match'],
                    'differences': comparison.get('differences', []),
                    'output_hash': answer_hash
                }
                
        except Exception as e:
            logger.error(f"Error in regression test: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query
            }
    
    async def run_suite(
        self,
        queries: Optional[List[str]] = None,
        create_golden: bool = False
    ) -> Dict[str, Any]:
        """
        Run full regression test suite.
        
        Args:
            queries: Optional list of queries (uses default if None)
            create_golden: If True, create golden masters
            
        Returns:
            Test suite results
        """
        queries = queries or self.test_queries
        
        logger.info(f"Running regression test suite with {len(queries)} queries...")
        
        results = []
        for query in queries:
            result = await self.run_test(query, create_golden=create_golden)
            results.append(result)
        
        # Summary
        passed = sum(1 for r in results if r.get('success', False))
        total = len(results)
        
        summary = {
            'total_tests': total,
            'passed': passed,
            'failed': total - passed,
            'success_rate': passed / total if total > 0 else 0.0,
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Regression suite complete: {passed}/{total} passed")
        return summary
    
    def save_results(self, results: Dict[str, Any], output_path: Optional[str] = None):
        """
        Save test results to file.
        
        Args:
            results: Test results
            output_path: Optional output path
        """
        if not output_path:
            output_path = str(
                Path(__file__).parent.parent / 'logs' / f"regression_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Saved regression results to {output_path}")


def main():
    """Main script for regression testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run regression tests')
    parser.add_argument('--create-golden', action='store_true', help='Create golden masters')
    parser.add_argument('--query', type=str, help='Single query to test')
    parser.add_argument('--queries-file', type=str, help='File with queries (one per line)')
    parser.add_argument('--output', type=str, help='Output file for results')
    
    args = parser.parse_args()
    
    # Initialize orchestrator (would need proper setup in production)
    orchestrator = MultiAgentOrchestrator()
    
    harness = RegressionHarness(orchestrator=orchestrator)
    
    if args.query:
        # Single query
        result = asyncio.run(harness.run_test(args.query, create_golden=args.create_golden))
        print(json.dumps(result, indent=2))
    else:
        # Load queries if file provided
        queries = None
        if args.queries_file and os.path.exists(args.queries_file):
            with open(args.queries_file, 'r') as f:
                queries = [line.strip() for line in f if line.strip()]
        
        # Run suite
        results = asyncio.run(harness.run_suite(queries=queries, create_golden=args.create_golden))
        
        if args.output:
            harness.save_results(results, args.output)
        else:
            print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

