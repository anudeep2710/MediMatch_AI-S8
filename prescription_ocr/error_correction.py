"""
OCR Error Correction for Prescription Text
Corrects common OCR errors using drug database matching and fuzzy logic
"""

import re
import logging
from typing import List, Tuple, Optional
from rapidfuzz import fuzz, process
import pandas as pd

logger = logging.getLogger(__name__)


class PrescriptionErrorCorrector:
    """
    Multi-stage error correction for prescription OCR
    Stage 1: OCR pattern correction (0↔O, 1↔l, etc.)
    Stage 2: Drug name fuzzy matching against database
    Stage 3: Dosage format validation
    """
    
    def __init__(self, drug_db_path='data/cleaned_clinical_drugs_dataset.csv'):
        self.drug_db_path = drug_db_path
        self.drug_database = None
        self.drug_names = []
        self._load_drug_database()
        
        # Common OCR error patterns
        self.ocr_patterns = {
            # Number/letter confusions
            r'\bO\b': '0',  # Letter O → number 0
            r'\bl\b': '1',  # Letter l → number 1
            r'\bI\b': '1',  # Letter I → number 1
            r'\bS\b(?=\d)': '5',  # Letter S → number 5 before digits
            r'(?<=\d)O\b': '0',  # O after digit → 0
            
            # Common drug name OCR errors
            r'ceta': 'ceta',
            r'moxic': 'moxic',
            r'parac': 'parac',
        }
        
        # Dosage format patterns
        self.dosage_format = re.compile(
            r'(\d+)\s*([Oo])\s*(\d+)\s*([Oo])\s*(\d+)'
        )
    
    def _load_drug_database(self):
        """Load drug database for fuzzy matching"""
        try:
            self.drug_database = pd.read_csv(self.drug_db_path)
            self.drug_names = self.drug_database['drug_name'].dropna().unique().tolist()
            logger.info(f"✅ Loaded {len(self.drug_names)} drugs from database")
        except Exception as e:
            logger.warning(f"⚠️  Could not load drug database: {e}")
            self.drug_names = []
    
    def correct_text(self, text: str) -> Tuple[str, float]:
        """
        Apply all correction stages
        
        Args:
            text: OCR extracted text
            
        Returns:
            (corrected_text, confidence_score)
        """
        corrections_made = 0
        total_words = len(text.split())
        
        # Stage 1: OCR pattern correction
        text, stage1_corrections = self._correct_ocr_patterns(text)
        corrections_made += stage1_corrections
        
        # Stage 2: Dosage format correction
        text, stage2_corrections = self._correct_dosage_format(text)
        corrections_made += stage2_corrections
        
        # Stage 3: Drug name correction
        text, stage3_corrections = self._correct_drug_names(text)
        corrections_made += stage3_corrections
        
        # Calculate confidence (more corrections = lower confidence in original)
        if total_words > 0:
            error_rate = corrections_made / total_words
            confidence = max(0.5, 1.0 - error_rate)
        else:
            confidence = 0.8
        
        logger.info(f"Made {corrections_made} corrections, confidence: {confidence:.2f}")
        
        return text, confidence
    
    def _correct_ocr_patterns(self, text: str) -> Tuple[str, int]:
        """
        Correct common OCR misrecognitions
        e.g., O→0 in "5OOmg" → "500mg"
        """
        corrections = 0
        original = text
        
        # Fix "5OOmg" → "500mg" type errors
        text = re.sub(r'(\d+)O+(\s*mg)', r'\g<1>00\2', text)
        text = re.sub(r'(\d+)O(\d+)', lambda m: m.group(0).replace('O', '0'), text)
        
        # Fix "l-0-l" → "1-0-1" frequency patterns
        text = re.sub(r'\bl-(\d)-l\b', r'1-\1-1', text)
        text = re.sub(r'I-(\d)-I', r'1-\1-1', text)
        
        # Fix "S days" → "5 days"
        text = re.sub(r'\bS\s+days\b', '5 days', text, flags=re.IGNORECASE)
        
        # Count corrections
        if text != original:
            corrections = len([i for i, (c1, c2) in enumerate(zip(original, text)) if c1 != c2])
        
        return text, corrections
    
    def _correct_dosage_format(self, text: str) -> Tuple[str, int]:
        """
        Correct dosage formats
        e.g., "1-O-1" → "1-0-1"
        """
        corrections = 0
        
        # Fix dosage patterns with O instead of 0
        def fix_dosage(match):
            nonlocal corrections
            corrections += 1
            groups = match.groups()
            # Convert all O's to 0's in dosage pattern
            return '-'.join([g.replace('O', '0').replace('o', '0') for g in groups if g.isdigit() or g in 'Oo'])
        
        text = re.sub(
            r'(\d+)\s*[-–]\s*([Oo\d]+)\s*[-–]\s*(\d+)',
            fix_dosage,
            text,
            flags=re.IGNORECASE
        )
        
        return text, corrections
    
    def _correct_drug_names(self, text: str) -> Tuple[str, int]:
        """
        Correct drug names using fuzzy matching against database
        """
        if not self.drug_names:
            return text, 0
        
        corrections = 0
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Skip short words and numbers
            if len(word) < 4 or word.isdigit():
                corrected_words.append(word)
                continue
            
            # Check if this looks like a drug name (capitalized, alphabetic)
            if word[0].isupper() and word.isalpha():
                # Try fuzzy match
                match = self._fuzzy_match_drug(word)
                if match:
                    corrected_word, score = match
                    if score > 85:  # High confidence match
                        logger.info(f"Corrected '{word}' → '{corrected_word}' (score: {score})")
                        corrected_words.append(corrected_word)
                        corrections += 1
                        continue
            
            corrected_words.append(word)
        
        return ' '.join(corrected_words), corrections
    
    def _fuzzy_match_drug(self, word: str, threshold=75) -> Optional[Tuple[str, float]]:
        """
        Find best matching drug name in database
        
        Args:
            word: Potentially misspelled drug name
            threshold: Minimum similarity score (0-100)
            
        Returns:
            (matched_drug_name, score) or None
        """
        if not self.drug_names:
            return None
        
        # Use rapidfuzz for fast fuzzy matching
        result = process.extractOne(
            word,
            self.drug_names,
            scorer=fuzz.ratio,
            score_cutoff=threshold
        )
        
        if result:
            matched_name, score, _ = result
            return matched_name, score
        
        return None
    
    def correct_drug_name(self, drug_name: str, top_n=3) -> List[Tuple[str, float]]:
        """
        Get top N drug name matches for a given (possibly incorrect) drug name
        
        Args:
            drug_name: Drug name to correct
            top_n: Number of suggestions to return
            
        Returns:
            List of (drug_name, score) tuples
        """
        if not self.drug_names:
            return []
        
        matches = process.extract(
            drug_name,
            self.drug_names,
            scorer=fuzz.ratio,
            limit=top_n
        )
        
        return [(match[0], match[1]) for match in matches]
    
    def validate_dosage(self, dosage: str) -> Tuple[bool, str]:
        """
        Validate dosage format
        
        Returns:
            (is_valid, corrected_dosage)
        """
        # Extract number and unit
        pattern = r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)'
        match = re.search(pattern, dosage)
        
        if not match:
            return False, dosage
        
        amount, unit = match.groups()
        
        # Normalize units
        unit_mapping = {
            'mg': 'mg',
            'gm': 'g',
            'gram': 'g',
            'mcg': 'mcg',
            'microgram': 'mcg',
            'ml': 'ml',
            'iu': 'IU',
        }
        
        normalized_unit = unit_mapping.get(unit.lower(), unit)
        corrected = f"{amount}{normalized_unit}"
        
        return True, corrected
    
    def validate_frequency(self, frequency: str) -> Tuple[bool, str]:
        """
        Validate and normalize frequency
        
        Returns:
            (is_valid, normalized_frequency)
        """
        # Common frequency patterns
        freq_patterns = {
            r'\b1-0-1\b': '1-0-1 (twice daily)',
            r'\b1-1-1\b': '1-1-1 (three times daily)',
            r'\b0-0-1\b': '0-0-1 (once at night)',
            r'\bOD\b': 'Once Daily',
            r'\bBD\b': 'Twice Daily',
            r'\bTDS\b': 'Three Times Daily',
            r'\bQID\b': 'Four Times Daily',
        }
        
        for pattern, replacement in freq_patterns.items():
            if re.search(pattern, frequency, re.IGNORECASE):
                return True, replacement
        
        return True, frequency  # Default: accept as is


# Standalone functions
def correct_prescription_text(text: str, drug_db_path='data/cleaned_clinical_drugs_dataset.csv'):
    """
    Quick function to correct prescription text
    
    Args:
        text: OCR extracted text
        drug_db_path: Path to drug database
        
    Returns:
        (corrected_text, confidence_score)
    """
    corrector = PrescriptionErrorCorrector(drug_db_path)
    return corrector.correct_text(text)


def suggest_drug_corrections(drug_name: str, top_n=5, drug_db_path='data/cleaned_clinical_drugs_dataset.csv'):
    """
    Get drug name correction suggestions
    
    Args:
        drug_name: Potentially incorrect drug name
        top_n: Number of suggestions
        drug_db_path: Path to drug database
        
    Returns:
        List of (suggestion, confidence_score) tuples
    """
    corrector = PrescriptionErrorCorrector(drug_db_path)
    return corrector.correct_drug_name(drug_name, top_n)
