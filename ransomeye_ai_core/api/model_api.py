# Path and File Name : /home/ransomeye/rebuild/ransomeye_ai_core/api/model_api.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: FastAPI application for model management and prediction with SHAP explainability

import os
import json
import hashlib
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

# Import internal modules
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from registry.model_registry import get_registry
from registry.model_storage import ModelStorage
from loader.model_validator import ModelValidator, ModelValidationError
from loader.model_loader import ModelLoader, ModelLoadError
from loader.hot_swap import get_model_manager
from explainability.explainability_engine import ExplainabilityEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
registry = get_registry()
storage = ModelStorage()
validator = ModelValidator()
loader = ModelLoader()
model_manager = get_model_manager()
explainability = ExplainabilityEngine()

# Create FastAPI app
app = FastAPI(
    title="RansomEye AI Core API",
    description="Model Registry and Prediction API with SHAP Explainability",
    version="1.0.0"
)

# Request/Response models
class PredictionRequest(BaseModel):
    """Request model for predictions."""
    data: dict
    model_name: Optional[str] = None

class PredictionResponse(BaseModel):
    """Response model for predictions."""
    prediction: any
    explanation: dict
    model_id: int
    model_name: str

class ModelActivateRequest(BaseModel):
    """Request model for model activation."""
    model_id: int

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RansomEye AI Core API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    model_info = model_manager.get_model_info()
    return {
        "status": "healthy",
        "model_loaded": model_info['active'],
        "model_id": model_info.get('model_id')
    }

