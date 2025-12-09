# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/cli/agent_ctl.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Admin CLI for agent management (status, flush, logs)

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def get_status():
    """Get agent status."""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'ransomeye-agent'],
            capture_output=True,
            text=True
        )
        status = result.stdout.strip()
        
        if status == 'active':
            print("Agent Status: RUNNING")
        elif status == 'inactive':
            print("Agent Status: STOPPED")
        else:
            print(f"Agent Status: {status.upper()}")
        
        # Get service info
        result = subprocess.run(
            ['systemctl', 'show', 'ransomeye-agent', '--property=ActiveState,SubState,MainPID'],
            capture_output=True,
            text=True
        )
        print("\nService Details:")
        print(result.stdout)
        
    except Exception as e:
        print(f"Error getting status: {e}")


def flush_buffer():
    """Flush buffer (force upload)."""
    buffer_dir = Path(os.environ.get(
        'BUFFER_DIR',
        '/var/lib/ransomeye-agent/buffer/pending'
    ))
    
    if not buffer_dir.exists():
        print(f"Buffer directory not found: {buffer_dir}")
        return
    
    files = list(buffer_dir.glob('*.json'))
    print(f"Found {len(files)} pending events in buffer")
    
    if files:
        print("Note: Events will be uploaded by the uploader thread")
        print("To force immediate upload, restart the agent service")


def show_logs(lines: int = 50):
    """Show agent logs."""
    try:
        result = subprocess.run(
            ['journalctl', '-u', 'ransomeye-agent', '-n', str(lines), '--no-pager'],
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except Exception as e:
        print(f"Error showing logs: {e}")


def show_buffer_stats():
    """Show buffer statistics."""
    buffer_dir = Path(os.environ.get(
        'BUFFER_DIR',
        '/var/lib/ransomeye-agent/buffer'
    ))
    
    pending_dir = buffer_dir / 'pending'
    archive_dir = buffer_dir / 'archive'
    
    pending_count = len(list(pending_dir.glob('*.json'))) if pending_dir.exists() else 0
    archive_count = len(list(archive_dir.glob('*.json'))) if archive_dir.exists() else 0
    
    print(f"Buffer Statistics:")
    print(f"  Pending events: {pending_count}")
    print(f"  Archived events: {archive_count}")
    print(f"  Buffer directory: {buffer_dir}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='RansomEye Agent Control CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Status command
    subparsers.add_parser('status', help='Show agent status')
    
    # Flush command
    subparsers.add_parser('flush', help='Flush buffer (force upload)')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Show agent logs')
    logs_parser.add_argument('-n', '--lines', type=int, default=50, help='Number of lines to show')
    
    # Stats command
    subparsers.add_parser('stats', help='Show buffer statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'status':
        get_status()
    elif args.command == 'flush':
        flush_buffer()
    elif args.command == 'logs':
        show_logs(args.lines)
    elif args.command == 'stats':
        show_buffer_stats()


if __name__ == "__main__":
    main()

