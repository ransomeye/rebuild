# Path and File Name : /home/ransomeye/rebuild/ransomeye_linux_agent/cli/inspect_buffer.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Debug tool to read and inspect buffer files

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def inspect_file(file_path: Path, pretty: bool = True):
    """Inspect a single buffer file."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        print(f"\nFile: {file_path.name}")
        print(f"Size: {file_path.stat().st_size} bytes")
        print(f"Modified: {datetime.fromtimestamp(file_path.stat().st_mtime)}")
        print("\nContent:")
        
        if pretty:
            print(json.dumps(data, indent=2))
        else:
            print(json.dumps(data))
    
    except Exception as e:
        print(f"Error reading file: {e}")


def list_files(buffer_dir: Path, limit: int = 10):
    """List buffer files."""
    pending_dir = buffer_dir / 'pending'
    archive_dir = buffer_dir / 'archive'
    
    print("Pending Events:")
    if pending_dir.exists():
        files = sorted(pending_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        for i, file_path in enumerate(files[:limit], 1):
            size = file_path.stat().st_size
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(f"  {i}. {file_path.name} ({size} bytes, {mtime})")
    else:
        print("  No pending events")
    
    print("\nArchived Events:")
    if archive_dir.exists():
        files = sorted(archive_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        for i, file_path in enumerate(files[:limit], 1):
            size = file_path.stat().st_size
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(f"  {i}. {file_path.name} ({size} bytes, {mtime})")
    else:
        print("  No archived events")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Inspect agent buffer files')
    parser.add_argument('file', nargs='?', help='Specific file to inspect')
    parser.add_argument('-d', '--dir', help='Buffer directory', 
                       default='/var/lib/ransomeye-agent/buffer')
    parser.add_argument('-l', '--list', action='store_true', help='List buffer files')
    parser.add_argument('-n', '--limit', type=int, default=10, help='Limit for list')
    parser.add_argument('--compact', action='store_true', help='Compact JSON output')
    
    args = parser.parse_args()
    
    buffer_dir = Path(args.dir)
    
    if args.list or not args.file:
        list_files(buffer_dir, args.limit)
    else:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            # Try in pending and archive directories
            pending_path = buffer_dir / 'pending' / file_path
            archive_path = buffer_dir / 'archive' / file_path
            
            if pending_path.exists():
                file_path = pending_path
            elif archive_path.exists():
                file_path = archive_path
            else:
                print(f"File not found: {file_path}")
                return
        
        inspect_file(file_path, pretty=not args.compact)


if __name__ == "__main__":
    main()

