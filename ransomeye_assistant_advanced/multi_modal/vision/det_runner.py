# Path and File Name : /home/ransomeye/rebuild/ransomeye_assistant_advanced/multi_modal/vision/det_runner.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Vision detector using ONNX runtime with YOLO-tiny model for object detection (Dialog Box, Terminal, Browser)

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import numpy as np

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logging.warning("onnxruntime not available - vision detection disabled")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security-relevant object classes
SECURITY_OBJECTS = [
    'error_dialog', 'warning_dialog', 'terminal', 'cmd_exe', 'powershell',
    'browser', 'file_explorer', 'registry_editor', 'task_manager', 'ransom_note',
    'encrypted_file', 'lock_icon', 'warning_icon'
]

class VisionDetector:
    """Vision detector using ONNX runtime."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize vision detector.
        
        Args:
            model_path: Path to ONNX model file (optional)
        """
        self.model_path = model_path or os.environ.get('VISION_MODEL_PATH', None)
        self.session = None
        self.available = False
        self.input_name = None
        self.output_name = None
        self.input_shape = None
        
        if ONNX_AVAILABLE:
            self._load_model()
        else:
            logger.warning("ONNX runtime not available - vision detection disabled")
    
    def _load_model(self):
        """Load ONNX model."""
        if not self.model_path or not Path(self.model_path).exists():
            logger.warning(f"Vision model not found at {self.model_path} - using fallback detection")
            self.available = False
            return
        
        try:
            # Create ONNX runtime session
            self.session = ort.InferenceSession(
                self.model_path,
                providers=['CPUExecutionProvider']  # Offline-only
            )
            
            # Get input/output names and shapes
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            self.input_shape = self.session.get_inputs()[0].shape
            
            self.available = True
            logger.info(f"Loaded vision model: {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error loading vision model: {e}")
            self.available = False
    
    def detect(self, image_path: Path, confidence_threshold: float = 0.5) -> List[str]:
        """
        Detect objects in image.
        
        Args:
            image_path: Path to image file
            confidence_threshold: Minimum confidence for detection
            
        Returns:
            List of detected object class names
        """
        if not self.available:
            return self._fallback_detection(image_path)
        
        try:
            # Load and preprocess image
            image = Image.open(image_path)
            image_array = self._preprocess_image(image)
            
            # Run inference
            outputs = self.session.run([self.output_name], {self.input_name: image_array})
            
            # Parse outputs (assuming YOLO format: [batch, num_detections, 6] where 6 = [x, y, w, h, conf, class])
            detections = self._parse_detections(outputs[0], confidence_threshold)
            
            # Map to security-relevant object names
            detected_objects = [self._map_class_to_security_object(d) for d in detections]
            
            logger.info(f"Detected {len(detected_objects)} objects: {detected_objects}")
            return detected_objects
            
        except Exception as e:
            logger.error(f"Error detecting objects: {e}", exc_info=True)
            return self._fallback_detection(image_path)
    
    def _preprocess_image(self, image: Image.Image) -> np.ndarray:
        """
        Preprocess image for ONNX model.
        
        Args:
            image: PIL Image
            
        Returns:
            Preprocessed numpy array
        """
        # Resize to model input size
        if self.input_shape:
            target_size = (self.input_shape[2], self.input_shape[3])  # (height, width)
        else:
            target_size = (640, 640)  # Default YOLO size
        
        image = image.resize(target_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array and normalize
        img_array = np.array(image).astype(np.float32) / 255.0
        
        # Transpose to CHW format and add batch dimension
        img_array = np.transpose(img_array, (2, 0, 1))
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array
    
    def _parse_detections(self, outputs: np.ndarray, confidence_threshold: float) -> List[Dict[str, Any]]:
        """
        Parse model outputs to detections.
        
        Args:
            outputs: Model output array
            confidence_threshold: Minimum confidence
            
        Returns:
            List of detection dictionaries
        """
        detections = []
        
        # Handle different output formats
        if len(outputs.shape) == 3:  # [batch, num_detections, 6]
            outputs = outputs[0]  # Remove batch dimension
        
        for detection in outputs:
            if len(detection) >= 6:
                x, y, w, h, conf, cls = detection[:6]
                if conf >= confidence_threshold:
                    detections.append({
                        'class_id': int(cls),
                        'confidence': float(conf),
                        'bbox': [float(x), float(y), float(w), float(h)]
                    })
        
        return detections
    
    def _map_class_to_security_object(self, detection: Dict[str, Any]) -> str:
        """
        Map detected class ID to security-relevant object name.
        
        Args:
            detection: Detection dictionary
            
        Returns:
            Object class name
        """
        class_id = detection.get('class_id', 0)
        
        # Simple mapping (in production, this would come from model metadata)
        # COCO classes: 0=person, 1=bicycle, etc.
        # For security, we map common UI elements
        
        # This is a placeholder - in production, you'd have a trained model
        # that directly outputs security-relevant classes
        if class_id < len(SECURITY_OBJECTS):
            return SECURITY_OBJECTS[class_id]
        else:
            return f"object_{class_id}"
    
    def _fallback_detection(self, image_path: Path) -> List[str]:
        """
        Fallback detection using simple heuristics when model is unavailable.
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of detected objects (heuristic-based)
        """
        if not PIL_AVAILABLE:
            return []
        
        try:
            image = Image.open(image_path)
            width, height = image.size
            
            # Simple heuristics based on image characteristics
            detected = []
            
            # Check for dark/encrypted file indicators (very basic)
            if width > 0 and height > 0:
                # Sample some pixels to check for dark images (potential encrypted files)
                pixels = list(image.getdata())
                avg_brightness = sum(sum(p[:3]) for p in pixels[:1000]) / (3 * min(1000, len(pixels)))
                
                if avg_brightness < 50:  # Very dark
                    detected.append('encrypted_file')
            
            # Always assume potential for terminal/browser (can't detect without model)
            # In production, this would be more sophisticated
            
            return detected
            
        except Exception as e:
            logger.error(f"Error in fallback detection: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if vision detection is available."""
        return self.available

