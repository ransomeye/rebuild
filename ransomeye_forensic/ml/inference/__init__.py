# Path and File Name : /home/ransomeye/rebuild/ransomeye_forensic/ml/inference/__init__.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: ML inference module initialization

from .classifier import ForensicClassifier
from .fingerprinter import DNAFingerprinter

__all__ = ['ForensicClassifier', 'DNAFingerprinter']

