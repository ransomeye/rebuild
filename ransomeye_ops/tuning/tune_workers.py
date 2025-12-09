# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/tuning/tune_workers.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Auto-calculates Gunicorn/Celery workers based on available RAM/CPU

import os
import sys
import psutil
import math
from pathlib import Path
from typing import Dict


class WorkerTuner:
    """Calculates optimal worker counts for Gunicorn/Celery."""
    
    def __init__(self):
        self.cpu_count = psutil.cpu_count(logical=True)
        self.memory_total_gb = psutil.virtual_memory().total / (1024**3)
        
        # Default memory per worker (GB)
        self.memory_per_worker_gb = float(os.environ.get('MEMORY_PER_WORKER_GB', '0.5'))
        self.memory_per_celery_worker_gb = float(os.environ.get('MEMORY_PER_CELERY_WORKER_GB', '0.3'))
    
    def calculate_gunicorn_workers(self) -> Dict:
        """Calculate optimal Gunicorn worker count."""
        # Formula: (2 * CPU cores) + 1 (common Gunicorn recommendation)
        workers_by_cpu = (2 * self.cpu_count) + 1
        
        # Also consider memory: total_memory / memory_per_worker
        workers_by_memory = int(self.memory_total_gb / self.memory_per_worker_gb)
        
        # Take the minimum to avoid over-allocation
        optimal_workers = min(workers_by_cpu, workers_by_memory)
        
        # Minimum 2, maximum reasonable limit
        optimal_workers = max(2, min(optimal_workers, 32))
        
        return {
            'optimal': optimal_workers,
            'by_cpu': workers_by_cpu,
            'by_memory': workers_by_memory,
            'cpu_count': self.cpu_count,
            'memory_total_gb': round(self.memory_total_gb, 2),
            'memory_per_worker_gb': self.memory_per_worker_gb
        }
    
    def calculate_celery_workers(self) -> Dict:
        """Calculate optimal Celery worker count."""
        # Celery workers can be more numerous but lighter
        workers_by_cpu = self.cpu_count * 2
        
        workers_by_memory = int(self.memory_total_gb / self.memory_per_celery_worker_gb)
        
        optimal_workers = min(workers_by_cpu, workers_by_memory)
        
        # Minimum 1, reasonable maximum
        optimal_workers = max(1, min(optimal_workers, 64))
        
        return {
            'optimal': optimal_workers,
            'by_cpu': workers_by_cpu,
            'by_memory': workers_by_memory,
            'cpu_count': self.cpu_count,
            'memory_total_gb': round(self.memory_total_gb, 2),
            'memory_per_worker_gb': self.memory_per_celery_worker_gb
        }
    
    def generate_gunicorn_config(self, output_path: Path) -> bool:
        """Generate Gunicorn configuration file."""
        gunicorn_config = self.calculate_gunicorn_workers()
        
        config_content = f"""# Auto-generated Gunicorn configuration
# Generated based on system resources:
#   CPU cores: {gunicorn_config['cpu_count']}
#   Total memory: {gunicorn_config['memory_total_gb']} GB
#   Memory per worker: {gunicorn_config['memory_per_worker_gb']} GB

workers = {gunicorn_config['optimal']}
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8000"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
"""
        
        try:
            with open(output_path, 'w') as f:
                f.write(config_content)
            return True
        except Exception as e:
            print(f"Error writing config: {e}")
            return False
    
    def generate_celery_config(self, output_path: Path) -> bool:
        """Generate Celery configuration."""
        celery_config = self.calculate_celery_workers()
        
        config_content = f"""# Auto-generated Celery configuration
# Generated based on system resources:
#   CPU cores: {celery_config['cpu_count']}
#   Total memory: {celery_config['memory_total_gb']} GB
#   Memory per worker: {celery_config['memory_per_worker_gb']} GB

worker_concurrency = {celery_config['optimal']}
worker_max_tasks_per_child = 1000
worker_prefetch_multiplier = 4
task_acks_late = True
task_reject_on_worker_lost = True
"""
        
        try:
            with open(output_path, 'w') as f:
                f.write(config_content)
            return True
        except Exception as e:
            print(f"Error writing config: {e}")
            return False
    
    def print_recommendations(self) -> None:
        """Print worker tuning recommendations."""
        print("=" * 60)
        print("Worker Tuning Recommendations")
        print("=" * 60)
        
        print(f"\nSystem Resources:")
        print(f"  CPU cores (logical): {self.cpu_count}")
        print(f"  Total memory: {self.memory_total_gb:.2f} GB")
        
        # Gunicorn
        gunicorn_config = self.calculate_gunicorn_workers()
        print(f"\nGunicorn Workers:")
        print(f"  Recommended: {gunicorn_config['optimal']}")
        print(f"    Based on CPU: {gunicorn_config['by_cpu']}")
        print(f"    Based on memory: {gunicorn_config['by_memory']}")
        
        # Celery
        celery_config = self.calculate_celery_workers()
        print(f"\nCelery Workers:")
        print(f"  Recommended: {celery_config['optimal']}")
        print(f"    Based on CPU: {celery_config['by_cpu']}")
        print(f"    Based on memory: {celery_config['by_memory']}")
        
        print("\n" + "=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate optimal worker counts')
    parser.add_argument('--gunicorn-config', type=str, help='Generate Gunicorn config file')
    parser.add_argument('--celery-config', type=str, help='Generate Celery config file')
    
    args = parser.parse_args()
    
    tuner = WorkerTuner()
    tuner.print_recommendations()
    
    if args.gunicorn_config:
        tuner.generate_gunicorn_config(Path(args.gunicorn_config))
        print(f"✓ Gunicorn config written to: {args.gunicorn_config}")
    
    if args.celery_config:
        tuner.generate_celery_config(Path(args.celery_config))
        print(f"✓ Celery config written to: {args.celery_config}")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

