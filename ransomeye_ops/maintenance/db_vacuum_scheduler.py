# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/maintenance/db_vacuum_scheduler.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Wraps PostgreSQL VACUUM FULL for maintenance windows

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict


class DBVacuumScheduler:
    """Schedules and executes PostgreSQL VACUUM operations."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.db_name = os.environ.get('DB_NAME', 'ransomeye')
        self.db_user = os.environ.get('DB_USER', 'gagan')
        self.db_pass = os.environ.get('DB_PASS', 'gagan')
    
    def run_vacuum_analyze(self, table_name: Optional[str] = None) -> bool:
        """Run VACUUM ANALYZE on database or specific table."""
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_pass
            
            if table_name:
                cmd = [
                    'psql',
                    '-h', self.db_host,
                    '-p', self.db_port,
                    '-U', self.db_user,
                    '-d', self.db_name,
                    '-c', f'VACUUM ANALYZE {table_name};'
                ]
                print(f"Running VACUUM ANALYZE on table: {table_name}")
            else:
                cmd = [
                    'psql',
                    '-h', self.db_host,
                    '-p', self.db_port,
                    '-U', self.db_user,
                    '-d', self.db_name,
                    '-c', 'VACUUM ANALYZE;'
                ]
                print("Running VACUUM ANALYZE on entire database...")
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            print("✓ VACUUM ANALYZE completed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ VACUUM ANALYZE failed: {e.stderr}")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    def run_vacuum_full(self, table_name: Optional[str] = None, require_maintenance_window: bool = True) -> bool:
        """Run VACUUM FULL (requires maintenance window due to table locking)."""
        if require_maintenance_window:
            print("WARNING: VACUUM FULL locks tables. Ensure maintenance window is scheduled.")
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Cancelled")
                return False
        
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_pass
            
            if table_name:
                cmd = [
                    'psql',
                    '-h', self.db_host,
                    '-p', self.db_port,
                    '-U', self.db_user,
                    '-d', self.db_name,
                    '-c', f'VACUUM FULL {table_name};'
                ]
                print(f"Running VACUUM FULL on table: {table_name}")
            else:
                cmd = [
                    'psql',
                    '-h', self.db_host,
                    '-p', self.db_port,
                    '-U', self.db_user,
                    '-d', self.db_name,
                    '-c', 'VACUUM FULL;'
                ]
                print("Running VACUUM FULL on entire database...")
                print("WARNING: This will lock all tables!")
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            print("✓ VACUUM FULL completed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ VACUUM FULL failed: {e.stderr}")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    def get_table_statistics(self) -> Dict:
        """Get table statistics to identify candidates for VACUUM."""
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_pass
            
            query = """
            SELECT 
                schemaname,
                tablename,
                n_dead_tup,
                n_live_tup,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE n_dead_tup > 0
            ORDER BY n_dead_tup DESC;
            """
            
            cmd = [
                'psql',
                '-h', self.db_host,
                '-p', self.db_port,
                '-U', self.db_user,
                '-d', self.db_name,
                '-c', query
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            print(result.stdout)
            return {'success': True, 'output': result.stdout}
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Schedule PostgreSQL VACUUM operations')
    parser.add_argument('--full', action='store_true', help='Run VACUUM FULL (requires maintenance window)')
    parser.add_argument('--analyze', action='store_true', help='Run VACUUM ANALYZE')
    parser.add_argument('--table', type=str, help='Specific table to vacuum')
    parser.add_argument('--stats', action='store_true', help='Show table statistics')
    parser.add_argument('--force', action='store_true', help='Skip maintenance window confirmation')
    
    args = parser.parse_args()
    
    scheduler = DBVacuumScheduler()
    
    if args.stats:
        scheduler.get_table_statistics()
    elif args.full:
        scheduler.run_vacuum_full(
            table_name=args.table,
            require_maintenance_window=not args.force
        )
    elif args.analyze:
        scheduler.run_vacuum_analyze(table_name=args.table)
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

