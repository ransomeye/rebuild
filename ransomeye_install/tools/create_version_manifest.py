# Path and File Name : /home/ransomeye/rebuild/ransomeye_install/tools/create_version_manifest.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Generate SHA256 hash manifest of all installed files for version tracking

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Warning: Could not hash {file_path}: {e}")
        return None

def should_include_file(file_path, root_dir):
    """Determine if a file should be included in the manifest."""
    rel_path = os.path.relpath(file_path, root_dir)
    
    # Exclude certain directories and files
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        '.pyo',
        '.pyd',
        '.git',
        '.env',
        '*.log',
        '*.tmp',
        '*.swp',
        '.DS_Store',
        'node_modules',
        'venv',
        'env',
        '.venv',
        'uninstall_snapshots',
    ]
    
    for pattern in exclude_patterns:
        if pattern in rel_path:
            return False
    
    return True

def create_manifest(root_dir, output_path):
    """Create version manifest of all files in root directory."""
    manifest = {
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "root_directory": os.path.abspath(root_dir),
        "files": {}
    }
    
    print(f"Scanning directory: {root_dir}")
    file_count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if should_include_file(os.path.join(root, d), root_dir)]
        
        for file in files:
            file_path = os.path.join(root, file)
            if should_include_file(file_path, root_dir):
                rel_path = os.path.relpath(file_path, root_dir)
                print(f"  Hashing: {rel_path}")
                
                file_hash = calculate_sha256(file_path)
                if file_hash:
                    file_stat = os.stat(file_path)
                    manifest["files"][rel_path] = {
                        "sha256": file_hash,
                        "size": file_stat.st_size,
                        "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat() + "Z"
                    }
                    file_count += 1
    
    manifest["file_count"] = file_count
    
    # Write manifest
    print(f"\nWriting manifest to: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    
    print(f"Manifest created successfully with {file_count} files")
    return manifest

def main():
    parser = argparse.ArgumentParser(description='Create version manifest of installed files')
    parser.add_argument('--root', type=str, required=True, help='Root directory to scan')
    parser.add_argument('--output', type=str, required=True, help='Output manifest JSON file path')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.root):
        print(f"Error: Root directory does not exist: {args.root}")
        return 1
    
    try:
        create_manifest(args.root, args.output)
        return 0
    except Exception as e:
        print(f"Error creating manifest: {e}")
        return 1

if __name__ == "__main__":
    exit(main())

