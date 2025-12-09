# Path and File Name : /home/ransomeye/rebuild/ransomeye_threat_intel/tests/test_narrative_gen.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Verifies the generated narrative text matches the template structure using mock data

import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from narrative.story_builder import StoryBuilder


class TestNarrativeGeneration(unittest.TestCase):
    """Test narrative story generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.builder = StoryBuilder()
    
    def test_template_structure(self):
        """Test that template has required fields."""
        mock_data = {
            'cve_id': 'CVE-2021-44228',
            'host_id': 'host-001',
            'weakness_name': 'Deserialization of Untrusted Data',
            'cwe_id': 'CWE-502',
            'tactic_name': 'Initial Access',
            'mitigation_action': 'Apply updates immediately'
        }
        
        story = self.builder.build_story_from_data(mock_data)
        
        # Verify all required fields are present
        self.assertIn('CVE-2021-44228', story)
        self.assertIn('host-001', story)
        self.assertIn('Deserialization of Untrusted Data', story)
        self.assertIn('CWE-502', story)
        self.assertIn('Initial Access', story)
        self.assertIn('Apply updates immediately', story)
    
    def test_template_format(self):
        """Test that template follows expected format."""
        mock_data = {
            'cve_id': 'CVE-2021-44228',
            'host_id': 'host-001',
            'weakness_name': 'Test Weakness',
            'cwe_id': 'CWE-123',
            'tactic_name': 'Test Tactic',
            'mitigation_action': 'Test Action'
        }
        
        story = self.builder.build_story_from_data(mock_data)
        
        # Verify structure
        lines = story.strip().split('\n')
        self.assertGreaterEqual(len(lines), 4, "Story should have at least 4 lines")
        
        # Verify first line format
        self.assertIn('Identified', lines[0])
        self.assertIn('CVE-2021-44228', lines[0])
        self.assertIn('host-001', lines[0])
        
        # Verify second line format
        self.assertIn('vulnerability is related to', lines[1])
        self.assertIn('Test Weakness', lines[1])
        self.assertIn('CWE-123', lines[1])
        
        # Verify third line format
        self.assertIn('attacker likely used', lines[2])
        self.assertIn('Test Tactic', lines[2])
        
        # Verify fourth line format
        self.assertIn('Recommended Action', lines[3])
        self.assertIn('Test Action', lines[3])
    
    def test_missing_data_handling(self):
        """Test handling of missing data."""
        mock_data = {
            'cve_id': 'CVE-2021-44228',
            'host_id': 'host-001',
            'weakness_name': 'Unknown',
            'cwe_id': 'N/A',
            'tactic_name': 'Unknown',
            'mitigation_action': 'Review vulnerability details and apply patches'
        }
        
        story = self.builder.build_story_from_data(mock_data)
        
        # Should still generate valid story
        self.assertIn('CVE-2021-44228', story)
        self.assertIn('host-001', story)
        self.assertIn('Unknown', story)
        self.assertIn('N/A', story)
    
    def test_special_characters(self):
        """Test handling of special characters in data."""
        mock_data = {
            'cve_id': 'CVE-2021-44228',
            'host_id': 'host-001',
            'weakness_name': 'Test & Special <Characters>',
            'cwe_id': 'CWE-123',
            'tactic_name': 'Test "Tactic"',
            'mitigation_action': 'Apply updates & patches'
        }
        
        story = self.builder.build_story_from_data(mock_data)
        
        # Should handle special characters
        self.assertIn('CVE-2021-44228', story)
        self.assertIn('Test & Special <Characters>', story)
        self.assertIn('Test "Tactic"', story)
        self.assertIn('Apply updates & patches', story)


if __name__ == '__main__':
    unittest.main()

