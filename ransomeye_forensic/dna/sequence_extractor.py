# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/dna/sequence_extractor.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Extract behavioral API call sequences from execution traces

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SequenceExtractor:
    """
    Extract behavioral API call sequences from execution traces.
    In production, integrates with ETW (Windows) or ptrace/strace (Linux).
    """
    
    def __init__(self):
        """Initialize sequence extractor."""
        # Common API call categories
        self.api_categories = {
            'file_ops': ['CreateFile', 'ReadFile', 'WriteFile', 'DeleteFile', 'MoveFile', 'CopyFile'],
            'registry_ops': ['RegOpenKey', 'RegSetValue', 'RegQueryValue', 'RegDeleteKey'],
            'network_ops': ['InternetOpen', 'HttpSendRequest', 'Socket', 'Connect', 'Bind', 'Listen'],
            'process_ops': ['CreateProcess', 'TerminateProcess', 'OpenProcess', 'execve', 'fork'],
            'memory_ops': ['VirtualAlloc', 'VirtualProtect', 'HeapAlloc', 'mmap', 'mprotect'],
            'crypto_ops': ['CryptEncrypt', 'CryptDecrypt', 'BCryptEncrypt', 'EVP_EncryptInit']
        }
    
    def extract_sequences(self, trace_path: Optional[str] = None, trace_data: Optional[List[Dict]] = None) -> Dict:
        """
        Extract API call sequences from trace.
        
        Args:
            trace_path: Path to trace file (JSON or text)
            trace_data: Pre-loaded trace data (list of API calls)
            
        Returns:
            Dictionary with extracted sequences and statistics
        """
        if trace_data is None:
            if trace_path is None:
                raise ValueError("Either trace_path or trace_data must be provided")
            trace_data = self._load_trace(trace_path)
        
        if not trace_data:
            return {
                'sequences': [],
                'statistics': {},
                'categories': {}
            }
        
        # Extract sequences
        sequences = []
        category_counts = {cat: 0 for cat in self.api_categories.keys()}
        category_counts['other'] = 0
        
        for call in trace_data:
            api_name = call.get('api', call.get('function', ''))
            category = self._categorize_api(api_name)
            category_counts[category] = category_counts.get(category, 0) + 1
            
            sequences.append({
                'timestamp': call.get('timestamp', datetime.utcnow().isoformat()),
                'api': api_name,
                'category': category,
                'parameters': call.get('parameters', {}),
                'return_value': call.get('return_value'),
                'pid': call.get('pid'),
                'tid': call.get('tid')
            })
        
        # Generate n-grams (sequences of N consecutive calls)
        bigrams = self._generate_ngrams(sequences, n=2)
        trigrams = self._generate_ngrams(sequences, n=3)
        
        # Calculate statistics
        statistics = {
            'total_calls': len(sequences),
            'unique_apis': len(set(s['api'] for s in sequences)),
            'bigrams': len(bigrams),
            'trigrams': len(trigrams),
            'categories': category_counts
        }
        
        return {
            'sequences': sequences,
            'bigrams': bigrams[:100],  # Limit for storage
            'trigrams': trigrams[:100],
            'statistics': statistics,
            'categories': category_counts
        }
    
    def _load_trace(self, trace_path: str) -> List[Dict]:
        """Load trace from file."""
        trace_file = Path(trace_path)
        
        if not trace_file.exists():
            logger.warning(f"Trace file not found: {trace_path}")
            return []
        
        # Try JSON first
        if trace_file.suffix == '.json':
            try:
                with open(trace_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading JSON trace: {e}")
                return []
        
        # Try text format (simulated strace/ETW output)
        else:
            return self._parse_text_trace(trace_file)
    
    def _parse_text_trace(self, trace_file: Path) -> List[Dict]:
        """Parse text-format trace (simulated)."""
        trace_data = []
        
        try:
            with open(trace_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Simulated trace format: "timestamp pid tid api_name(params) = return_value"
                    # In production, would parse actual strace/ETW format
                    if '=' in line and '(' in line:
                        parts = line.strip().split('=', 1)
                        if len(parts) == 2:
                            api_part = parts[0].strip()
                            return_part = parts[1].strip()
                            
                            # Extract API name
                            if '(' in api_part:
                                api_name = api_part.split('(')[0].strip()
                                params = api_part.split('(')[1].rstrip(')')
                            else:
                                api_name = api_part
                                params = ''
                            
                            trace_data.append({
                                'timestamp': datetime.utcnow().isoformat(),
                                'api': api_name,
                                'parameters': {'raw': params},
                                'return_value': return_part,
                                'line': line_num
                            })
        except Exception as e:
            logger.error(f"Error parsing text trace: {e}")
        
        return trace_data
    
    def _categorize_api(self, api_name: str) -> str:
        """Categorize API call."""
        api_lower = api_name.lower()
        
        for category, apis in self.api_categories.items():
            for api in apis:
                if api.lower() in api_lower:
                    return category
        
        return 'other'
    
    def _generate_ngrams(self, sequences: List[Dict], n: int = 2) -> List[List[str]]:
        """Generate n-grams from sequences."""
        ngrams = []
        
        for i in range(len(sequences) - n + 1):
            ngram = [seq['api'] for seq in sequences[i:i + n]]
            ngrams.append(ngram)
        
        return ngrams
    
    def extract_from_memory_dump(self, memory_dump_path: str) -> Dict:
        """
        Extract sequences from memory dump (simulated - would use Volatility in production).
        
        Args:
            memory_dump_path: Path to memory dump
            
        Returns:
            Extracted sequences
        """
        # In production, would use Volatility plugins to extract API call traces
        # For now, return empty sequences
        logger.info(f"Extracting sequences from memory dump: {memory_dump_path}")
        
        return {
            'sequences': [],
            'statistics': {'total_calls': 0},
            'categories': {},
            'source': 'memory_dump',
            'note': 'Memory dump sequence extraction requires Volatility integration'
        }

