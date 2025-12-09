# Path and File Name : /home/ransomeye/rebuild/ransomeye_deception/tests/test_deception.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Test suite for Deception Framework components

import os
import sys
import pytest
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ransomeye_deception.dispatcher import Dispatcher
from ransomeye_deception.placement_engine import PlacementEngine
from ransomeye_deception.deployers.file_decoy import FileDecoy
from ransomeye_deception.ml.placement_model import PlacementModel
from ransomeye_deception.storage.config_store import ConfigStore


class TestPlacementModel:
    """Test placement model."""
    
    def test_model_initialization(self):
        """Test model initialization."""
        model = PlacementModel()
        assert model is not None
    
    def test_predict_attractiveness(self):
        """Test attractiveness prediction."""
        model = PlacementModel()
        import numpy as np
        
        features = np.array([0.8, 0.5, 0.2, 0.6, 0.7])
        score = model.predict_attractiveness(features)
        
        assert 0.0 <= score <= 1.0


class TestFileDecoy:
    """Test file decoy deployer."""
    
    @pytest.mark.asyncio
    async def test_provision_file(self):
        """Test file decoy provisioning."""
        deployer = FileDecoy()
        decoy_id = "test-file-001"
        
        test_path = "/tmp/test_honeyfile.txt"
        
        try:
            result = await deployer.provision(decoy_id, test_path, {})
            
            assert result['decoy_id'] == decoy_id
            assert result['type'] == 'file'
            assert Path(test_path).exists()
            
        finally:
            # Cleanup
            await deployer.deprovision(decoy_id, result)
    
    @pytest.mark.asyncio
    async def test_verify_file(self):
        """Test file decoy verification."""
        deployer = FileDecoy()
        decoy_id = "test-file-002"
        test_path = "/tmp/test_honeyfile2.txt"
        
        try:
            provision_result = await deployer.provision(decoy_id, test_path, {})
            
            verification = await deployer.verify(decoy_id, provision_result)
            
            assert verification['verified'] is True
            
        finally:
            await deployer.deprovision(decoy_id, provision_result)


class TestPlacementEngine:
    """Test placement engine."""
    
    @pytest.mark.asyncio
    async def test_recommend_placement(self):
        """Test placement recommendation."""
        engine = PlacementEngine()
        
        recommendation = await engine.recommend_placement(
            decoy_type='file',
            metadata={}
        )
        
        assert 'location' in recommendation
        assert 'score' in recommendation
        assert 'reasoning' in recommendation
        assert 0.0 <= recommendation['score'] <= 1.0


class TestConfigStore:
    """Test config store."""
    
    @pytest.mark.asyncio
    async def test_create_decoy(self):
        """Test creating decoy record."""
        store = ConfigStore()
        
        decoy_data = {
            'id': 'test-decoy-001',
            'type': 'file',
            'location': '/tmp/test.txt',
            'metadata': {},
            'provision_result': {},
            'created_at': '2024-01-01T00:00:00',
            'last_rotated_at': None,
            'status': 'active'
        }
        
        try:
            decoy_id = await store.create_decoy(decoy_data)
            assert decoy_id == 'test-decoy-001'
            
            decoy = await store.get_decoy(decoy_id)
            assert decoy is not None
            assert decoy['type'] == 'file'
            
        finally:
            await store.remove_decoy('test-decoy-001')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

