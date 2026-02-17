"""
Gemini Vision OCR Module
Uses Gemini Vision capabilities to directly analyze prescription images
and extract medication details in one step.
"""

import os
import logging
import json
import PIL.Image
import google.generativeai as genai
from typing import Dict, List, Optional
import sys
import traceback

logger = logging.getLogger(__name__)

class GeminiVisionOCR:
    """
    Direct Image-to-JSON extraction using Gemini Vision
    """
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            logger.error("❌ GEMINI_API_KEY not found in environment variables")
            raise ValueError("GEMINI_API_KEY is required")
            
        genai.configure(api_key=self.api_key)
        # Using user-specified model
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("✅ Gemini Vision initialized (Model: gemini-2.5-flash)")

    def process_image(self, image_path: str) -> Dict:
        """
        Send image to Gemini and get structured prescription data
        """
        try:
            logger.info(f"🤖 Sending image to Gemini Vision: {image_path}")
            
            # Load image
            img = PIL.Image.open(image_path)
            
            # Prompt for extraction
            prompt = """
            You are an expert pharmacist. Analyze this prescription image.
            
            Extract the following details for each medicine found:
            1. Drug Name
            2. Dosage
            3. Frequency
            4. Duration
            5. Instructions
            
            Output the result strictly as a JSON object with this format:
            {
                "medicines": [
                    {
                        "drug_name": "Name",
                        "dosage": "Dosage",
                        "frequency": "Frequency",
                        "duration": "Duration",
                        "instructions": "Instructions"
                    }
                ],
                "confidence_score": 0.95
            }
            """
            
            # Generate content
            response = self.model.generate_content([prompt, img])
            
            # Parse response
            response_text = response.text
            logger.info(f"✅ Gemini response received (Length: {len(response_text)})")
            print(f"[GEMINI RAW] {response_text[:200]}...", file=sys.stderr)
            
            # Extract JSON from response
            json_data = self._extract_json(response_text)
            
            # Convert medicines to prescription_items format
            medicines = json_data.get('medicines', [])
            prescription_items = []
            
            for med in medicines:
                # Normalize the structure
                item = {
                    'drug_name': med.get('drug_name', 'Unknown'),
                    'dosage': med.get('dosage', ''),
                    'frequency': med.get('frequency', ''),
                    'duration': med.get('duration', ''),
                    'route': med.get('route', 'oral'),
                    'instructions': med.get('instructions', ''),  # Keep as string
                    'confidence': 0.85
                }
                prescription_items.append(item)
            
            return {
                'status': 'completed',
                'prescription_items': prescription_items,
                'overall_confidence': json_data.get('confidence_score', 0.85),
                'raw_text': response_text
            }
            
        except Exception as e:
            logger.error(f"❌ Gemini Vision failed: {e}")
            traceback.print_exc()
            return {
                'status': 'failed',
                'error': str(e),
                'prescription_items': []
            }

    def _extract_json(self, text: str) -> Dict:
        """Helper to extract JSON from markdown code blocks or raw text"""
        try:
            # Remove markdown code blocks if present
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            text = text.strip()
            
            # Try to find JSON block with regex if simple cleanup didn't work
            import re
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                text = match.group(0)
            
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Failed to parse JSON: {e}")
            print(f"[GEMINI JSON ERROR] Could not parse: {text[:100]}...", file=sys.stderr)
            return {"medicines": []}
