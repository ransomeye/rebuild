# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/tuning/postgres_tuner.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generates postgresql.conf suggestions based on hardware

import os
import sys
import psutil
import math
from pathlib import Path
from typing import Dict


class PostgresTuner:
    """Generates PostgreSQL configuration recommendations."""
    
    def __init__(self):
        self.cpu_count = psutil.cpu_count(logical=True)
        self.memory_total_gb = psutil.virtual_memory().total / (1024**3)
        self.disk_io = psutil.disk_io_counters()
    
    def calculate_shared_buffers(self) -> str:
        """Calculate shared_buffers (typically 25% of RAM)."""
        shared_buffers_gb = max(1, int(self.memory_total_gb * 0.25))
        return f"{shared_buffers_gb}GB"
    
    def calculate_effective_cache_size(self) -> str:
        """Calculate effective_cache_size (typically 50-75% of RAM)."""
        effective_cache_gb = max(2, int(self.memory_total_gb * 0.6))
        return f"{effective_cache_gb}GB"
    
    def calculate_work_mem(self) -> str:
        """Calculate work_mem based on connections and RAM."""
        # Assume max_connections = 100
        max_connections = 100
        work_mem_mb = int((self.memory_total_gb * 1024 * 0.25) / max_connections)
        work_mem_mb = max(4, min(work_mem_mb, 256))  # Between 4MB and 256MB
        return f"{work_mem_mb}MB"
    
    def calculate_maintenance_work_mem(self) -> str:
        """Calculate maintenance_work_mem (typically 10% of RAM)."""
        maint_work_mem_gb = max(1, int(self.memory_total_gb * 0.1))
        return f"{maint_work_mem_gb}GB"
    
    def calculate_max_connections(self) -> int:
        """Calculate max_connections based on resources."""
        # Base on CPU and memory
        base_connections = self.cpu_count * 10
        memory_connections = int(self.memory_total_gb * 20)
        
        # Reasonable range
        max_conn = min(base_connections, memory_connections, 200)
        return max(50, max_conn)
    
    def generate_postgresql_conf(self, output_path: Path) -> bool:
        """Generate PostgreSQL configuration file."""
        try:
            config_lines = [
                "# Auto-generated PostgreSQL configuration",
                f"# Generated based on system resources:",
                f"#   CPU cores: {self.cpu_count}",
                f"#   Total memory: {self.memory_total_gb:.2f} GB",
                "",
                "# Memory Settings",
                f"shared_buffers = {self.calculate_shared_buffers()}",
                f"effective_cache_size = {self.calculate_effective_cache_size()}",
                f"work_mem = {self.calculate_work_mem()}",
                f"maintenance_work_mem = {self.calculate_maintenance_work_mem()}",
                "",
                "# Connection Settings",
                f"max_connections = {self.calculate_max_connections()}",
                "",
                "# Checkpoint Settings",
                "checkpoint_completion_target = 0.9",
                "wal_buffers = 16MB",
                "default_statistics_target = 100",
                "",
                "# Query Planner",
                "random_page_cost = 1.1",
                "effective_io_concurrency = 200",
                "",
                "# Logging",
                "log_destination = 'stderr'",
                "logging_collector = on",
                "log_directory = 'log'",
                "log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'",
                "log_rotation_age = 1d",
                "log_rotation_size = 100MB",
                "log_min_duration_statement = 1000",
                "log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '",
                "",
                "# Autovacuum",
                "autovacuum = on",
                "autovacuum_max_workers = 3",
                "autovacuum_naptime = 1min",
            ]
            
            with open(output_path, 'w') as f:
                f.write('\n'.join(config_lines))
            
            return True
        except Exception as e:
            print(f"Error writing config: {e}")
            return False
    
    def print_recommendations(self) -> None:
        """Print PostgreSQL tuning recommendations."""
        print("=" * 60)
        print("PostgreSQL Tuning Recommendations")
        print("=" * 60)
        
        print(f"\nSystem Resources:")
        print(f"  CPU cores: {self.cpu_count}")
        print(f"  Total memory: {self.memory_total_gb:.2f} GB")
        
        print(f"\nRecommended Settings:")
        print(f"  shared_buffers = {self.calculate_shared_buffers()}")
        print(f"  effective_cache_size = {self.calculate_effective_cache_size()}")
        print(f"  work_mem = {self.calculate_work_mem()}")
        print(f"  maintenance_work_mem = {self.calculate_maintenance_work_mem()}")
        print(f"  max_connections = {self.calculate_max_connections()}")
        
        print("\n" + "=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate PostgreSQL configuration recommendations')
    parser.add_argument('--output', type=str, help='Generate postgresql.conf file')
    
    args = parser.parse_args()
    
    tuner = PostgresTuner()
    tuner.print_recommendations()
    
    if args.output:
        tuner.generate_postgresql_conf(Path(args.output))
        print(f"\n✓ Configuration written to: {args.output}")
        print("WARNING: Review and test before applying to production!")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

