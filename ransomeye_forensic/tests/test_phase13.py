# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/tests/test_phase13.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Integration tests for Phase 13 (Memory Diff, DNA Extraction, ML Classification)

import os
import sys
import tempfile
import random
from pathlib import Path
import unittest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_forensic.diff.diff_memory import MemoryDiffer
from ransomeye_forensic.diff.snapshot_reader import SnapshotReader
from ransomeye_forensic.diff.diff_algorithms import RollingHash, EntropyCalculator
from ransomeye_forensic.dna.malware_dna import MalwareDNAExtractor
from ransomeye_forensic.dna.dna_serializer import DNASerializer
from ransomeye_forensic.dna.yara_wrapper import YARAWrapper
from ransomeye_forensic.ml.inference.classifier import ForensicClassifier
from ransomeye_forensic.ml.inference.fingerprinter import DNAFingerprinter


class SyntheticDataGenerator:
    """Generate synthetic binary data for testing (no real malware)."""
    
    @staticmethod
    def generate_memory_snapshot(size_mb: int = 10, entropy: float = 4.0) -> bytes:
        """
        Generate synthetic memory snapshot.
        
        Args:
            size_mb: Size in megabytes
            entropy: Target entropy (0-8)
            
        Returns:
            Synthetic memory bytes
        """
        size_bytes = size_mb * 1024 * 1024
        
        if entropy > 7.0:
            # High entropy (packed/encrypted) - random bytes
            return bytes(random.randint(0, 255) for _ in range(size_bytes))
        elif entropy > 5.0:
            # Medium entropy - mix of random and structured
            data = bytearray()
            for i in range(size_bytes):
                if i % 100 < 50:
                    data.append(random.randint(0, 255))
                else:
                    data.append(i % 256)
            return bytes(data)
        else:
            # Low entropy - structured data
            pattern = b'RansomEye Test Pattern ' * (size_bytes // 25)
            return pattern[:size_bytes]
    
    @staticmethod
    def generate_binary_artifact(size_kb: int = 100, is_malicious: bool = False) -> bytes:
        """
        Generate synthetic binary artifact.
        
        Args:
            size_kb: Size in kilobytes
            is_malicious: Whether to include suspicious features
            
        Returns:
            Synthetic binary bytes
        """
        size_bytes = size_kb * 1024
        data = bytearray()
        
        # Add PE header (MZ signature)
        data.extend(b'MZ\x90\x00')
        data.extend(b'\x00' * 60)
        
        # Add some strings
        if is_malicious:
            # Suspicious strings
            data.extend(b'http://malicious-site.com\x00')
            data.extend(b'C:\\Windows\\Temp\\malware.exe\x00')
            data.extend(b'192.168.1.100\x00')
            data.extend(b'CreateFile\x00ReadFile\x00WriteFile\x00')
        else:
            # Benign strings
            data.extend(b'Hello World\x00')
            data.extend(b'Test Application\x00')
        
        # Fill rest with pattern or high entropy
        remaining = size_bytes - len(data)
        if is_malicious:
            # High entropy for packed malware
            data.extend(bytes(random.randint(0, 255) for _ in range(remaining)))
        else:
            # Low entropy pattern
            pattern = b'DATA' * (remaining // 4)
            data.extend(pattern[:remaining])
        
        return bytes(data[:size_bytes])


class TestMemoryDiffing(unittest.TestCase):
    """Test memory diffing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = SyntheticDataGenerator()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_rolling_hash(self):
        """Test rolling hash algorithm."""
        rolling_hash = RollingHash(window_size=4)
        
        data1 = b'ABCD'
        data2 = b'BCDE'
        
        hash1 = rolling_hash.compute_hash(data1)
        hash2 = rolling_hash.compute_hash(data2)
        
        self.assertNotEqual(hash1, hash2)
        
        # Test rolling
        hash_rolled = rolling_hash.roll_hash(hash1, ord('A'), ord('E'))
        self.assertEqual(hash_rolled, hash2)
    
    def test_entropy_calculation(self):
        """Test entropy calculation."""
        calc = EntropyCalculator()
        
        # Low entropy (repeating pattern)
        low_entropy_data = b'AAAA' * 100
        entropy_low = calc.calculate_entropy(low_entropy_data)
        self.assertLess(entropy_low, 2.0)
        
        # High entropy (random)
        high_entropy_data = bytes(random.randint(0, 255) for _ in range(400))
        entropy_high = calc.calculate_entropy(high_entropy_data)
        self.assertGreater(entropy_high, 7.0)
    
    def test_memory_diff(self):
        """Test memory snapshot diffing."""
        # Generate two snapshots
        snapshot_a = self.generator.generate_memory_snapshot(size_mb=1, entropy=4.0)
        snapshot_b = self.generator.generate_memory_snapshot(size_mb=1, entropy=6.0)
        
        # Write to files
        snapshot_a_path = Path(self.temp_dir) / "snapshot_a.raw"
        snapshot_b_path = Path(self.temp_dir) / "snapshot_b.raw"
        
        snapshot_a_path.write_bytes(snapshot_a)
        snapshot_b_path.write_bytes(snapshot_b)
        
        # Perform diff
        differ = MemoryDiffer()
        diff_result = differ.diff_snapshots(
            str(snapshot_a_path),
            str(snapshot_b_path)
        )
        
        self.assertIn('diff_id', diff_result)
        self.assertIn('statistics', diff_result)
        self.assertIn('changed_pages', diff_result)
        self.assertGreater(diff_result['statistics']['changed_pages'], 0)


class TestDNAExtraction(unittest.TestCase):
    """Test DNA extraction functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = SyntheticDataGenerator()
        self.extractor = MalwareDNAExtractor()
        self.serializer = DNASerializer()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dna_extraction(self):
        """Test DNA extraction from binary."""
        # Generate test artifact
        artifact_data = self.generator.generate_binary_artifact(size_kb=50, is_malicious=False)
        artifact_path = Path(self.temp_dir) / "test_artifact.bin"
        artifact_path.write_bytes(artifact_data)
        
        # Extract DNA
        dna_data = self.extractor.extract_dna(str(artifact_path), artifact_type='binary')
        
        self.assertIn('hashes', dna_data)
        self.assertIn('entropy', dna_data)
        self.assertIn('strings', dna_data)
        self.assertIn('imports', dna_data)
        self.assertIn('metadata', dna_data)
    
    def test_dna_serialization(self):
        """Test DNA serialization."""
        # Generate test DNA
        artifact_data = self.generator.generate_binary_artifact(size_kb=50)
        artifact_path = Path(self.temp_dir) / "test_artifact.bin"
        artifact_path.write_bytes(artifact_data)
        
        dna_data = self.extractor.extract_dna(str(artifact_path))
        
        # Serialize
        dna_json = self.serializer.serialize(dna_data)
        self.assertIsInstance(dna_json, str)
        
        # Compute hash
        dna_hash = self.serializer.compute_dna_hash(dna_data)
        self.assertIsInstance(dna_hash, str)
        self.assertEqual(len(dna_hash), 64)  # SHA256 hex
    
    def test_yara_wrapper(self):
        """Test YARA wrapper (may not have rules, but should not crash)."""
        wrapper = YARAWrapper()
        
        # Generate test artifact
        artifact_data = self.generator.generate_binary_artifact(size_kb=10)
        artifact_path = Path(self.temp_dir) / "test_artifact.bin"
        artifact_path.write_bytes(artifact_data)
        
        # Scan (may return empty if no rules)
        matches = wrapper.scan_file(str(artifact_path))
        self.assertIsInstance(matches, list)


class TestMLClassification(unittest.TestCase):
    """Test ML classification functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = SyntheticDataGenerator()
        self.classifier = ForensicClassifier()
        self.fingerprinter = DNAFingerprinter()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_classifier_prediction(self):
        """Test classifier prediction."""
        # Generate test DNA
        artifact_data = self.generator.generate_binary_artifact(size_kb=50, is_malicious=True)
        artifact_path = Path(self.temp_dir) / "test_artifact.bin"
        artifact_path.write_bytes(artifact_data)
        
        extractor = MalwareDNAExtractor()
        dna_data = extractor.extract_dna(str(artifact_path))
        
        # Predict
        prediction = self.classifier.predict(dna_data, return_shap=True)
        
        self.assertIn('is_malicious', prediction)
        self.assertIn('malicious_score', prediction)
        self.assertIn('confidence', prediction)
        self.assertIn('shap_values', prediction)
        self.assertIsInstance(prediction['malicious_score'], float)
        self.assertGreaterEqual(prediction['malicious_score'], 0.0)
        self.assertLessEqual(prediction['malicious_score'], 1.0)
    
    def test_fingerprinting(self):
        """Test DNA fingerprinting."""
        # Generate test DNA
        artifact_data = self.generator.generate_binary_artifact(size_kb=50)
        artifact_path = Path(self.temp_dir) / "test_artifact.bin"
        artifact_path.write_bytes(artifact_data)
        
        extractor = MalwareDNAExtractor()
        dna_data = extractor.extract_dna(str(artifact_path))
        
        # Generate fingerprint
        fingerprint = self.fingerprinter.generate_fingerprint(dna_data, method='lsh')
        
        self.assertIn('method', fingerprint)
        self.assertIn('fingerprint', fingerprint)
        self.assertEqual(fingerprint['method'], 'lsh')
        
        # Test comparison
        fingerprint2 = self.fingerprinter.generate_fingerprint(dna_data, method='lsh')
        similarity = self.fingerprinter.compare_fingerprints(fingerprint, fingerprint2)
        self.assertEqual(similarity, 1.0)  # Same DNA should match


if __name__ == '__main__':
    unittest.main()

