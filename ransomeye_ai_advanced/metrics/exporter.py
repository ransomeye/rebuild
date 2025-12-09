# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_advanced/metrics/exporter.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prometheus metrics exporter for agent steps and governor blocks

import os
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
agent_steps_total = Counter(
    'ransomeye_agent_steps_total',
    'Total number of agent steps executed',
    ['agent_name', 'status']
)

governor_blocks_total = Counter(
    'ransomeye_governor_blocks_total',
    'Total number of requests blocked by governor',
    ['block_type']  # 'rate_limit', 'policy', 'validation'
)

agent_latency_seconds = Histogram(
    'ransomeye_agent_latency_seconds',
    'Agent execution latency',
    ['agent_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

governor_rate_limit_tokens = Gauge(
    'ransomeye_governor_rate_limit_tokens',
    'Available tokens in rate limiter',
    ['user_id']
)

conversations_active = Gauge(
    'ransomeye_conversations_active',
    'Number of active conversations'
)


def record_agent_step(agent_name: str, status: str = 'success'):
    """
    Record an agent step.
    
    Args:
        agent_name: Name of agent
        status: 'success' or 'error'
    """
    agent_steps_total.labels(agent_name=agent_name, status=status).inc()


def record_governor_block(block_type: str):
    """
    Record a governor block.
    
    Args:
        block_type: 'rate_limit', 'policy', or 'validation'
    """
    governor_blocks_total.labels(block_type=block_type).inc()


def record_agent_latency(agent_name: str, duration: float):
    """
    Record agent execution latency.
    
    Args:
        agent_name: Name of agent
        duration: Duration in seconds
    """
    agent_latency_seconds.labels(agent_name=agent_name).observe(duration)


def update_rate_limit_tokens(user_id: str, tokens: float):
    """
    Update rate limit tokens gauge.
    
    Args:
        user_id: User ID
        tokens: Available tokens
    """
    governor_rate_limit_tokens.labels(user_id=user_id).set(tokens)


def update_active_conversations(count: int):
    """
    Update active conversations gauge.
    
    Args:
        count: Number of active conversations
    """
    conversations_active.set(count)


def setup_metrics_endpoint(app, port: int = None):
    """
    Setup Prometheus metrics endpoint.
    
    Args:
        app: FastAPI app (optional)
        port: Metrics port (from AI_METRICS_PORT env var)
    """
    metrics_port = port or int(os.environ.get('AI_METRICS_PORT', 9100))
    
    try:
        start_http_server(metrics_port)
        logger.info(f"Prometheus metrics server started on port {metrics_port}")
    except Exception as e:
        logger.error(f"Error starting metrics server: {e}")


def get_metrics_summary() -> Dict[str, Any]:
    """Get metrics summary."""
    return {
        'agent_steps': 'See agent_steps_total metric',
        'governor_blocks': 'See governor_blocks_total metric',
        'agent_latency': 'See agent_latency_seconds metric',
        'rate_limit_tokens': 'See governor_rate_limit_tokens metric',
        'active_conversations': 'See conversations_active metric'
    }

