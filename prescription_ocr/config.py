"""
Configuration for Prescription OCR System
"""

import os

# OCR Settings
OCR_ENGINES = {
    'tesseract': True,  # Good for printed text
    'easyocr': True,    # Excellent for handwriting
}

# For handwriting, EasyOCR is prioritized
DEFAULT_ENGINE = 'easyocr'  # Best for doctor's handwriting

# EasyOCR Settings (optimized for handwriting)
EASYOCR_CONFIG = {
    'languages': ['en'],
    'gpu': False,  # Set to True if GPU available
    'detail': 1,   # Get bounding boxes and confidence scores
    'paragraph': False,
    'decoder': 'beamsearch',  # Better for handwriting
}

# Tesseract Settings (fallback for printed text)
TESSERACT_CONFIG = {
    'lang': 'eng',
    'config': '--psm 6 --oem 3',  # PSM 6: uniform block of text, OEM 3: default
}

# Image Preprocessing
PREPROCESSING = {
    'resize_width': 2000,  # Larger size for better OCR
    'denoise': True,
    'contrast_enhancement': True,
    'adaptive_threshold': True,
    'deskew': True,
}

# Confidence thresholds
CONFIDENCE_THRESHOLDS = {
    'high': 0.85,
    'medium': 0.65,
    'low': 0.45,
}

# Prescription entity types
ENTITY_TYPES = [
    'DRUG_NAME',
    'DOSAGE',
    'FREQUENCY',
    'DURATION',
    'ROUTE',
    'QUANTITY',
    'INSTRUCTION',
    'PATIENT_NAME',
    'PATIENT_AGE',
    'DOCTOR_NAME',
    'DATE',
]

# Common medical abbreviations
MEDICAL_ABBREVIATIONS = {
    'OD': 'Once Daily',
    'BD': 'Twice Daily',
    'TDS': 'Three Times Daily',
    'QID': 'Four Times Daily',
    'PRN': 'As Needed',
    'AC': 'Before Meals',
    'PC': 'After Meals',
    'HS': 'At Bedtime',
    'STAT': 'Immediately',
    'PO': 'By Mouth',
    'IV': 'Intravenous',
    'IM': 'Intramuscular',
    'SC': 'Subcutaneous',
    'SL': 'Sublingual',
    'TOP': 'Topical',
}

# Dosage units
DOSAGE_UNITS = ['mg', 'g', 'mcg', 'ml', 'L', 'IU', 'units', '%']

# Storage paths
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'prescriptions')
PROCESSED_FOLDER = os.path.join('static', 'processed', 'prescriptions')
MODEL_FOLDER = os.path.join('models', 'prescription_ocr')

# Database
DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///medimatch.db')

# Ensure directories exist
for folder in [UPLOAD_FOLDER, PROCESSED_FOLDER, MODEL_FOLDER]:
    os.makedirs(folder, exist_ok=True)
