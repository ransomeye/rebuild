# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_core/loader/model_loader.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Safe model loading for pickle and ONNX models

import os
import pickle
import logging
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("onnxruntime not available, ONNX models cannot be loaded")

class ModelLoadError(Exception):
    """Custom exception for model loading errors."""
    pass

class ModelLoader:
    """Safe loader for different model types."""
    
    def __init__(self):
        """Initialize model loader."""
        self.loaded_models = {}
    
    def load_pickle_model(self, model_path: Path) -> Any:
        """
        Load a pickle model with safety checks.
        
        Args:
            model_path: Path to the .pkl file
            
        Returns:
            Loaded model object
            
        Raises:
            ModelLoadError: If loading fails
        """
        if not model_path.exists():
            raise ModelLoadError(f"Model file not found: {model_path}")
        
        try:
            logger.info(f"Loading pickle model from {model_path}")
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info("Pickle model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to load pickle model: {e}")
            raise ModelLoadError(f"Pickle load error: {e}")
    
    def load_onnx_model(self, model_path: Path) -> Any:
        """
        Load an ONNX model.
        
        Args:
            model_path: Path to the .onnx file
            
        Returns:
            ONNX Runtime InferenceSession
            
        Raises:
            ModelLoadError: If loading fails
        """
        if not ONNX_AVAILABLE:
            raise ModelLoadError("onnxruntime is not installed")
        
        if not model_path.exists():
            raise ModelLoadError(f"Model file not found: {model_path}")
        
        try:
            logger.info(f"Loading ONNX model from {model_path}")
            session = ort.InferenceSession(str(model_path))
            logger.info("ONNX model loaded successfully")
            return session
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise ModelLoadError(f"ONNX load error: {e}")
    
    def load_model(self, model_path: Path, model_type: str = None) -> Any:
        """
        Load a model based on file extension or explicit type.
        
        Args:
            model_path: Path to the model file
            model_type: Explicit model type (pickle, onnx) or None for auto-detect
            
        Returns:
            Loaded model object
            
        Raises:
            ModelLoadError: If loading fails
        """
        model_path = Path(model_path)
        
        # Auto-detect type if not specified
        if model_type is None:
            suffix = model_path.suffix.lower()
            if suffix == '.pkl' or suffix == '.pickle':
                model_type = 'pickle'
            elif suffix == '.onnx':
                model_type = 'onnx'
            else:
                raise ModelLoadError(f"Unknown model type for file: {model_path}")
        
        # Load based on type
        if model_type == 'pickle':
            return self.load_pickle_model(model_path)
        elif model_type == 'onnx':
            return self.load_onnx_model(model_path)
        else:
            raise ModelLoadError(f"Unsupported model type: {model_type}")
    
    def predict_pickle(self, model: Any, input_data: Any) -> Any:
        """
        Run prediction with a pickle model.
        
        Args:
            model: Loaded pickle model
            input_data: Input data for prediction
            
        Returns:
            Prediction result
        """
        try:
            # Try common prediction methods
            if hasattr(model, 'predict'):
                return model.predict(input_data)
            elif hasattr(model, '__call__'):
                return model(input_data)
            elif callable(model):
                return model(input_data)
            else:
                raise ModelLoadError("Model does not have a recognizable prediction interface")
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise ModelLoadError(f"Prediction failed: {e}")
    
    def predict_onnx(self, session: Any, input_data: dict, output_names: list = None) -> dict:
        """
        Run prediction with an ONNX model.
        
        Args:
            session: ONNX Runtime InferenceSession
            input_data: Dictionary of input names to numpy arrays
            output_names: Optional list of output names to retrieve
            
        Returns:
            Dictionary of output names to numpy arrays
        """
        if not ONNX_AVAILABLE:
            raise ModelLoadError("onnxruntime is not installed")
        
        try:
            # Get input names if not provided
            input_names = [input.name for input in session.get_inputs()]
            
            # Prepare inputs
            inputs = {}
            for name in input_names:
                if name not in input_data:
                    raise ModelLoadError(f"Missing input: {name}")
                inputs[name] = input_data[name]
            
            # Run inference
            outputs = session.run(output_names, inputs)
            
            # Format outputs
            output_names = output_names or [output.name for output in session.get_outputs()]
            result = {}
            for i, name in enumerate(output_names):
                result[name] = outputs[i]
            
            return result
            
        except Exception as e:
            logger.error(f"ONNX prediction error: {e}")
            raise ModelLoadError(f"ONNX prediction failed: {e}")

