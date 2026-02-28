"""
Database Models for VedaVision
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    experience_level = db.Column(db.String(20), default='Beginner')
    goals = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    routines = db.relationship('SavedRoutine', backref='user', lazy=True, cascade='all, delete-orphan')
    sessions = db.relationship('YogaSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'

class SavedRoutine(db.Model):
    __tablename__ = 'saved_routines'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    routine_name = db.Column(db.String(200), nullable=False)
    routine_data = db.Column(db.Text, nullable=False)  # JSON string
    goal = db.Column(db.String(200))
    duration = db.Column(db.Integer)
    experience_level = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_favorite = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<SavedRoutine {self.routine_name}>'

class YogaSession(db.Model):
    __tablename__ = 'yoga_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pose_name = db.Column(db.String(100), nullable=False)
    duration_seconds = db.Column(db.Integer)
    average_score = db.Column(db.Float)
    max_score = db.Column(db.Float)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<YogaSession {self.pose_name} - Score: {self.average_score}>'
