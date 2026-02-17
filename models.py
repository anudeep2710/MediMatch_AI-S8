"""
MediMatch Phase II - Database Models
SQLAlchemy ORM models for personalization features
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
import json

db = SQLAlchemy()

class User(db.Model):
    """User profile for personalization"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    preferences = db.Column(db.Text, default='{}')  # JSON string
    
    # Relationships
    saved_drugs = db.relationship('SavedDrug', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reminders = db.relationship('MedicationReminder', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    prescriptions = db.relationship('Prescription', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def get_preferences(self):
        """Parse preferences JSON"""
        try:
            return json.loads(self.preferences)
        except:
            return {}
    
    def set_preferences(self, prefs_dict):
        """Set preferences from dictionary"""
        self.preferences = json.dumps(prefs_dict)


class SavedDrug(db.Model):
    """User's bookmarked/favorite drugs"""
    __tablename__ = 'saved_drugs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    drug_name = db.Column(db.String(255), nullable=False)
    drug_id = db.Column(db.String(100), nullable=True)  # External DB ID
    smiles = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), default='General')
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reminders = db.relationship('MedicationReminder', backref='saved_drug', lazy='dynamic')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'drug_name', name='unique_user_drug'),
        Index('idx_saved_drugs_user', 'user_id'),
        Index('idx_saved_drugs_name', 'drug_name'),
    )
    
    def __repr__(self):
        return f'<SavedDrug {self.drug_name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'drug_name': self.drug_name,
            'drug_id': self.drug_id,
            'smiles': self.smiles,
            'notes': self.notes,
            'category': self.category,
            'saved_at': self.saved_at.isoformat()
        }


class MedicationReminder(db.Model):
    """Medication schedules and reminders"""
    __tablename__ = 'medication_reminders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    saved_drug_id = db.Column(db.Integer, db.ForeignKey('saved_drugs.id'), nullable=True)
    medication_name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(100), nullable=True)
    frequency = db.Column(db.String(50), nullable=True)
    time_of_day = db.Column(db.String(200), nullable=True)  # JSON array: ["08:00", "20:00"]
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_reminded_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_reminders_user_active', 'user_id', 'is_active'),
        Index('idx_reminders_start_date', 'start_date'),
    )
    
    def __repr__(self):
        return f'<Reminder {self.medication_name} @ {self.time_of_day}>'
    
    def get_times(self):
        """Parse time_of_day JSON"""
        try:
            return json.loads(self.time_of_day)
        except:
            return []
    
    def set_times(self, times_list):
        """Set times from list"""
        self.time_of_day = json.dumps(times_list)
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'medication_name': self.medication_name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'times': self.get_times(),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active,
            'notes': self.notes
        }


class Prescription(db.Model):
    """Uploaded prescription metadata"""
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    ocr_confidence = db.Column(db.Float, nullable=True)
    api_source = db.Column(db.String(50), nullable=True)
    raw_text = db.Column(db.Text, nullable=True)
    doctor_name = db.Column(db.String(255), nullable=True)
    prescription_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    items = db.relationship('PrescriptionItem', backref='prescription', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_prescriptions_user_date', 'user_id', 'upload_date'),
    )
    
    def __repr__(self):
        return f'<Prescription {self.id} uploaded {self.upload_date}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'image_path': self.image_path,
            'upload_date': self.upload_date.isoformat(),
            'ocr_confidence': self.ocr_confidence,
            'api_source': self.api_source,
            'raw_text': self.raw_text,
            'doctor_name': self.doctor_name,
            'prescription_date': self.prescription_date.isoformat() if self.prescription_date else None,
            'notes': self.notes,
            'items': [item.to_dict() for item in self.items]
        }


class PrescriptionItem(db.Model):
    """Individual medications from each prescription"""
    __tablename__ = 'prescription_items'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False)
    drug_name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(100), nullable=True)
    frequency = db.Column(db.String(100), nullable=True)
    duration = db.Column(db.String(100), nullable=True)
    route = db.Column(db.String(50), nullable=True)
    instructions = db.Column(db.Text, nullable=True)
    
    __table_args__ = (
        Index('idx_prescription_items_prescription', 'prescription_id'),
    )
    
    def __repr__(self):
        return f'<PrescriptionItem {self.drug_name}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'drug_name': self.drug_name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration,
            'route': self.route,
            'instructions': self.instructions
        }


# Helper function to create default user if none exists
def get_or_create_default_user():
    """Get the current user based on Firebase UID header or fallback to default"""
    from flask import request
    
    firebase_uid = None
    try:
        # Check if we are in a request context
        if request:
            firebase_uid = request.headers.get('X-Firebase-UID')
    except RuntimeError:
        # Outside of request context (e.g., init scripts)
        pass
        
    username = 'default'
    if firebase_uid:
        username = f"firebase_{firebase_uid}"
        
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(
            username=username,
            email=None,
            preferences=json.dumps({
                'theme': 'light',
                'notifications_enabled': True
            })
        )
        db.session.add(user)
        db.session.commit()
    return user
