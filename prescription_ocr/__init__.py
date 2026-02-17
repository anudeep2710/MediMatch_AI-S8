"""
Prescription OCR Module for MediMatch
Handles medical prescription image processing, OCR, NER, and error correction
"""

from .pipeline import PrescriptionOCRPipeline

__version__ = "1.0.0"
__all__ = ['PrescriptionOCRPipeline']
