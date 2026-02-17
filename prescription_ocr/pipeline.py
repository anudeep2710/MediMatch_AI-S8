"""
Main Prescription OCR Pipeline
Orchestrates the complete workflow: preprocessing → OCR → NER → Gemini correction
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime
import json

from .preprocessing import ImagePreprocessor
from .ocr_engine import PrescriptionOCR
from .medical_ner import MedicalNER
from .error_correction import PrescriptionErrorCorrector

logger = logging.getLogger(__name__)


class PrescriptionOCRPipeline:
    """
    Complete pipeline for prescription digitization with Gemini AI fallback
    """
    
    def __init__(self, use_gpu=False, use_spacy=False, drug_db_path='data/cleaned_clinical_drugs_dataset.csv'):
        logger.info("🚀 Initializing Prescription OCR Pipeline...")
        
        self.preprocessor = ImagePreprocessor()
        self.ocr = PrescriptionOCR(use_gpu=use_gpu)
        self.ner = MedicalNER(use_spacy=use_spacy)
        self.corrector = PrescriptionErrorCorrector(drug_db_path=drug_db_path)
        
        # Initialize Gemini corrector
        try:
            from .gemini_correction import GeminiOCRCorrector
            self.gemini_corrector = GeminiOCRCorrector(drug_db_path=drug_db_path)
            logger.info("✅ Gemini AI corrector initialized")
        except Exception as e:
            logger.warning(f"⚠️  Gemini corrector unavailable: {e}")
            self.gemini_corrector = None
        
        logger.info("✅ Pipeline initialized successfully")
    
    def process_prescription(
        self,
        image_path: str,
        ocr_engine='auto',
        save_intermediate=False,
        output_dir=None
    ) -> Dict:
        """Process a prescription image end-to-end"""
        start_time = datetime.now()
        logger.info(f"📄 Processing prescription: {image_path}")
        
        results = {
            'input_image': image_path,
            'timestamp': start_time.isoformat(),
            'status': 'processing',
            'stages': {}
        }
        
        try:
            # Stage 1: Preprocessing
            logger.info("🖼️  Stage 1: Preprocessing image...")
            preprocessed_image = self.preprocessor.preprocess(image_path)
            results['stages']['preprocessing'] = {'status': 'completed'}
            
            # Stage 2: OCR
            logger.info(f"📝 Stage 2: Extracting text with {ocr_engine}...")
            if ocr_engine == 'ensemble':
                ocr_result = self.ocr.extract_with_ensemble(preprocessed_image)
            else:
                ocr_result = self.ocr.extract_text(preprocessed_image, engine=ocr_engine)
            
            raw_text = ocr_result['text']
            ocr_confidence = ocr_result['confidence']
            
            results['stages']['ocr'] = {
                'status': 'completed',
                'raw_text': raw_text,
                'confidence': ocr_confidence,
                'engine_used': ocr_result['engine_used']
            }
            
            logger.info(f"✅ OCR completed. Confidence: {ocr_confidence:.2f}")
            
            # Stage 3: Error Correction
            logger.info("🔧 Stage 3: Correcting OCR errors...")
            corrected_text, correction_confidence = self.corrector.correct_text(raw_text)
            
            results['stages']['correction'] = {
                'status': 'completed',
                'corrected_text': corrected_text,
                'confidence': correction_confidence
            }
            
            # Stage 4: NER
            logger.info("🔍 Stage 4: Extracting medical entities...")
            entities = self.ner.extract_entities(corrected_text)
            
            # Convert entities to serializable format
            entities_dict = {}
            for entity_type, entity_list in entities.items():
                entities_dict[entity_type] = [
                    {'type': e.type, 'value': e.value, 'confidence': e.confidence}
                    for e in entity_list
                ]
            
            results['stages']['ner'] = {
                'status': 'completed',
                'entities': entities_dict,
                'entity_count': sum(len(v) for v in entities.values())
            }
            
            logger.info(f"✅ NER found {results['stages']['ner']['entity_count']} entities")
            
            # Stage 5: Smart Extraction - Use Gemini if needed
            use_gemini = (ocr_confidence < 0.6 or 
                         len(entities.get('drugs', [])) == 0 or
                         len(entities.get('drugs', [])) > 10)  # Too many = probably wrong
            
            if use_gemini and self.gemini_corrector:
                logger.info("🤖 Stage 5: Using Gemini AI for intelligent extraction...")
                try:
                    gemini_result = self.gemini_corrector.correct_and_extract(raw_text)
                    
                    if gemini_result.get('status') == 'success' and gemini_result.get('medicines'):
                        logger.info(f"✅ Gemini extracted {len(gemini_result['medicines'])} medicines!")
                        prescription_items = gemini_result['medicines']
                        for item in prescription_items:
                            if 'confidence' not in item:
                                item['confidence'] = 0.85
                        results['stages']['gemini'] = {
                            'status': 'used',
                            'medicines_found': len(prescription_items)
                        }
                    else:
                        # Gemini didn't work, use NER
                        prescription_items = self.ner.structure_prescription(corrected_text, entities)
                        results['stages']['gemini'] = {'status': 'failed', 'fallback_to_ner': True}
                except Exception as e:
                    logger.warning(f"Gemini failed: {e}, using NER")
                    prescription_items = self.ner.structure_prescription(corrected_text, entities)
                    results['stages']['gemini'] = {'status': 'error', 'error': str(e)}
            else:
                # NER worked well, don't need Gemini
                logger.info("📋 Stage 5: Structuring prescription (NER)...")
                prescription_items = self.ner.structure_prescription(corrected_text, entities)
                results['stages']['gemini'] = {'status': 'skipped', 'reason': 'NER confidence good'}
            
            results['prescription_items'] = prescription_items
            results['item_count'] = len(prescription_items)
            
            # Stage 6: Validate
            logger.info("✅ Stage 6: Validating...")
            for item in prescription_items:
                if item.get('dosage'):
                    is_valid, corrected_dosage = self.corrector.validate_dosage(item['dosage'])
                    item['dosage'] = corrected_dosage
                    item['dosage_valid'] = is_valid
                
                if item.get('frequency'):
                    is_valid, normalized_freq = self.corrector.validate_frequency(item['frequency'])
                    item['frequency'] = normalized_freq
                    item['frequency_valid'] = is_valid
                
                if item.get('drug_name') and item.get('confidence', 1.0) < 0.8:
                    suggestions = self.corrector.correct_drug_name(item['drug_name'], top_n=3)
                    item['drug_suggestions'] = [
                        {'name': name, 'confidence': score/100.0}
                        for name, score in suggestions
                    ]
            
            # Calculate overall confidence
            confidences = [
                ocr_confidence,
                correction_confidence,
                sum(item.get('confidence', 0.5) for item in prescription_items) / max(len(prescription_items), 1)
            ]
            overall_confidence = sum(confidences) / len(confidences)
            
            # Finalize
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            results.update({
                'status': 'completed',
                'overall_confidence': overall_confidence,
                'processing_time_seconds': processing_time,
                'completed_at': end_time.isoformat()
            })
            
            logger.info(f"✅ Pipeline completed in {processing_time:.2f}s")
            logger.info(f"💊 Found {len(prescription_items)} prescription items")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
            results.update({
                'status': 'failed',
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            })
            return results
    
    def quick_extract(self, image_path: str) -> str:
        """Quick extraction - just get the text"""
        result = self.process_prescription(image_path, ocr_engine='easyocr')
        if result['status'] == 'completed':
            return result['stages']['correction']['corrected_text']
        else:
            return f"Error: {result.get('error', 'Unknown error')}"
    
    def extract_drugs(self, image_path: str) -> list:
        """Extract just the drug list"""
        result = self.process_prescription(image_path, ocr_engine='easyocr')
        if result['status'] == 'completed':
            return [item['drug_name'] for item in result.get('prescription_items', [])]
        else:
            return []


# Standalone function
def process_prescription_image(
    image_path: str,
    use_gpu=False,
    ocr_engine='easyocr',
    save_results=False,
    output_dir=None
):
    """Quick function to process a prescription image"""
    pipeline = PrescriptionOCRPipeline(use_gpu=use_gpu)
    return pipeline.process_prescription(
        image_path,
        ocr_engine=ocr_engine,
        save_intermediate=save_results,
        output_dir=output_dir
    )
