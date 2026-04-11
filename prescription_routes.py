"""
Prescription OCR Flask Routes - Gemini Vision (local) only
"""

from flask import request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import uuid
import logging
import sys
import traceback
from datetime import datetime

# Import models
from models import db, Prescription, PrescriptionItem, get_or_create_default_user

logger = logging.getLogger(__name__)

# Global reference
gemini_ocr = None

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
        print("[PRESCRIPTION] Upload endpoint called (Local Gemini only)", file=sys.stderr)

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

            # Always use local Gemini Vision
            ocr = get_gemini_ocr()
            if not ocr:
                return jsonify({'error': 'Local Gemini Vision not available. Check GEMINI_API_KEY in .env'}), 500

            result = ocr.process_image(filepath)
            if not result or 'error' in result:
                return jsonify({'error': result.get('error', 'Gemini Vision processing failed')}), 500

            result['source'] = 'local_gemini'

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

    @app.route('/api/expiry/check', methods=['POST'])
    def check_expiry():
        """Stateless Endpoint: Check expiry using CAMEE multimodal algorithm"""
        try:
            print("[CAMEE] Stateless expiry check requested", file=sys.stderr)
            
            # Need to get image_front and image_back
            if 'image_front' not in request.files or 'image_back' not in request.files:
                return jsonify({'error': 'Both image_front and image_back are required for maximum accuracy'}), 400
                
            files = []
            temps = []
            
            # Extract front image
            f_front = request.files['image_front']
            if allowed_file(f_front.filename):
                files.append(f_front)
                    
            # Extract back image
            f_back = request.files['image_back']
            if allowed_file(f_back.filename):
                files.append(f_back)
                    
            if not files:
                return jsonify({'error': 'Valid image not provided'}), 400
                
            from prescription_ocr.expiry_extractor import CAMEEVerifier
            verifier = CAMEEVerifier()
            
            # Temporarily save images to pass paths to extraction algorithms
            upload_dir = app.config['UPLOAD_FOLDER']
            for f in files:
                ext = f.filename.rsplit('.', 1)[1].lower()
                temp_filename = f"temp_camee_{uuid.uuid4().hex[:8]}.{ext}"
                temp_path = os.path.join(upload_dir, temp_filename)
                f.save(temp_path)
                temps.append(temp_path)
                
            # Perform verification
            result = verifier.process_images(temps)
            
            # Important: Stateless cleanup, delete temporary files immediately
            for temp_path in temps:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
            return jsonify(result)
            
        except Exception as e:
            # Clean up if failed
            for temp_path in temps:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            print(f"[CAMEE ERROR] {e}", file=sys.stderr)
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    logger.info("✅ MediMatch Prescription Routes Registered (Hosted API + Gemini Fallback + CAMEE)")
