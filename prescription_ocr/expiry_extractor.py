import os
import re
import json
import logging
from datetime import datetime
import numpy as np
import PIL.Image
import google.generativeai as genai

logger = logging.getLogger(__name__)

class CAMEEVerifier:
    """
    Expiry Extraction using Purely Gemini Vision (Cloud)
    Bypassing local OCR dependencies to guarantee stability.
    """
    def __init__(self, use_gpu=False):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Extraction will fail.")
        else:
            genai.configure(api_key=self.api_key)
        
        self.vlm_model = genai.GenerativeModel('gemini-2.5-flash')

    def process_images(self, image_paths):
        """
        Processes list of images purely via Gemini API.
        """
        logger.info(f"[CAMEE] Beginning cloud extraction on {len(image_paths)} images")
        
        vlm_result, vlm_conf = self._run_gemini_branch(image_paths)
        
        # Normalization
        final_date = self._normalize_date(vlm_result.get('expiry_date', ''))
        
        # Status Validation
        status = self._validate_logical_status(final_date)
        
        return {
            "expiry_date": final_date if final_date else None,
            "status": status,
            "confidence": round(vlm_conf, 3),
            "source": "Gemini_Vision",
            "debug": {
                "ocr_raw": "Bypassed (Using Gemini)",
                "vlm_raw": vlm_result,
                "agreement_score": 1.0
            }
        }

    def _run_gemini_branch(self, image_paths):
        """Send to Gemini for structured extraction"""
        try:
            images = [PIL.Image.open(p) for p in image_paths]
            
            prompt = '''
            You are an expert pharmaceutical system. Analyze these medicine packaging images.
            Look specifically for the Expiry Date (often labeled EXP, EXPIRY, or USE BEFORE).
            Also find the Manufacturing Date (MFG) if possible.
            
            Return strictly a JSON object:
            {
               "expiry_date": "MM/YYYY",
               "confidence": 0.95
            }
            If no reasonable expiry date can be identified, return empty string and 0.0 for confidence.
            Output ONLY valid JSON. Keep it raw without markdown tags if possible.
            '''
            
            response = self.vlm_model.generate_content([prompt] + images)
            text = response.text.replace('```json', '').replace('```', '').strip()
            
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                data = json.loads(match.group(0))
                
                date_val = data.get('expiry_date', '')
                conf_val = float(data.get('confidence', 0.0))
                return data, conf_val
        except Exception as e:
            logger.error(f"[GEMINI] Extraction failed: {e}")
            
        return {"expiry_date": ""}, 0.0

    def _normalize_date(self, raw_str):
        """Convert various date strings into rigid YYYY-MM ISO format"""
        if not raw_str:
            return None
            
        raw_str = raw_str.upper().strip()
        
        for kw in ['EXPIRY DATE', 'EXPIRY', 'EXP', 'EXP.', 'USE BEFORE']:
            raw_str = raw_str.replace(kw, '').strip()
            raw_str = raw_str.lstrip(':.-+*# ').strip()
        
        # Matches MM/YY, MM/YYYY, MM-YY, MM-YYYY, MM.YY, MM.YYYY
        match = re.search(r'(\d{1,2})[/.\-](\d{2,4})', raw_str)
        if match:
            mm = int(match.group(1))
            yy = int(match.group(2))
            
            if yy < 100:
                yy += 2000
            
            if 1 <= mm <= 12 and 2020 <= yy <= 2040:
                return f"{yy:04d}-{mm:02d}"
                
        return None

    def _validate_logical_status(self, iso_date):
        if not iso_date:
            return "UNKNOWN"
            
        try:
            y, m = map(int, iso_date.split('-'))
            exp_date = datetime(y, m, 1)
            now = datetime.now()
            
            diff_days = (exp_date - now).days
            
            if diff_days < 0:
                return "EXPIRED"
            elif diff_days <= 30:
                return "NEAR_EXPIRY"
            else:
                return "SAFE"
        except:
            return "UNKNOWN"
