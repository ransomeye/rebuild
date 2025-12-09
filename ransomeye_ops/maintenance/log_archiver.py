# Path and File Name : /home/ransomeye/rebuild/ransomeye_ops/maintenance/log_archiver.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Compresses logs older than retention period, verifies hash before deletion

import os
import sys
import gzip
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List


class LogArchiver:
    """Archives and compresses old log files."""
    
    def __init__(self, rebuild_root: str = None):
        self.rebuild_root = Path(rebuild_root) if rebuild_root else Path(
            os.environ.get('REBUILD_ROOT', '/home/ransomeye/rebuild')
        )
        self.logs_dir = self.rebuild_root / 'logs'
        self.archive_dir = self.logs_dir / 'archive'
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        self.retention_days = int(os.environ.get('LOG_RETENTION_DAYS', '30'))
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def compress_log(self, log_file: Path) -> bool:
        """Compress a log file and verify integrity."""
        try:
            # Calculate original checksum
            original_hash = self.calculate_checksum(log_file)
            
            # Compress file
            compressed_path = log_file.with_suffix('.log.gz')
            with open(log_file, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Verify compressed file can be read
            with gzip.open(compressed_path, 'rb') as f:
                decompressed = f.read()
                verify_hash = hashlib.sha256(decompressed).hexdigest()
            
            if verify_hash != original_hash:
                print(f"ERROR: Checksum mismatch for {log_file}")
                compressed_path.unlink()
                return False
            
            # Move compressed file to archive
            archive_path = self.archive_dir / compressed_path.name
            shutil.move(str(compressed_path), str(archive_path))
            
            # Delete original only after verification
            log_file.unlink()
            
            print(f"  ✓ Archived: {log_file.name} -> {archive_path.name}")
            return True
            
        except Exception as e:
            print(f"  ✗ Failed to archive {log_file}: {e}")
            return False
    
    def archive_old_logs(self, dry_run: bool = False) -> dict:
        """Archive logs older than retention period."""
        if not self.logs_dir.exists():
            print(f"Logs directory not found: {self.logs_dir}")
            return {'archived': 0, 'failed': 0, 'skipped': 0}
        
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        print(f"Archiving logs older than {self.retention_days} days (before {cutoff_time.date()})...")
        
        archived = 0
        failed = 0
        skipped = 0
        
        # Find all .log files
        for log_file in self.logs_dir.rglob('*.log'):
            # Skip already compressed files
            if log_file.suffix == '.gz':
                continue
            
            # Check if file is old enough
            file_mtime = log_file.stat().st_mtime
            if file_mtime > cutoff_timestamp:
                skipped += 1
                continue
            
            if dry_run:
                print(f"  [DRY RUN] Would archive: {log_file.relative_to(self.logs_dir)}")
                archived += 1
            else:
                if self.compress_log(log_file):
                    archived += 1
                else:
                    failed += 1
        
        print(f"\nArchive complete: {archived} archived, {failed} failed, {skipped} skipped")
        return {'archived': archived, 'failed': failed, 'skipped': skipped}
    
    def cleanup_old_archives(self, archive_retention_days: int = 365) -> int:
        """Remove archived logs older than archive retention period."""
        if not self.archive_dir.exists():
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=archive_retention_days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        removed = 0
        for archive_file in self.archive_dir.glob('*.gz'):
            if archive_file.stat().st_mtime < cutoff_timestamp:
                archive_file.unlink()
                removed += 1
                print(f"  Removed old archive: {archive_file.name}")
        
        return removed


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Archive old log files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be archived without doing it')
    parser.add_argument('--retention-days', type=int, help='Days to retain logs (default: from env or 30)')
    parser.add_argument('--cleanup-archives', type=int, help='Remove archives older than N days')
    
    args = parser.parse_args()
    
    archiver = LogArchiver()
    if args.retention_days:
        archiver.retention_days = args.retention_days
    
    archiver.archive_old_logs(dry_run=args.dry_run)
    
    if args.cleanup_archives:
        removed = archiver.cleanup_old_archives(args.cleanup_archives)
        print(f"Removed {removed} old archive files")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

