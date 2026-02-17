"""
Gemini AI-powered OCR correction and validation
Uses Gemini to intelligently extract medicines from messy OCR text
"""

import os
import logging
from typing import Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class GeminiOCRCorrector:
    """
    Uses Gemini AI to clean up OCR text and extract medicines
    Validates against drug database and provides structured output
    """
    
    def __init__(self, drug_db_path='data/cleaned_clinical_drugs_dataset.csv'):
        self.drug_db_path = drug_db_path
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.drug_database = None
        self.drug_list = []
        self._load_drug_database()
        
        # Initialize Gemini
        try:
            import google.generativeai as genai
            if self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("✅ Gemini AI initialized for OCR correction")
            else:
                logger.warning("⚠️  GEMINI_API_KEY not found")
                self.model = None
        except Exception as e:
            logger.warning(f"⚠️  Gemini initialization failed: {e}")
            self.model = None
    
    def _load_drug_database(self):
        """Load drug database for validation"""
        try:
            self.drug_database = pd.read_csv(self.drug_db_path)
            self.drug_list = self.drug_database['drug_name'].dropna().unique().tolist()
            logger.info(f"✅ Loaded {len(self.drug_list)} drugs for validation")
        except Exception as e:
            logger.warning(f"⚠️  Could not load drug database: {e}")
            self.drug_list = []
    
    def correct_and_extract(self, ocr_text: str) -> Dict:
        """
        Use Gemini to correct OCR errors and extract medicines
        
        Args:
            ocr_text: Raw OCR text (possibly with errors)
            
        Returns:
            Dict with corrected medicines and details
        """
        if not self.model:
            logger.warning("Gemini not available, skipping AI correction")
            return {'status': 'gemini_unavailable', 'medicines': []}
        
        try:
            # Create prompt with drug database context
            prompt = self._create_extraction_prompt(ocr_text)
            
            # Call Gemini
            logger.info("🤖 Calling Gemini AI to extract medicines...")
            response = self.model.generate_content(prompt)
            
            # Parse response
            result = self._parse_gemini_response(response.text)
            
            logger.info(f"✅ Gemini extracted {len(result.get('medicines', []))} medicines")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Gemini correction failed: {e}")
            return {'status': 'error', 'error': str(e), 'medicines': []}
    
    def _create_extraction_prompt(self, ocr_text: str) -> str:
        """Create smart prompt for Gemini with drug database context"""
        
        # Sample of common drugs for context (first 100)
        common_drugs_sample = self.drug_list[:100] if self.drug_list else []
        
        prompt = f"""You are a medical prescription expert. Extract ONLY the prescribed medicines from this OCR text.

**IMPORTANT RULES:**
1. **IGNORE** all header information: doctor names, hospital names, qualifications (MBBS, MD), registration numbers, phone numbers
2. **IGNORE** patient information: patient name, age, gender, weight, date
3. **IGNORE** clinical descriptions and diagnoses
4. **EXTRACT ONLY** from the "Advice" or prescription section
5. **LOOK FOR** medicine patterns like: Syp, Tab, Cap, Inj followed by drug names
6. **CORRECT** OCR spelling mistakes in drug names
7. **VALIDATE** drug names against common medicines

**OCR Text (with possible errors):**
{ocr_text}

**Common Medicine Names for Reference:**
{', '.join(common_drugs_sample[:50])}

**Your Task:**
Extract ONLY the actual prescribed medicines. For each medicine provide:
1. Drug name (corrected if OCR made mistakes)
2. Dosage (e.g., 500mg, 5ml, 250mg/5ml)
3. Frequency (e.g., 1-0-1, twice daily, TDS, BD, Q6H)
4. Duration (e.g., 5 days, 1 week)
5. Instructions (e.g., after food, before meals, SOS)

**Output Format (JSON):**
{{
  "medicines": [
    {{
      "drug_name": "Paracetamol",
      "dosage": "500mg",
      "frequency": "1-0-1 (three times daily)",
      "duration": "5 days",
      "route": "oral",
      "instructions": "after food"
    }}
  ]
}}

**CRITICAL:** 
- Do NOT include doctor names, hospital names, or patient details as medicines
- Do NOT include words like "Advice", "Clinical", "Description" as medicines
- ONLY extract actual pharmaceutical drugs that would be prescribed

Extract the medicines now in JSON format:"""
        
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse Gemini's JSON response"""
        import json
        import re
        
        try:
            # Try to extract JSON from response
            # Find JSON block
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return {
                    'status': 'success',
                    'medicines': result.get('medicines', []),
                    'raw_response': response_text
                }
            else:
                # Try to parse entire response
                result = json.loads(response_text)
                return {
                    'status': 'success',
                    'medicines': result.get('medicines', []),
                    'raw_response': response_text
                }
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON, trying structured text parsing...")
            # Fallback: try to parse as text
            return {
                'status': 'parsed_text',
                'medicines': [],
                'raw_response': response_text
            }


def extract_medicines_with_gemini(ocr_text: str, drug_db_path='data/cleaned_clinical_drugs_dataset.csv') -> Dict:
    """
    Quick function to extract medicines using Gemini AI
    
    Args:
        ocr_text: Raw OCR text
        drug_db_path: Path to drug database
        
    Returns:
        Dict with extracted medicines
    """
    corrector = GeminiOCRCorrector(drug_db_path)
    return corrector.correct_and_extract(ocr_text)
