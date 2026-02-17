"""
Prescription OCR Flask Routes - Hosted API + Gemini Vision Fallback
"""

from flask import request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import uuid
import logging
import sys
import traceback
import base64
import requests
from datetime import datetime

# Import models
from models import db, Prescription, PrescriptionItem, get_or_create_default_user

logger = logging.getLogger(__name__)

# Global reference
gemini_ocr = None

# Hosted API endpoint (primary)
HOSTED_OCR_API = "https://us-central1-medimatch-f446c.cloudfunctions.net/gemini_medical_assistant"

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_gemini_ocr():
    """Get or initialize Gemini Vision OCR (fallback)"""
    global gemini_ocr
    if gemini_ocr is None:
        try:
            print("[GEMINI INIT] Initializing Gemini Vision (fallback)...", file=sys.stderr)
            from prescription_ocr.gemini_vision import GeminiVisionOCR
            gemini_ocr = GeminiVisionOCR()
            print("[GEMINI INIT] ✅ Gemini Vision initialized successfully!", file=sys.stderr)
        except Exception as e:
            print(f"[GEMINI INIT] ❌ Failed to initialize: {e}", file=sys.stderr)
            traceback.print_exc()
            gemini_ocr = None
    return gemini_ocr

def process_with_hosted_api(image_path):
    """
    Process prescription image using hosted MediMatch API (primary method).
    Converts image to base64 and sends to hosted endpoint.
    """
    try:
        print(f"[HOSTED API] Processing image: {image_path}", file=sys.stderr)

        # Read and encode image to base64
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')

        print(f"[HOSTED API] Image encoded, size: {len(base64_image)} chars", file=sys.stderr)

        # Send to hosted API
        response = requests.post(
            HOSTED_OCR_API,
            headers={'Content-Type': 'application/json'},
            json={'image_base64': base64_image},
            timeout=60  # 60 second timeout
        )

        print(f"[HOSTED API] Response status: {response.status_code}", file=sys.stderr)

        if response.status_code == 200:
            result = response.json()
            print(f"[HOSTED API] ✅ Success! Response received.", file=sys.stderr)

            # Parse the response - hosted API returns 'response' field with formatted text
            if 'response' in result:
                return parse_hosted_api_response(result['response'])
            return result
        else:
            print(f"[HOSTED API] ❌ Error: {response.status_code} - {response.text}", file=sys.stderr)
            return None

    except requests.exceptions.Timeout:
        print("[HOSTED API] ❌ Request timed out", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[HOSTED API] ❌ Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return None

def parse_hosted_api_response(response_text):
    """
    Parse the formatted text response from hosted API into structured data.
    The hosted API returns formatted text with medicine info.
    """
    result = {
        'raw_text': response_text,
        'overall_confidence': 0.85,   
        'prescription_items': [],
        'source': 'hosted_api'
    }

    # Try to extract medicine names and details from the response
    lines = response_text.split('\n')
    current_item = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for medicine names (usually in bold or numbered)
        if line.startswith('**') and line.endswith('**'):
            # Bold text - likely medicine name
            if current_item:
                result['prescription_items'].append(current_item)
            current_item = {
                'drug_name': line.strip('*').strip(),
                'dosage': '',
                'frequency': '',
                'duration': '',
                'confidence': 0.85
            }
        elif current_item:
            # Try to extract dosage, frequency, duration from subsequent lines
            line_lower = line.lower()
            if 'mg' in line_lower or 'ml' in line_lower or 'tablet' in line_lower:
                current_item['dosage'] = line
            elif 'daily' in line_lower or 'times' in line_lower or 'once' in line_lower or 'twice' in line_lower:
                current_item['frequency'] = line
            elif 'day' in line_lower or 'week' in line_lower or 'month' in line_lower:
                current_item['duration'] = line

    # Add last item
    if current_item:
        result['prescription_items'].append(current_item)

    return result

def register_prescription_routes(app):
    """Register prescription OCR routes"""
    
    UPLOAD_FOLDER = 'static/uploads/prescriptions'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # Try init on startup
    get_gemini_ocr()
    
    @app.route('/prescription-ocr')
    def prescription_ocr_page():
        return render_template('prescription_ocr.html')
    
    @app.route('/api/prescription/upload', methods=['POST'])
    def upload_prescription():
        # Get API mode from request (default to 'hosted')
        api_mode = request.form.get('api_mode', 'hosted')
        print(f"[PRESCRIPTION] Upload endpoint called (Mode: {api_mode})", file=sys.stderr)

        if 'prescription_image' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['prescription_image']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400

        try:
            # Save file
            prescription_id = str(uuid.uuid4())
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{prescription_id}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            print(f"[PRESCRIPTION] Saved to {filepath}", file=sys.stderr)

            result = None

            if api_mode == 'local':
                # User chose local Gemini Vision (no OCR engine selection - always use Gemini)
                print("[PRESCRIPTION] Using local Gemini Vision (user selected)...", file=sys.stderr)
                ocr = get_gemini_ocr()
                if ocr:
                    result = ocr.process_image(filepath)
                    if result and 'error' not in result:
                        result['source'] = 'local_gemini'
                    else:
                        return jsonify({'error': result.get('error', 'Gemini Vision processing failed')}), 500
                else:
                    return jsonify({'error': 'Local Gemini Vision not available. Check GEMINI_API_KEY in .env'}), 500
            else:
                # Default: Try hosted API first, fallback to local
                print("[PRESCRIPTION] Trying hosted MediMatch API (primary)...", file=sys.stderr)
                result = process_with_hosted_api(filepath)

                # FALLBACK: If hosted API fails, use local Gemini Vision
                if result is None:
                    print("[PRESCRIPTION] Hosted API failed, falling back to local Gemini Vision...", file=sys.stderr)
                    ocr = get_gemini_ocr()
                    if ocr:
                        result = ocr.process_image(filepath)
                        if result and 'error' not in result:
                            result['source'] = 'local_gemini_fallback'
                        else:
                            return jsonify({'error': 'Both hosted API and local Gemini failed. ' + result.get('error', '')}), 500
                    else:
                        return jsonify({'error': 'Both hosted API and local Gemini failed. Check configuration.'}), 500

            # Add metadata for frontend
            result['prescription_id'] = prescription_id
            result['image_url'] = f'/static/uploads/prescriptions/{filename}'

            # === SAVE TO DATABASE (Feature 3) ===
            try:
                user = get_or_create_default_user()
                
                new_prescription = Prescription(
                    user_id=user.id,
                    image_path=filename,
                    upload_date=datetime.utcnow(),
                    ocr_confidence=result.get('overall_confidence', 0.0),
                    api_source=result.get('source', 'unknown'),
                    raw_text=result.get('raw_text', ''),
                    doctor_name=None, # Not extracted yet
                    notes=request.form.get('notes', '')
                )
                db.session.add(new_prescription)
                db.session.flush() # Get ID
                
                # Save items
                items = result.get('prescription_items', [])
                for item in items:
                    p_item = PrescriptionItem(
                        prescription_id=new_prescription.id,
                        drug_name=item.get('drug_name', 'Unknown'),
                        dosage=item.get('dosage'),
                        frequency=item.get('frequency'),
                        duration=item.get('duration'),
                        instructions=item.get('instructions')
                    )
                    db.session.add(p_item)
                
                db.session.commit()
                result['db_id'] = new_prescription.id
                print(f"[DB] Saved prescription {new_prescription.id} for user {user.username}", file=sys.stderr)
                
            except Exception as db_err:
                db.session.rollback()
                print(f"[DB ERROR] Failed to save prescription: {db_err}", file=sys.stderr)
                # Do not fail request, just log error
                result['db_error'] = str(db_err)

            print(f"[PRESCRIPTION] Completed via {result.get('source', 'unknown')}. Found {len(result.get('prescription_items', []))} items.", file=sys.stderr)

            return jsonify(result)

        except Exception as e:
            print(f"[PRESCRIPTION] Error: {e}", file=sys.stderr)
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/prescription/history')
    def get_prescription_history():
        """Get uploaded prescription history for current user"""
        try:
            user = get_or_create_default_user()
            # Sort by newest first
            prescriptions = Prescription.query.filter_by(user_id=user.id).order_by(Prescription.upload_date.desc()).all()
            
            return jsonify({
                'success': True,
                'count': len(prescriptions),
                'prescriptions': [p.to_dict() for p in prescriptions]
            })
        except Exception as e:
            print(f"[HISTORY ERROR] {e}", file=sys.stderr)
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/prescription/<int:id>')
    def get_prescription_detail(id):
        """Get details of a specific prescription"""
        try:
            user = get_or_create_default_user()
            prescription = Prescription.query.filter_by(id=id, user_id=user.id).first()
            if not prescription:
                return jsonify({'error': 'Not found'}), 404
            
            return jsonify(prescription.to_dict())
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/drug/insights', methods=['POST'])
    def get_drug_insights():
        """Get AI-powered insights for a specific drug using Web RAG"""
        data = request.get_json()
        drug_name = data.get('drug_name')
        
        if not drug_name:
            return jsonify({'error': 'Drug name required'}), 400
            
        try:
            print(f"[RAG] Fetching external insights for {drug_name}...", file=sys.stderr)
            from rag_engine import get_external_insights
            insights = get_external_insights(drug_name)
            return jsonify(insights)
        except Exception as e:
            print(f"[RAG] Error: {e}", file=sys.stderr)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/prescription/check-interactions', methods=['POST'])
    def check_prescription_interactions():
        """Check drug-drug interactions"""
        data = request.get_json()
        drugs = data.get('drugs', [])
        
        if not drugs or len(drugs) < 2:
            return jsonify({'interactions': [], 'message': 'Need at least 2 drugs'})
        
        # Simplified interaction checker (keep existing logic for speed, or upgrade to RAG later)
        interactions = []
        dangerous_combinations = {
            ('aspirin', 'warfarin'): 'Increased bleeding risk',
            ('aspirin', 'ibuprofen'): 'Increased GI bleeding risk',
            ('metformin', 'alcohol'): 'Risk of lactic acidosis',
        }
        
        for i, drug1 in enumerate(drugs):
            for drug2 in drugs[i+1:]:
                key1 = (drug1.lower(), drug2.lower())
                key2 = (drug2.lower(), drug1.lower())
                
                if key1 in dangerous_combinations:
                    interactions.append({
                        'drug1': drug1,
                        'drug2': drug2,
                        'severity': 'major',
                        'description': dangerous_combinations[key1]
                    })
                elif key2 in dangerous_combinations:
                    interactions.append({
                        'drug1': drug2,
                        'drug2': drug1,
                        'severity': 'major',
                        'description': dangerous_combinations[key2]
                    })
        
        return jsonify({
            'interactions': interactions,
            'drugs_checked': drugs
        })

    logger.info("✅ MediMatch Prescription Routes Registered (Hosted API + Gemini Fallback)")
