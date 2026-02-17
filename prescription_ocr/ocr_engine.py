"""
Multi-engine OCR system for prescription text extraction
Combines EasyOCR (best for handwriting) and Tesseract (good for printed text)
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class PrescriptionOCR:
    """
    Multi-engine OCR system optimized for medical prescriptions
    Prioritizes EasyOCR for handwriting recognition
    """
    
    def __init__(self, use_gpu=False):
        self.use_gpu = use_gpu
        self.engines = {}
        self._easyocr_initialized = False
        self._tesseract_initialized = False
        # Don't initialize on startup - do it lazily when needed
    
    def _initialize_engines(self):
        """Initialize OCR engines (called lazily on first use)"""
        # Initialize EasyOCR (best for handwriting)
        if not self._easyocr_initialized:
            try:
                logger.info("🔄 Initializing EasyOCR (may download models on first run, ~100MB)...")
                import easyocr
                self.engines['easyocr'] = easyocr.Reader(
                    ['en'], 
                    gpu=self.use_gpu,
                    verbose=False,
                    download_enabled=True
                )
                self._easyocr_initialized = True
                logger.info("✅ EasyOCR ready (optimized for handwriting)")
            except Exception as e:
                logger.warning(f"⚠️  EasyOCR initialization failed: {e}")
                self.engines['easyocr'] = None
        
        # Initialize Tesseract (fallback for printed text)
        if not self._tesseract_initialized:
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                self.engines['tesseract'] = pytesseract
                self._tesseract_initialized = True
                logger.info("✅ Tesseract ready")
            except Exception as e:
                logger.warning(f"⚠️  Tesseract not available (optional): {e}")
                self.engines['tesseract'] = None
    
    def extract_text(self, image, engine='auto') -> Dict:
        """
        Extract text from prescription image
        
        Args:
            image: Numpy array or image path
            engine: 'easyocr', 'tesseract', or 'auto'
            
        Returns:
            Dict with text, confidence, details, and engine_used
        """
        # Initialize engines if not done yet
        self._initialize_engines()
        
        if engine == 'auto':
            # Try  EasyOCR first (best for handwriting)
            if self.engines.get('easyocr'):
                engine = 'easyocr'
            elif self.engines.get('tesseract'):
                engine = 'tesseract'
            else:
                raise RuntimeError("No OCR engine available. Please wait for models to download or check installation.")
        
        logger.info(f"Using OCR engine: {engine}")
        
        if engine == 'easyocr':
            return self._extract_with_easyocr(image)
        elif engine == 'tesseract':
            return self._extract_with_tesseract(image)
        else:
            raise ValueError(f"Unknown engine: {engine}")
    
    def _extract_with_easyocr(self, image) -> Dict:
        """Extract text using EasyOCR (excellent for handwriting)"""
        if not self.engines.get('easyocr'):
            raise RuntimeError("EasyOCR not available")
        
        try:
            reader = self.engines['easyocr']
            
            # EasyOCR returns: [([bbox], text, confidence), ...]
            results = reader.readtext(
                image,
                detail=1,
                paragraph=False,
                decoder='beamsearch',  # Best for handwriting
                beamWidth=5,
                batch_size=1
            )
            
            texts = []
            confidences = []
            details = []
            
            for bbox, text, conf in results:
                texts.append(text)
                confidences.append(conf)
                details.append({
                    'text': text,
                    'confidence': conf,
                    'bbox': bbox
                })
            
            combined_text = ' '.join(texts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            logger.info(f"✅ EasyOCR extracted {len(texts)} segments, confidence: {avg_confidence:.2f}")
            
            return {
                'text': combined_text,
                'confidence': float(avg_confidence),
                'details': details,
                'engine_used': 'easyocr',
                'raw_results': results
            }
            
        except Exception as e:
            logger.error(f"❌ EasyOCR extraction failed: {e}")
            raise
    
    def _extract_with_tesseract(self, image) -> Dict:
        """Extract text using Tesseract (good for printed text)"""
        if not self.engines.get('tesseract'):
            raise RuntimeError("Tesseract not available")
        
        try:
            import pytesseract
            from PIL import Image
            
            if isinstance(image, np.ndarray):
                pil_image = Image.fromarray(image)
            else:
                pil_image = Image.open(image)
            
            data = pytesseract.image_to_data(
                pil_image,
                output_type=pytesseract.Output.DICT,
                config='--psm 6 --oem 3'
            )
            
            texts = []
            confidences = []
            details = []
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                
                if text and conf > 0:
                    texts.append(text)
                    confidences.append(conf / 100.0)
                    details.append({
                        'text': text,
                        'confidence': conf / 100.0,
                        'bbox': [data['left'][i], data['top'][i], 
                                data['width'][i], data['height'][i]]
                    })
            
            combined_text = ' '.join(texts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            logger.info(f"✅ Tesseract extracted {len(texts)} words, confidence: {avg_confidence:.2f}")
            
            return {
                'text': combined_text,
                'confidence': float(avg_confidence),
                'details': details,
                'engine_used': 'tesseract',
                'raw_results': data
            }
            
        except Exception as e:
            logger.error(f"❌ Tesseract extraction failed: {e}")
            raise
    
    def extract_with_ensemble(self, image) -> Dict:
        """Use both engines and pick best result"""
        results = []
        
        for engine_name in ['easyocr', 'tesseract']:
            if self.engines.get(engine_name):
                try:
                    result = self.extract_text(image, engine=engine_name)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"{engine_name} failed: {e}")
        
        if not results:
            raise RuntimeError("All OCR engines failed")
        
        best_result = max(results, key=lambda x: x['confidence'])
        best_result['all_engines'] = results
        best_result['engine_used'] = 'ensemble'
        
        return best_result


def extract_text_from_image(image_path, engine='auto', use_gpu=False):
    """Quick function to extract text from prescription image"""
    ocr = PrescriptionOCR(use_gpu=use_gpu)
    
    if engine == 'ensemble':
        return ocr.extract_with_ensemble(image_path)
    else:
        return ocr.extract_text(image_path, engine=engine)