@app.post("/models/upload")
async def upload_model(
    file: UploadFile = File(...),
    metadata: str = Form(None)
):
    """
    Upload and register a new model bundle.
    
    Args:
        file: Model bundle file (.tar.gz)
        metadata: Optional JSON string of model metadata
        
    Returns:
        Model registration information
    """
    try:
        # Validate file type
        if not file.filename.endswith('.tar.gz'):
            raise HTTPException(
                status_code=400,
                detail="File must be a .tar.gz bundle"
            )
        
        # Save uploaded file temporarily
        temp_path = Path(f"/tmp/{file.filename}")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Calculate bundle SHA256
        bundle_sha256 = hashlib.sha256(content).hexdigest()
        
        # Validate bundle
        try:
            validation_result = validator.validate_bundle(temp_path)
            extract_dir = Path(validation_result['extract_dir'])
        except ModelValidationError as e:
            temp_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Model validation failed: {str(e)}"
            )
        
        # Load metadata
        metadata_path = extract_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                model_metadata = json.load(f)
        elif metadata:
            model_metadata = json.loads(metadata)
        else:
            raise HTTPException(
                status_code=400,
                detail="Model metadata not found in bundle and not provided"
            )
        
        # Validate metadata schema
        name = model_metadata.get('name')
        version = model_metadata.get('version')
        if not name or not version:
            raise HTTPException(
                status_code=400,
                detail="Metadata must contain 'name' and 'version'"
            )
        
        # Store model files
        model_id = registry.register_model(
            name=name,
            version=version,
            sha256=bundle_sha256,
            file_path=str(temp_path),
            metadata_json=json.dumps(model_metadata),
            created_by="api_upload"
        )
        
        # Move bundle to storage
        stored_path = storage.store_model_atomic(
            temp_path,
            model_id,
            f"{name}_{version}.tar.gz"
        )
        
        # Extract bundle to storage
        storage.extract_model_bundle(stored_path, model_id)
        
        # Clean up temp file
        temp_path.unlink()
        
        return {
            "model_id": model_id,
            "name": name,
            "version": version,
            "sha256": bundle_sha256,
            "status": "registered"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading model: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/models/{model_id}/activate")
async def activate_model(model_id: int):
    """
    Activate a model by ID (hot-swap).
    
    Args:
        model_id: ID of the model to activate
        
    Returns:
        Activation status
    """
    try:
        # Get model record
        model_record = registry.get_model_by_id(model_id)
        if not model_record:
            raise HTTPException(
                status_code=404,
                detail=f"Model ID {model_id} not found"
            )
        
        # Load metadata
        metadata = json.loads(model_record.metadata_json) if model_record.metadata_json else {}
        model_type = metadata.get('model_type', 'pickle')
        model_file = metadata.get('model_file', 'model.pkl')
        
        # Get model file path
        model_dir = storage.get_model_path(model_id)
        model_path = model_dir / model_file
        
        if not model_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Model file not found: {model_file}"
            )
        
        # Load model
        try:
            loaded_model = loader.load_model(model_path, model_type)
        except ModelLoadError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to load model: {str(e)}"
            )
        
        # Hot-swap model
        success = model_manager.set_active_model(
            loaded_model,
            model_id,
            model_type,
            metadata
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to activate model"
            )
        
        # Update registry
        registry.activate_model(model_id)
        
        return {
            "model_id": model_id,
            "name": model_record.name,
            "version": model_record.version,
            "status": "active"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating model: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.post("/predict/{model_name}")
async def predict(model_name: str, request: PredictionRequest):
    """
    Run prediction with SHAP explainability.
    
    Args:
        model_name: Name of the model to use
        request: Prediction request with data
        
    Returns:
        Prediction result with SHAP explanation
    """
    try:
        # Get active model or model by name
        model_info = model_manager.get_model_info()
        
        if not model_info['active']:
            # Try to get model by name
            model_record = registry.get_model_by_name(model_name)
            if not model_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model_name}' not found and no active model"
                )
            
            # Activate model
            # (In production, you might want to auto-activate here)
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_name}' is not active. Please activate it first."
            )
        
        # Get model
        model = model_manager.get_active_model()
        if not model:
            raise HTTPException(
                status_code=500,
                detail="Active model not available"
            )
        
        # Prepare input data
        input_data = request.data
        
        # Convert to numpy array if needed
        import numpy as np
        if isinstance(input_data, dict):
            # For dict inputs, use first value or convert appropriately
            input_array = np.array(list(input_data.values())[0]) if input_data else np.array([])
        elif isinstance(input_data, list):
            input_array = np.array(input_data)
        else:
            input_array = np.array([input_data])
        
        # Make prediction
        try:
            if model_info['model_type'] == 'pickle':
                prediction = loader.predict_pickle(model, input_array)
            elif model_info['model_type'] == 'onnx':
                # For ONNX, input_data should be a dict
                prediction = loader.predict_onnx(model, input_data if isinstance(input_data, dict) else {'input': input_array})
            else:
                prediction = loader.predict_pickle(model, input_array)
        except ModelLoadError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Prediction failed: {str(e)}"
            )
        
        # Generate SHAP explanation
        try:
            metadata = model_info.get('metadata', {})
            feature_names = metadata.get('features', None)
            
            explanation = explainability.explain_prediction(
                model=model,
                input_data=input_array,
                feature_names=feature_names,
                model_type=model_info['model_type']
            )
        except Exception as e:
            logger.warning(f"SHAP explanation generation failed: {e}")
            explanation = {
                'base_value': 0.0,
                'shap_values': {'type': 'error', 'error': str(e)},
                'features': {},
                'error': str(e)
            }
        
        # Convert prediction to JSON-serializable format
        import numpy as np
        if isinstance(prediction, np.ndarray):
            prediction_result = prediction.tolist()
        elif isinstance(prediction, dict):
            prediction_result = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in prediction.items()}
        else:
            prediction_result = float(prediction) if isinstance(prediction, (int, float)) else str(prediction)
        
        return {
            "prediction": prediction_result,
            "explanation": explanation,
            "model_id": model_info['model_id'],
            "model_name": model_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/models")
async def list_models(status: Optional[str] = None):
    """List all models, optionally filtered by status."""
    try:
        models = registry.list_models(status=status)
        return {
            "models": [model.to_dict() for model in models]
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@app.get("/models/{model_id}")
async def get_model(model_id: int):
    """Get model information by ID."""
    try:
        model = registry.get_model_by_id(model_id)
        if not model:
            raise HTTPException(
                status_code=404,
                detail=f"Model ID {model_id} not found"
            )
        return model.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get('AI_CORE_API_HOST', '0.0.0.0')
    port = int(os.environ.get('AI_CORE_API_PORT', 8084))
    
    uvicorn.run(app, host=host, port=port)

