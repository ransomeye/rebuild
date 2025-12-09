# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/monitoring/deep_health_check.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Checks DB connection pool, disk IO, and internal queue latency

import os
import sys
import time
import subprocess
import psutil
from pathlib import Path
from typing import Dict, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool


class DeepHealthChecker:
    """Performs deep health checks on system components."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        
        # DB connection
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.db_name = os.environ.get('DB_NAME', 'ransomeye')
        self.db_user = os.environ.get('DB_USER', 'gagan')
        self.db_pass = os.environ.get('DB_PASS', 'gagan')
        
        self.db_url = f"postgresql://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    def check_disk_io(self) -> Dict:
        """Check disk I/O performance."""
        try:
            disk_io = psutil.disk_io_counters()
            disk_usage = psutil.disk_usage(str(self.rebuild_root))
            
            return {
                'success': True,
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0,
                'read_count': disk_io.read_count if disk_io else 0,
                'write_count': disk_io.write_count if disk_io else 0,
                'total_space': disk_usage.total,
                'used_space': disk_usage.used,
                'free_space': disk_usage.free,
                'percent_used': disk_usage.percent
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_db_connection_pool(self) -> Dict:
        """Check database connection pool status."""
        try:
            engine = create_engine(
                self.db_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True
            )
            
            with engine.connect() as conn:
                # Check connection
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                
                # Get pool stats
                pool = engine.pool
                
                return {
                    'success': True,
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid()
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_db_latency(self) -> Dict:
        """Check database query latency."""
        try:
            engine = create_engine(self.db_url, pool_pre_ping=True)
            
            # Simple query
            start_time = time.time()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT NOW()"))
                result.fetchone()
            simple_latency = (time.time() - start_time) * 1000  # ms
            
            # Complex query
            start_time = time.time()
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'
                """))
                result.fetchone()
            complex_latency = (time.time() - start_time) * 1000  # ms
            
            return {
                'success': True,
                'simple_query_ms': round(simple_latency, 2),
                'complex_query_ms': round(complex_latency, 2)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_queue_latency(self) -> Dict:
        """Check internal queue latency (if applicable)."""
        # This would check application-specific queues
        # For now, we'll check system load as a proxy
        try:
            load_avg = os.getloadavg()
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            return {
                'success': True,
                'load_avg_1min': load_avg[0],
                'load_avg_5min': load_avg[1],
                'load_avg_15min': load_avg[2],
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def run_health_check(self) -> Dict:
        """Run complete health check."""
        print("=" * 60)
        print("Deep Health Check")
        print("=" * 60)
        
        results = {
            'timestamp': time.time(),
            'disk_io': {},
            'db_pool': {},
            'db_latency': {},
            'queue_latency': {},
            'overall_status': 'UNKNOWN'
        }
        
        # Check disk I/O
        print("\n[1/4] Checking disk I/O...")
        disk_result = self.check_disk_io()
        results['disk_io'] = disk_result
        if disk_result.get('success'):
            print(f"  ✓ Disk usage: {disk_result.get('percent_used', 0):.1f}%")
            if disk_result.get('percent_used', 0) > 80:
                print("  ⚠ WARNING: Disk usage above 80%")
        else:
            print(f"  ✗ Disk check failed: {disk_result.get('error')}")
        
        # Check DB connection pool
        print("\n[2/4] Checking database connection pool...")
        pool_result = self.check_db_connection_pool()
        results['db_pool'] = pool_result
        if pool_result.get('success'):
            print(f"  ✓ Pool size: {pool_result.get('pool_size', 0)}")
            print(f"  ✓ Checked out: {pool_result.get('checked_out', 0)}")
        else:
            print(f"  ✗ Pool check failed: {pool_result.get('error')}")
        
        # Check DB latency
        print("\n[3/4] Checking database latency...")
        latency_result = self.check_db_latency()
        results['db_latency'] = latency_result
        if latency_result.get('success'):
            print(f"  ✓ Simple query: {latency_result.get('simple_query_ms', 0)} ms")
            print(f"  ✓ Complex query: {latency_result.get('complex_query_ms', 0)} ms")
            if latency_result.get('simple_query_ms', 0) > 100:
                print("  ⚠ WARNING: High database latency")
        else:
            print(f"  ✗ Latency check failed: {latency_result.get('error')}")
        
        # Check queue latency
        print("\n[4/4] Checking system load and queues...")
        queue_result = self.check_queue_latency()
        results['queue_latency'] = queue_result
        if queue_result.get('success'):
            print(f"  ✓ Load average (1min): {queue_result.get('load_avg_1min', 0):.2f}")
            print(f"  ✓ CPU usage: {queue_result.get('cpu_percent', 0):.1f}%")
            print(f"  ✓ Memory usage: {queue_result.get('memory_percent', 0):.1f}%")
        else:
            print(f"  ✗ Queue check failed: {queue_result.get('error')}")
        
        # Determine overall status
        all_checks_passed = all([
            disk_result.get('success', False),
            pool_result.get('success', False),
            latency_result.get('success', False),
            queue_result.get('success', False)
        ])
        
        results['overall_status'] = 'HEALTHY' if all_checks_passed else 'DEGRADED'
        
        print("\n" + "=" * 60)
        print(f"Overall Status: {results['overall_status']}")
        print("=" * 60)
        
        return results


def main():
    """Main entry point."""
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description='Perform deep health check')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    checker = DeepHealthChecker()
    results = checker.run_health_check()
    
    if args.json:
        print(json.dumps(results, indent=2))
    
    sys.exit(0 if results['overall_status'] == 'HEALTHY' else 1)


if __name__ == "__main__":
    main()

