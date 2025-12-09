# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/tools/bench_pipeline.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Performance benchmark tool for the multi-agent pipeline

import os
import sys
import asyncio
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..multi_agent.orchestrator import MultiAgentOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineBenchmark:
    """
    Benchmark tool for multi-agent pipeline performance.
    """
    
    def __init__(self, orchestrator: MultiAgentOrchestrator):
        """
        Initialize benchmark.
        
        Args:
            orchestrator: Multi-agent orchestrator instance
        """
        self.orchestrator = orchestrator
    
    async def benchmark_query(
        self,
        query: str,
        iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Benchmark a single query.
        
        Args:
            query: Query to benchmark
            iterations: Number of iterations
            
        Returns:
            Benchmark results
        """
        latencies = []
        successes = 0
        
        for i in range(iterations):
            start_time = time.time()
            try:
                result = await self.orchestrator.process_query(query)
                latency = time.time() - start_time
                latencies.append(latency)
                if result.get('answer'):
                    successes += 1
            except Exception as e:
                logger.error(f"Error in iteration {i}: {e}")
                latencies.append(None)
        
        # Calculate statistics
        valid_latencies = [l for l in latencies if l is not None]
        
        if not valid_latencies:
            return {
                'query': query,
                'iterations': iterations,
                'successes': 0,
                'error': 'All iterations failed'
            }
        
        return {
            'query': query,
            'iterations': iterations,
            'successes': successes,
            'success_rate': successes / iterations,
            'latency': {
                'mean': sum(valid_latencies) / len(valid_latencies),
                'min': min(valid_latencies),
                'max': max(valid_latencies),
                'p50': sorted(valid_latencies)[len(valid_latencies) // 2],
                'p95': sorted(valid_latencies)[int(len(valid_latencies) * 0.95)],
                'p99': sorted(valid_latencies)[int(len(valid_latencies) * 0.99)]
            },
            'all_latencies': valid_latencies
        }
    
    async def benchmark_suite(
        self,
        queries: List[str],
        iterations_per_query: int = 10
    ) -> Dict[str, Any]:
        """
        Benchmark a suite of queries.
        
        Args:
            queries: List of queries
            iterations_per_query: Iterations per query
            
        Returns:
            Suite benchmark results
        """
        results = []
        
        for query in queries:
            logger.info(f"Benchmarking query: {query[:50]}...")
            result = await self.benchmark_query(query, iterations_per_query)
            results.append(result)
        
        # Aggregate statistics
        all_latencies = []
        total_successes = 0
        total_iterations = 0
        
        for result in results:
            if 'latency' in result:
                all_latencies.extend(result['all_latencies'])
                total_successes += result['successes']
                total_iterations += result['iterations']
        
        summary = {
            'total_queries': len(queries),
            'total_iterations': total_iterations,
            'total_successes': total_successes,
            'overall_success_rate': total_successes / total_iterations if total_iterations > 0 else 0.0,
            'overall_latency': {
                'mean': sum(all_latencies) / len(all_latencies) if all_latencies else 0,
                'min': min(all_latencies) if all_latencies else 0,
                'max': max(all_latencies) if all_latencies else 0
            },
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return summary
    
    def save_results(self, results: Dict[str, Any], output_path: Optional[str] = None):
        """Save benchmark results."""
        if not output_path:
            output_path = str(
                Path(__file__).parent.parent / 'logs' / f"benchmark_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Saved benchmark results to {output_path}")


def main():
    """Main benchmark script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Benchmark multi-agent pipeline')
    parser.add_argument('--query', type=str, help='Single query to benchmark')
    parser.add_argument('--queries-file', type=str, help='File with queries (one per line)')
    parser.add_argument('--iterations', type=int, default=10, help='Iterations per query')
    parser.add_argument('--output', type=str, help='Output file for results')
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = MultiAgentOrchestrator()
    benchmark = PipelineBenchmark(orchestrator)
    
    if args.query:
        # Single query
        result = asyncio.run(benchmark.benchmark_query(args.query, args.iterations))
        print(json.dumps(result, indent=2))
    else:
        # Load queries
        queries = []
        if args.queries_file and os.path.exists(args.queries_file):
            with open(args.queries_file, 'r') as f:
                queries = [line.strip() for line in f if line.strip()]
        else:
            queries = [
                "What is the status of the security system?",
                "Show me recent authentication failures",
                "Analyze network traffic patterns"
            ]
        
        # Run suite
        results = asyncio.run(benchmark.benchmark_suite(queries, args.iterations))
        
        if args.output:
            benchmark.save_results(results, args.output)
        else:
            print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

