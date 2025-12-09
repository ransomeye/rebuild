# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/maintenance/disk_cleaner.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Prunes temporary files and orphaned chunks in buffer directories

import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict


class DiskCleaner:
    """Cleans up temporary files and orphaned data."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        self.buffer_dir = Path(os.environ.get('BUFFER_DIR', str(self.rebuild_root / 'buffers')))
        self.temp_dir = self.rebuild_root / 'tmp'
        
        # Age thresholds (days)
        self.temp_file_age = int(os.environ.get('TEMP_FILE_AGE_DAYS', '7'))
        self.orphan_chunk_age = int(os.environ.get('ORPHAN_CHUNK_AGE_DAYS', '30'))
    
    def get_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes."""
        total = 0
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
        except Exception:
            pass
        return total
    
    def clean_temp_files(self, dry_run: bool = False) -> Dict[str, int]:
        """Clean temporary files older than threshold."""
        if not self.temp_dir.exists():
            return {'removed': 0, 'freed_bytes': 0}
        
        cutoff_time = datetime.now() - timedelta(days=self.temp_file_age)
        cutoff_timestamp = cutoff_time.timestamp()
        
        removed = 0
        freed_bytes = 0
        
        print(f"Cleaning temporary files older than {self.temp_file_age} days...")
        
        for temp_file in self.temp_dir.rglob('*'):
            if not temp_file.is_file():
                continue
            
            file_mtime = temp_file.stat().st_mtime
            if file_mtime < cutoff_timestamp:
                file_size = temp_file.stat().st_size
                
                if dry_run:
                    print(f"  [DRY RUN] Would remove: {temp_file.relative_to(self.temp_dir)} ({file_size} bytes)")
                else:
                    try:
                        temp_file.unlink()
                        print(f"  ✓ Removed: {temp_file.name} ({file_size} bytes)")
                        removed += 1
                        freed_bytes += file_size
                    except Exception as e:
                        print(f"  ✗ Failed to remove {temp_file}: {e}")
        
        return {'removed': removed, 'freed_bytes': freed_bytes}
    
    def find_orphaned_chunks(self) -> List[Path]:
        """Find orphaned chunks in buffer directory."""
        orphaned = []
        
        if not self.buffer_dir.exists():
            return orphaned
        
        cutoff_time = datetime.now() - timedelta(days=self.orphan_chunk_age)
        cutoff_timestamp = cutoff_time.timestamp()
        
        # Look for chunk files (common patterns: *.chunk, *.part, *.tmp)
        chunk_patterns = ['*.chunk', '*.part', '*.tmp', '*.buffer']
        
        for pattern in chunk_patterns:
            for chunk_file in self.buffer_dir.rglob(pattern):
                if chunk_file.is_file():
                    file_mtime = chunk_file.stat().st_mtime
                    if file_mtime < cutoff_timestamp:
                        orphaned.append(chunk_file)
        
        return orphaned
    
    def clean_orphaned_chunks(self, dry_run: bool = False) -> Dict[str, int]:
        """Remove orphaned chunks from buffer directory."""
        orphaned = self.find_orphaned_chunks()
        
        if not orphaned:
            print("No orphaned chunks found")
            return {'removed': 0, 'freed_bytes': 0}
        
        print(f"Found {len(orphaned)} orphaned chunks...")
        
        removed = 0
        freed_bytes = 0
        
        for chunk_file in orphaned:
            file_size = chunk_file.stat().st_size
            
            if dry_run:
                print(f"  [DRY RUN] Would remove: {chunk_file.relative_to(self.buffer_dir)} ({file_size} bytes)")
            else:
                try:
                    chunk_file.unlink()
                    print(f"  ✓ Removed orphaned chunk: {chunk_file.name} ({file_size} bytes)")
                    removed += 1
                    freed_bytes += file_size
                except Exception as e:
                    print(f"  ✗ Failed to remove {chunk_file}: {e}")
        
        return {'removed': removed, 'freed_bytes': freed_bytes}
    
    def clean_empty_directories(self, dry_run: bool = False) -> int:
        """Remove empty directories."""
        removed = 0
        
        # Start from deepest directories
        directories = []
        for root, dirs, files in os.walk(self.buffer_dir):
            for d in dirs:
                directories.append(Path(root) / d)
        
        # Sort by depth (deepest first)
        directories.sort(key=lambda p: len(p.parts), reverse=True)
        
        for directory in directories:
            try:
                if not any(directory.iterdir()):  # Empty directory
                    if dry_run:
                        print(f"  [DRY RUN] Would remove empty directory: {directory.relative_to(self.buffer_dir)}")
                    else:
                        directory.rmdir()
                        print(f"  ✓ Removed empty directory: {directory.relative_to(self.buffer_dir)}")
                        removed += 1
            except Exception:
                pass
        
        return removed
    
    def run_cleanup(self, dry_run: bool = False) -> Dict:
        """Run complete cleanup."""
        print("=" * 60)
        print("Disk Cleanup")
        print("=" * 60)
        
        results = {
            'temp_files': {'removed': 0, 'freed_bytes': 0},
            'orphaned_chunks': {'removed': 0, 'freed_bytes': 0},
            'empty_dirs': 0,
            'total_freed_bytes': 0
        }
        
        # Clean temp files
        temp_results = self.clean_temp_files(dry_run=dry_run)
        results['temp_files'] = temp_results
        
        # Clean orphaned chunks
        chunk_results = self.clean_orphaned_chunks(dry_run=dry_run)
        results['orphaned_chunks'] = chunk_results
        
        # Clean empty directories
        if not dry_run:
            results['empty_dirs'] = self.clean_empty_directories(dry_run=dry_run)
        
        # Calculate total
        results['total_freed_bytes'] = (
            temp_results['freed_bytes'] + chunk_results['freed_bytes']
        )
        
        print("\n" + "=" * 60)
        print("Cleanup Summary")
        print("=" * 60)
        print(f"Temp files removed: {temp_results['removed']}")
        print(f"Orphaned chunks removed: {chunk_results['removed']}")
        print(f"Empty directories removed: {results['empty_dirs']}")
        print(f"Total space freed: {results['total_freed_bytes'] / (1024*1024):.2f} MB")
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up temporary files and orphaned chunks')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be cleaned without doing it')
    
    args = parser.parse_args()
    
    cleaner = DiskCleaner()
    cleaner.run_cleanup(dry_run=args.dry_run)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

