# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/cli/assistant_cli.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: CLI tool for ingesting artifacts and querying playbook suggestions

import os
import sys
import argparse
from pathlib import Path
import requests
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def ingest_artifact(api_url: str, file_path: str, description: str = None, incident_id: str = None, token: str = None):
    """
    Ingest an artifact via API.
    
    Args:
        api_url: API base URL
        file_path: Path to artifact file
        description: Optional description
        incident_id: Optional incident ID
        token: Optional API token
    """
    url = f"{api_url}/ingest"
    
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    with open(file_path, 'rb') as f:
        files = {'file': (Path(file_path).name, f, 'application/octet-stream')}
        data = {}
        if description:
            data['description'] = description
        if incident_id:
            data['incident_id'] = incident_id
        
        response = requests.post(url, files=files, data=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        print(json.dumps(result, indent=2))
        return result

def suggest_playbook(api_url: str, artifact_id: str = None, summary: str = None, token: str = None):
    """
    Get playbook suggestion via API.
    
    Args:
        api_url: API base URL
        artifact_id: Optional artifact ID
        summary: Optional incident summary
        token: Optional API token
    """
    url = f"{api_url}/suggest_playbook"
    
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    data = {}
    if artifact_id:
        data['artifact_id'] = artifact_id
    if summary:
        data['incident_summary'] = summary
    data['include_shap'] = True
    
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    print(json.dumps(result, indent=2))
    return result

def submit_feedback(api_url: str, artifact_id: str, playbook_id: int, accepted: bool, comment: str = None, token: str = None):
    """
    Submit feedback via API.
    
    Args:
        api_url: API base URL
        artifact_id: Artifact ID
        playbook_id: Playbook ID
        accepted: Whether suggestion was accepted
        comment: Optional comment
        token: Optional API token
    """
    url = f"{api_url}/feedback"
    
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    data = {
        'artifact_id': artifact_id,
        'playbook_id': playbook_id,
        'accepted': accepted
    }
    if comment:
        data['comment'] = comment
    
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    print(json.dumps(result, indent=2))
    return result

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='RansomEye Advanced SOC Copilot CLI')
    parser.add_argument('--api-url', default='http://localhost:8008', help='API base URL')
    parser.add_argument('--token', help='API authentication token')
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest an artifact')
    ingest_parser.add_argument('file', help='Path to artifact file')
    ingest_parser.add_argument('--description', help='Artifact description')
    ingest_parser.add_argument('--incident-id', help='Incident ID')
    
    # Suggest command
    suggest_parser = subparsers.add_parser('suggest', help='Suggest a playbook')
    suggest_parser.add_argument('--artifact-id', help='Artifact ID')
    suggest_parser.add_argument('--summary', help='Incident summary')
    
    # Feedback command
    feedback_parser = subparsers.add_parser('feedback', help='Submit feedback')
    feedback_parser.add_argument('artifact_id', help='Artifact ID')
    feedback_parser.add_argument('playbook_id', type=int, help='Playbook ID')
    feedback_parser.add_argument('--accepted', action='store_true', help='Suggestion was accepted')
    feedback_parser.add_argument('--rejected', action='store_true', help='Suggestion was rejected')
    feedback_parser.add_argument('--comment', help='Optional comment')
    
    args = parser.parse_args()
    
    if args.command == 'ingest':
        ingest_artifact(
            args.api_url,
            args.file,
            args.description,
            args.incident_id,
            args.token
        )
    elif args.command == 'suggest':
        suggest_playbook(
            args.api_url,
            args.artifact_id,
            args.summary,
            args.token
        )
    elif args.command == 'feedback':
        accepted = args.accepted and not args.rejected
        submit_feedback(
            args.api_url,
            args.artifact_id,
            args.playbook_id,
            accepted,
            args.comment,
            args.token
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

