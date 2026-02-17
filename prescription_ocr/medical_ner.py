"""
Medical Named Entity Recognition (NER) for Prescription Text
Extracts structured information: drugs, dosages, frequencies, etc.
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
from prescription_ocr.config import MEDICAL_ABBREVIATIONS, DOSAGE_UNITS

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents an extracted entity"""
    type: str
    value: str
    confidence: float
    start_pos: int = 0
    end_pos: int = 0


class MedicalNER:
    """
    Extract medical entities from prescription text
    Uses regex patterns + optional spaCy for better accuracy
    """
    
    def __init__(self, use_spacy=False):
        self.use_spacy = use_spacy
        self.nlp = None
        
        if use_spacy:
            try:
                import spacy
                # Try to load medical model
                try:
                    self.nlp = spacy.load("en_core_sci_sm")
                    logger.info("✅ Loaded scispacy medical model")
                except:
                    self.nlp = spacy.load("en_core_web_sm")
                    logger.info("✅ Loaded standard spacy model")
            except Exception as e:
                logger.warning(f"⚠️  spaCy not available: {e}")
                self.use_spacy = False
        
        # Compile regex patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for entity extraction"""
        
        # Drug name patterns (capitalized words, branded names)
        self.drug_pattern = re.compile(
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b'
        )
        
        # Dosage patterns
        dosage_units = '|'.join(DOSAGE_UNITS)
        self.dosage_pattern = re.compile(
            rf'\b(\d+(?:\.\d+)?)\s*({dosage_units})\b',
            re.IGNORECASE
        )
        
        # Frequency patterns (1-0-1, twice daily, etc.)
        self.frequency_pattern = re.compile(
            r'\b(\d+-\d+-\d+|\d+\s*times?\s*(?:a\s*)?day|once|twice|thrice|'
            r'OD|BD|TDS|QID|PRN)\b',
            re.IGNORECASE
        )
        
        # Duration patterns
        self.duration_pattern = re.compile(
            r'\b(?:for\s+)?(\d+)\s*(days?|weeks?|months?)\b',
            re.IGNORECASE
        )
        
        # Route patterns
        self.route_pattern = re.compile(
            r'\b(oral(?:ly)?|IV|IM|SC|PO|topical(?:ly)?|sublingual)\b',
            re.IGNORECASE
        )
        
        # Quantity patterns
        self.quantity_pattern = re.compile(
            r'\b(?:qty|quantity|#)\s*[:=]?\s*(\d+)\b',
            re.IGNORECASE
        )
        
        # Date patterns
        self.date_pattern = re.compile(
            r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b'
        )
        
        # Age patterns
        self.age_pattern = re.compile(
            r'\b(\d{1,3})\s*(?:years?|yrs?|Y)\b',
            re.IGNORECASE
        )
    
    def extract_entities(self, text: str) -> Dict[str, List[Entity]]:
        """
        Extract all medical entities from prescription text
        
        Args:
            text: OCR extracted text
            
        Returns:
            Dict of entity_type -> List[Entity]
        """
        entities = {
            'drugs': [],
            'dosages': [],
            'frequencies': [],
            'durations': [],
            'routes': [],
            'quantities': [],
            'dates': [],
            'ages': [],
            'instructions': []
        }
        
        try:
            # **NEW: Identify and extract only medication section**
            medication_text = self._extract_medication_section(text)
            
            # Extract using regex patterns on medication section
            entities['dosages'] = self._extract_dosages(medication_text)
            entities['frequencies'] = self._extract_frequencies(medication_text)
            entities['durations'] = self._extract_durations(medication_text)
            entities['routes'] = self._extract_routes(medication_text)
            entities['quantities'] = self._extract_quantities(medication_text)
            
            # Extract dates and ages from full text (not just medication section)
            entities['dates'] = self._extract_dates(text)
            entities['ages'] = self._extract_ages(text)
            
            # Extract drug names from medication section only
            entities['drugs'] = self._extract_drug_names(medication_text)
            
            # Extract instructions
            entities['instructions'] = self._extract_instructions(medication_text)
            
            # If spaCy available, refine results
            if self.use_spacy and self.nlp:
                entities = self._refine_with_spacy(medication_text, entities)
            
            logger.info(f"Extracted entities: {sum(len(v) for v in entities.values())} total")
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
        
        return entities
    
    def _extract_medication_section(self, text: str) -> str:
        """
        Extract only the medication/advice section from prescription
        Filters out header, patient info, doctor info
        """
        lines = text.split('\n')
        medication_lines = []
        in_medication_section = False
        
        # Keywords that indicate start of medication section
        medication_markers = ['advice', 'rx', 'prescription', 'medicine', 'medication', 'treatment']
        
        # Keywords to skip (header information)
        skip_keywords = ['mbbs', 'md', 'doctor', 'dr.', 'clinic', 'hospital', 
                        'phone', 'ph:', 'reg', 'registration', 'college',
                        'patient', 'name:', 'age:', 'gender:', 'weight:', 
                        'date:', 'clinical', 'description:', 'diagnosis:']
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Skip empty lines
            if not line_lower:
                continue
            
            # Check if this line starts medication section
            if any(marker in line_lower for marker in medication_markers):
                in_medication_section = True
                continue
            
            # Skip header/patient information
            if any(skip in line_lower for skip in skip_keywords):
                continue
            
            # If we're in medication section, add the line
            if in_medication_section:
                medication_lines.append(line)
        
        # If no medication section found, try to identify lines with medicine patterns
        if not medication_lines:
            logger.warning("No 'Advice' section found, looking for medicine patterns...")
            medicine_prefixes = ['syp', 'tab', 'cap', 'inj', 'oint', 'drops', 'mg', 'ml']
            for line in lines:
                line_lower = line.lower()
                # Skip header lines
                if any(skip in line_lower for skip in skip_keywords):
                    continue
                # Include lines with medicine indicators
                if any(prefix in line_lower for prefix in medicine_prefixes):
                    medication_lines.append(line)
        
        medication_text = '\n'.join(medication_lines)
        logger.info(f"Extracted medication section ({len(medication_lines)} lines)")
        
        return medication_text if medication_text else text  # Fallback to full text
    
    def _extract_dosages(self, text: str) -> List[Entity]:
        """Extract dosage information"""
        dosages = []
        for match in self.dosage_pattern.finditer(text):
            amount, unit = match.groups()
            dosages.append(Entity(
                type='DOSAGE',
                value=f"{amount}{unit}",
                confidence=0.9,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return dosages
    
    def _extract_frequencies(self, text: str) -> List[Entity]:
        """Extract frequency information"""
        frequencies = []
        for match in self.frequency_pattern.finditer(text):
            freq = match.group(1)
            # Expand abbreviations
            expanded = MEDICAL_ABBREVIATIONS.get(freq.upper(), freq)
            frequencies.append(Entity(
                type='FREQUENCY',
                value=expanded,
                confidence=0.85,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return frequencies
    
    def _extract_durations(self, text: str) -> List[Entity]:
        """Extract duration information"""
        durations = []
        for match in self.duration_pattern.finditer(text):
            number, unit = match.groups()
            durations.append(Entity(
                type='DURATION',
                value=f"{number} {unit}",
                confidence=0.85,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return durations
    
    def _extract_routes(self, text: str) -> List[Entity]:
        """Extract route of administration"""
        routes = []
        for match in self.route_pattern.finditer(text):
            route = match.group(1)
            # Expand abbreviations
            expanded = MEDICAL_ABBREVIATIONS.get(route.upper(), route)
            routes.append(Entity(
                type='ROUTE',
                value=expanded,
                confidence=0.8,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return routes
    
    def _extract_quantities(self, text: str) -> List[Entity]:
        """Extract quantity information"""
        quantities = []
        for match in self.quantity_pattern.finditer(text):
            qty = match.group(1)
            quantities.append(Entity(
                type='QUANTITY',
                value=qty,
                confidence=0.8,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return quantities
    
    def _extract_dates(self, text: str) -> List[Entity]:
        """Extract dates"""
        dates = []
        for match in self.date_pattern.finditer(text):
            date = match.group(1)
            dates.append(Entity(
                type='DATE',
                value=date,
                confidence=0.9,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return dates
    
    def _extract_ages(self, text: str) -> List[Entity]:
        """Extract age information"""
        ages = []
        for match in self.age_pattern.finditer(text):
            age = match.group(1)
            ages.append(Entity(
                type='AGE',
                value=f"{age} years",
                confidence=0.85,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return ages
    
    def _extract_drug_names(self, text: str) -> List[Entity]:
        """
        Extract drug names - improved to recognize medicine patterns
        Looks for: Syp DRUGNAME, Tab DRUGNAME, Cap DRUGNAME, etc.
        """
        drugs = []
        
        # **NEW: Pattern for medicines with prefixes**
        # Matches: Syp CALPOL, Tab Paracetamol, Cap Amoxicillin, Inj Insulin, etc.
        medicine_pattern = re.compile(
            r'\b(syp|tab|cap|inj|oint|drops|sachet|powder|cream|gel|lotion|spray)\s+([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+)?)',
            re.IGNORECASE
        )
        
        for match in medicine_pattern.finditer(text):
            prefix = match.group(1)
            drug_name = match.group(2).strip()
            
            # Validate it's not a common non-drug word
            if drug_name.lower() not in ['and', 'the', 'for', 'with', 'after', 'before']:
                drugs.append(Entity(
                    type='DRUG_NAME',
                    value=drug_name,
                    confidence=0.9,  # High confidence for pattern-matched drugs
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
                logger.info(f"Found medicine: {prefix} {drug_name}")
        
        # If no pattern matches, fall back to looking for capitalized words
        # But only in medication context
        if not drugs:
            # Words that are likely drug names (capitalized, not common words)
            potential_drugs = self.drug_pattern.findall(text)
            
            # Filter out common non-drug words
            common_words = {'Patient', 'Doctor', 'Name', 'Date', 'Age', 'Address', 'Phone', 
                           'Prescription', 'Rx', 'Dr', 'Mr', 'Mrs', 'Ms', 'The', 'For', 'With',
                           'Advice', 'Clinical', 'Description', 'Weight', 'Gender', 'Reg',
                           'College', 'Hospital', 'Clinic', 'Medical', 'Health'}
            
            for drug in potential_drugs:
                if drug not in common_words and len(drug) > 3:
                    drugs.append(Entity(
                        type='DRUG_NAME',
                        value=drug,
                        confidence=0.6,  # Lower confidence for non-pattern matches
                        start_pos=0,
                        end_pos=0
                    ))
        
        return drugs
    
    def _extract_instructions(self, text: str) -> List[Entity]:
        """Extract special instructions"""
        instructions = []
        
        # Look for common instruction phrases
        instruction_keywords = [
            'before meals', 'after meals', 'with food', 'on empty stomach',
            'at bedtime', 'in the morning', 'as needed', 'if needed',
            'for pain', 'for fever', 'for infection'
        ]
        
        for keyword in instruction_keywords:
            if keyword in text.lower():
                instructions.append(Entity(
                    type='INSTRUCTION',
                    value=keyword,
                    confidence=0.75,
                    start_pos=0,
                    end_pos=0
                ))
        
        return instructions
    
    def _refine_with_spacy(self, text: str, entities: Dict) -> Dict:
        """Use spaCy to refine entity extraction"""
        if not self.nlp:
            return entities
        
        try:
            doc = self.nlp(text)
            
            # Extract named entities
            for ent in doc.ents:
                if ent.label_ in ['CHEMICAL', 'DRUG']:
                    # Add to drugs if not already found
                    drug_values = [e.value for e in entities['drugs']]
                    if ent.text not in drug_values:
                        entities['drugs'].append(Entity(
                            type='DRUG_NAME',
                            value=ent.text,
                            confidence=0.85,
                            start_pos=ent.start_char,
                            end_pos=ent.end_char
                        ))
            
            logger.info(f"spaCy refined extraction, added {len(doc.ents)} entities")
            
        except Exception as e:
            logger.warning(f"spaCy refinement failed: {e}")
        
        return entities
    
    def structure_prescription(self, text: str, entities: Dict) -> List[Dict]:
        """
        Structure entities into prescription items
        
        Returns:
            List of prescription items, each with drug, dosage, frequency, etc.
        """
        # Group entities into prescription items
        # This is simplified - in production, use more sophisticated grouping
        
        items = []
        
        for drug in entities.get('drugs', []):
            item = {
                'drug_name': drug.value,
                'dosage': None,
                'frequency': None,
                'duration': None,
                'route': None,
                'quantity': None,
                'instructions': [],
                'confidence': drug.confidence
            }
            
            # Try to match dosage, frequency, etc. near this drug
            if entities.get('dosages'):
                item['dosage'] = entities['dosages'][0].value if entities['dosages'] else None
            
            if entities.get('frequencies'):
                item['frequency'] = entities['frequencies'][0].value if entities['frequencies'] else None
            
            if entities.get('durations'):
                item['duration'] = entities['durations'][0].value if entities['durations'] else None
            
            if entities.get('routes'):
                item['route'] = entities['routes'][0].value if entities['routes'] else None
            
            if entities.get('quantities'):
                item['quantity'] = entities['quantities'][0].value if entities['quantities'] else None
            
            if entities.get('instructions'):
                item['instructions'] = [inst.value for inst in entities['instructions']]
            
            items.append(item)
        
        return items


# Standalone function
def extract_prescription_entities(text: str, use_spacy=False):
    """
    Quick function to extract entities from prescription text
    
    Args:
        text: OCR extracted text
        use_spacy: Use spaCy for better accuracy (requires installation)
        
    Returns:
        Dict of extracted entities
    """
    ner = MedicalNER(use_spacy=use_spacy)
    return ner.extract_entities(text)
