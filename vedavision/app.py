"""
VedaVision - Full Web Application
Flask backend with yoga coach integration
"""

from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import json
from datetime import datetime
import os
from dotenv import load_dotenv
from google import genai
from models import db, User, SavedRoutine, YogaSession

# Load environment variables
load_dotenv()

# Set API key as environment variable for genai.Client()
if os.getenv('GEMINI_API_KEY'):
    os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vedavision-yoga-coach-2026-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vedavision.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Global yoga coach instance
yoga_coach = None
camera = None
gemini_assistant = None

class YogaCoachAPI:
    def __init__(self):
        """Initialize AI-powered yoga pose detector"""
        
        # Create BlazePose landmarker
        base_options = python.BaseOptions(model_asset_path='pose_landmarker_heavy.task')
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.7,
            min_pose_presence_confidence=0.7,
            min_tracking_confidence=0.7)
        self.detector = vision.PoseLandmarker.create_from_options(options)
        
        self.current_pose = None
        self.frame_timestamp = 0
        self.score_buffer = []
        self.landmark_history = {}
        self.alpha = 0.3
        self.max_jump_threshold = 0.15
        self.score_weights = [0.1, 0.15, 0.2, 0.25, 0.3]
        self.pose_start_time = None
        self.best_score = 0
        self.session_data = []
        
        print("✓ YogaCoach API initialized!")
    
    def get_landmark_3d(self, lm, idx):
        """Get 3D landmark with Temporal Filtering"""
        if idx >= len(lm) or lm[idx].visibility < 0.7 or lm[idx].presence < 0.7:
            return None
        
        current_pos = np.array([lm[idx].x, lm[idx].y, lm[idx].z], dtype=np.float64)
        
        if idx in self.landmark_history:
            prev_pos = self.landmark_history[idx]
            movement = np.linalg.norm(current_pos - prev_pos)
            
            if movement > self.max_jump_threshold:
                filtered_pos = self.alpha * 0.3 * current_pos + (1 - self.alpha * 0.3) * prev_pos
            else:
                filtered_pos = self.alpha * current_pos + (1 - self.alpha) * prev_pos
            
            self.landmark_history[idx] = filtered_pos
            return filtered_pos.tolist()
        else:
            self.landmark_history[idx] = current_pos
            return current_pos.tolist()
    
    def calc_angle_3d(self, a, b, c):
        """Calculate 3D angle using dot product"""
        if not all([a, b, c]) or len(a) < 3 or len(b) < 3 or len(c) < 3:
            return 0
        
        a = np.array(a, dtype=np.float64)
        b = np.array(b, dtype=np.float64)
        c = np.array(c, dtype=np.float64)
        
        ba = a - b
        bc = c - b
        
        dot_product = np.dot(ba, bc)
        magnitude_ba = np.linalg.norm(ba)
        magnitude_bc = np.linalg.norm(bc)
        
        if magnitude_ba == 0 or magnitude_bc == 0:
            return 0
        
        cos_angle = np.clip(dot_product / (magnitude_ba * magnitude_bc), -1.0, 1.0)
        return np.arccos(cos_angle) * 180.0 / np.pi
    
    def evaluate_pose(self, landmarks):
        """Evaluate current yoga pose - complete implementation"""
        if not landmarks or not self.current_pose:
            return [], 0
        
        feedback = []
        score = 60
        lm = landmarks[0]
        
        # Check landmark visibility
        visible_count = sum(1 for l in lm if l.visibility > 0.7 and l.presence > 0.7)
        if visible_count < 12:
            return ["⚠ Move closer - need clear view"], 25
        
        try:
            # Extract key body points with temporal filtering
            l_shoulder = self.get_landmark_3d(lm, 11)
            r_shoulder = self.get_landmark_3d(lm, 12)
            l_elbow = self.get_landmark_3d(lm, 13)
            r_elbow = self.get_landmark_3d(lm, 14)
            l_wrist = self.get_landmark_3d(lm, 15)
            r_wrist = self.get_landmark_3d(lm, 16)
            l_hip = self.get_landmark_3d(lm, 23)
            r_hip = self.get_landmark_3d(lm, 24)
            l_knee = self.get_landmark_3d(lm, 25)
            r_knee = self.get_landmark_3d(lm, 26)
            l_ankle = self.get_landmark_3d(lm, 27)
            r_ankle = self.get_landmark_3d(lm, 28)
            l_foot = self.get_landmark_3d(lm, 31)
            r_foot = self.get_landmark_3d(lm, 32)
            
            # Precision checks
            if l_shoulder and r_shoulder:
                shoulder_tilt = abs(l_shoulder[1] - r_shoulder[1])
                if shoulder_tilt > 0.08:
                    feedback.append("⚠ Level shoulders")
                    score -= 15
                elif shoulder_tilt < 0.03:
                    feedback.append("✓ Shoulders level!")
                    score += 12
            
            if l_hip and r_hip:
                hip_tilt = abs(l_hip[1] - r_hip[1])
                if hip_tilt > 0.08:
                    feedback.append("⚠ Level hips")
                    score -= 15
                elif hip_tilt < 0.03:
                    feedback.append("✓ Hips level!")
                    score += 12
            
            # Pose-specific evaluation
            if self.current_pose == 'warrior2':
                if l_ankle and r_ankle and l_foot and r_foot:
                    stance_width = max(abs(l_ankle[0] - r_ankle[0]), abs(l_foot[0] - r_foot[0]))
                    if stance_width < 0.35:
                        feedback.append("⚠ Stance too narrow")
                        score -= 20
                    elif stance_width > 0.45:
                        feedback.append("✓ Perfect stance!")
                        score += 15
                    else:
                        score += 8
                
                if l_knee and l_hip and l_ankle:
                    angle = self.calc_angle_3d(l_hip, l_knee, l_ankle)
                    if angle > 135:
                        feedback.append("⚠ BEND front knee to 90°")
                        score -= 30
                    elif 88 <= angle <= 92:
                        feedback.append("✓ PERFECT 90° knee!")
                        score += 20
                    elif 82 <= angle <= 98:
                        feedback.append("✓ Great knee angle!")
                        score += 12
                    else:
                        feedback.append("→ Adjust knee bend")
                        score += 5
                
                if r_knee and r_hip and r_ankle:
                    back_leg = self.calc_angle_3d(r_hip, r_knee, r_ankle)
                    if back_leg < 155:
                        feedback.append("⚠ Straighten back leg")
                        score -= 18
                    elif back_leg >= 170:
                        feedback.append("✓ Back leg perfect!")
                        score += 15
            
            elif self.current_pose == 'tree':
                if l_knee and r_knee and l_hip and r_hip:
                    left_knee_height = l_hip[1] - l_knee[1]
                    right_knee_height = r_hip[1] - r_knee[1]
                    
                    if not (left_knee_height > 0.15 or right_knee_height > 0.15):
                        feedback.append("⚠ RAISE one leg high")
                        score -= 35
                    else:
                        feedback.append("✓ Leg raised!")
                        score += 15
                
                if r_knee and r_hip and r_ankle:
                    leg = self.calc_angle_3d(r_hip, r_knee, r_ankle)
                    if leg >= 172:
                        feedback.append("✓ Standing leg perfect!")
                        score += 18
                    elif leg < 155:
                        feedback.append("⚠ Straighten standing leg")
                        score -= 20
            
            elif self.current_pose == 'mountain':
                if l_knee and l_hip and l_ankle and r_knee and r_hip and r_ankle:
                    left_leg = self.calc_angle_3d(l_hip, l_knee, l_ankle)
                    right_leg = self.calc_angle_3d(r_hip, r_knee, r_ankle)
                    if left_leg >= 165 and right_leg >= 165:
                        feedback.append("✓ Perfect alignment!")
                        score += 20
                    elif left_leg < 150 or right_leg < 150:
                        feedback.append("⚠ Straighten both legs")
                        score -= 20
            
            elif self.current_pose == 'triangle':
                if l_ankle and r_ankle:
                    stance = abs(l_ankle[0] - r_ankle[0])
                    if stance < 0.35:
                        feedback.append("⚠ Widen stance")
                        score -= 20
                    else:
                        score += 10
                
                if l_knee and l_hip and l_ankle and r_knee and r_hip and r_ankle:
                    left_leg = self.calc_angle_3d(l_hip, l_knee, l_ankle)
                    right_leg = self.calc_angle_3d(r_hip, r_knee, r_ankle)
                    if left_leg >= 165 and right_leg >= 165:
                        feedback.append("✓ Legs straight!")
                        score += 20
                    elif left_leg < 150 or right_leg < 150:
                        feedback.append("⚠ STRAIGHTEN legs")
                        score -= 25
            
            elif self.current_pose == 'downdog':
                if l_hip and l_shoulder:
                    hip_height = l_shoulder[1] - l_hip[1]
                    if hip_height <= 0:
                        feedback.append("⚠ LIFT hips high")
                        score -= 35
                    elif hip_height > 0.20:
                        feedback.append("✓ Perfect inverted V!")
                        score += 25
                    else:
                        feedback.append("→ Lift hips higher")
                        score += 10
        
        except:
            feedback = ["Analyzing..."]
        
        if len(feedback) == 0:
            feedback.append("→ Getting into position...")
        
        # Score smoothing
        self.score_buffer.append(score)
        if len(self.score_buffer) > 5:
            self.score_buffer.pop(0)
        
        if len(self.score_buffer) == 5:
            smoothed_score = int(sum(s * w for s, w in zip(self.score_buffer, self.score_weights)))
        else:
            smoothed_score = int(sum(self.score_buffer) / len(self.score_buffer))
        
        final_score = max(0, min(100, smoothed_score))
        
        if final_score > self.best_score:
            self.best_score = final_score
        
        return feedback, final_score
    
    def draw_skeleton(self, frame, landmarks):
        """Draw pose skeleton on frame"""
        h, w, _ = frame.shape
        lm = landmarks[0]
        
        # Skeleton connections
        connections = [
            (11, 12), (11, 23), (12, 24), (23, 24),  # Torso
            (11, 13), (13, 15), (12, 14), (14, 16),  # Arms
            (23, 25), (25, 27), (27, 31),  # Left leg
            (24, 26), (26, 28), (28, 32),  # Right leg
        ]
        
        # Draw lines
        for start, end in connections:
            if start < len(lm) and end < len(lm):
                if lm[start].visibility > 0.5 and lm[end].visibility > 0.5:
                    pt1 = (int(lm[start].x * w), int(lm[start].y * h))
                    pt2 = (int(lm[end].x * w), int(lm[end].y * h))
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 3)
        
        # Draw joints
        key_points = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
        for idx in key_points:
            if idx < len(lm) and lm[idx].visibility > 0.5:
                x, y = int(lm[idx].x * w), int(lm[idx].y * h)
                cv2.circle(frame, (x, y), 8, (0, 255, 0), -1)
                cv2.circle(frame, (x, y), 9, (255, 255, 255), 2)
        
        return frame
    
    def process_frame(self, frame):
        """Process video frame and return annotated frame"""
        self.frame_timestamp += 1
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        feedback = []
        score = 0
        
        try:
            result = self.detector.detect_for_video(mp_img, self.frame_timestamp)
            
            if result.pose_landmarks:
                frame = self.draw_skeleton(frame, result.pose_landmarks)
                
                if self.current_pose:
                    feedback, score = self.evaluate_pose(result.pose_landmarks)
                    
                    # Add score overlay on frame
                    h, w, _ = frame.shape
                    cv2.putText(frame, f"Score: {score}%", (20, 50),
                               cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 0), 2)
                    
                    # Add feedback text
                    y = 100
                    for msg in feedback[:3]:
                        cv2.putText(frame, msg, (20, y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                        y += 40
        except Exception as e:
            print(f"Frame processing error: {e}")
        
        return frame, score, feedback

class GeminiAssistant:
    def __init__(self):
        """Initialize Gemini AI for personalized routine generation"""
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key or api_key == 'your_gemini_api_key_here' or api_key == 'your_api_key_here':
            self.client = None
            return
        
        try:
            # The client gets the API key from the environment variable GEMINI_API_KEY
            self.client = genai.Client()
        except Exception as e:
            self.client = None
    
    def generate_routine(self, user_goal, experience_level, duration, focus_areas=None):
        """Generate a personalized yoga routine based on user goals"""
        if not self.client:
            return {
                'error': 'AI routine generator is currently unavailable. Please contact support.',
                'routine': None
            }
        
        try:
            # Build the prompt
            prompt = f"""As a professional yoga instructor, create a personalized yoga routine with the following requirements:

User Goal: {user_goal}
Experience Level: {experience_level}
Duration: {duration} minutes
Focus Areas: {', '.join(focus_areas) if focus_areas else 'Full body'}

Please provide a structured routine in JSON format with the following structure:
{{
    "routine_name": "A descriptive name for this routine",
    "description": "Brief description of the routine and its benefits",
    "total_duration": {duration},
    "difficulty": "{experience_level}",
    "poses": [
        {{
            "pose_name": "Name of the pose",
            "sanskrit_name": "Sanskrit name",
            "duration": "Duration in minutes or breaths",
            "instructions": "Clear, step-by-step instructions",
            "benefits": "Key benefits of this pose",
            "modifications": "Easier variations for beginners"
        }}
    ],
    "tips": ["General tips for this routine"],
    "breathing": "Breathing guidance for this practice"
}}

Focus on poses suitable for {experience_level} level. Include warm-up, main sequence, and cool-down/relaxation."""

            response = self.client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )
            
            # Extract JSON from response
            text = response.text
            
            # Try to find JSON in the response
            if '```json' in text:
                json_start = text.find('```json') + 7
                json_end = text.find('```', json_start)
                json_text = text[json_start:json_end].strip()
            elif '```' in text:
                json_start = text.find('```') + 3
                json_end = text.find('```', json_start)
                json_text = text[json_start:json_end].strip()
            else:
                json_text = text.strip()
            
            try:
                routine = json.loads(json_text)
                return {
                    'success': True,
                    'routine': routine
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, return as text
                return {
                    'success': True,
                    'routine': {
                        'routine_name': 'Personalized Practice',
                        'description': text,
                        'raw_text': True
                    }
                }
            
        except Exception as e:
            print(f"Error generating routine: {e}")
            return {
                'error': f'Failed to generate routine: {str(e)}',
                'routine': None
            }

# Routes
# Public routes (accessible without login)
@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/features')
def features():
    """Features page"""
    return render_template('features.html')

# Authentication routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name', '')
        
        # Validation
        if not username or not email or not password:
            if request.is_json:
                return jsonify({'error': 'All fields are required'}), 400
            flash('All fields are required', 'danger')
            return redirect(url_for('signup'))
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            if request.is_json:
                return jsonify({'error': 'Username already exists'}), 400
            flash('Username already exists', 'danger')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'error': 'Email already registered'}), 400
            flash('Email already registered', 'danger')
            return redirect(url_for('signup'))
        
        # Create new user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            full_name=full_name
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Account created successfully!'})
            flash('Account created successfully! Welcome to VedaVision!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': 'Error creating account'}), 500
            flash('Error creating account. Please try again.', 'danger')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)
        
        if not username or not password:
            if request.is_json:
                return jsonify({'error': 'Username and password required'}), 400
            flash('Username and password required', 'danger')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if request.is_json:
                return jsonify({'success': True, 'redirect': next_page or url_for('dashboard')})
            return redirect(next_page or url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({'error': 'Invalid username or password'}), 401
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Protected routes (require authentication)
@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Get user's recent sessions
    recent_sessions = YogaSession.query.filter_by(user_id=current_user.id)\
        .order_by(YogaSession.started_at.desc()).limit(5).all()
    
    # Get saved routines
    saved_routines = SavedRoutine.query.filter_by(user_id=current_user.id)\
        .order_by(SavedRoutine.created_at.desc()).limit(3).all()
    
    # Calculate stats
    total_sessions = YogaSession.query.filter_by(user_id=current_user.id).count()
    total_routines = SavedRoutine.query.filter_by(user_id=current_user.id).count()
    
    return render_template('dashboard.html',
                         recent_sessions=recent_sessions,
                         saved_routines=saved_routines,
                         total_sessions=total_sessions,
                         total_routines=total_routines)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile"""
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        
        current_user.full_name = data.get('full_name', current_user.full_name)
        current_user.experience_level = data.get('experience_level', current_user.experience_level)
        current_user.goals = data.get('goals', current_user.goals)
        
        try:
            db.session.commit()
            if request.is_json:
                return jsonify({'success': True, 'message': 'Profile updated successfully'})
            flash('Profile updated successfully!', 'success')
        except:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': 'Error updating profile'}), 500
            flash('Error updating profile', 'danger')
    
    return render_template('profile.html')

@app.route('/coach')
@login_required
def coach():
    """Yoga coach page"""
    return render_template('coach.html')

@app.route('/routines')
@login_required
def routines():
    """Personalized routines page"""
    user_routines = SavedRoutine.query.filter_by(user_id=current_user.id)\
        .order_by(SavedRoutine.created_at.desc()).all()
    return render_template('routines.html', user_routines=user_routines)

@app.route('/api/generate-routine', methods=['POST'])
@login_required
def generate_routine():
    """Generate personalized yoga routine using Gemini AI"""
    global gemini_assistant
    
    try:
        if gemini_assistant is None:
            gemini_assistant = GeminiAssistant()
        
        data = request.json
        user_goal = data.get('goal', 'General wellness')
        experience_level = data.get('level', 'Beginner')
        duration = data.get('duration', 30)
        focus_areas = data.get('focus_areas', [])
        
        result = gemini_assistant.generate_routine(
            user_goal=user_goal,
            experience_level=experience_level,
            duration=duration,
            focus_areas=focus_areas
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'routine': None
        }), 500

@app.route('/api/save-routine', methods=['POST'])
@login_required
def save_routine():
    """Save a generated routine to user's account"""
    try:
        data = request.json
        routine_name = data.get('routine_name')
        routine_data = json.dumps(data.get('routine_data'))
        goal = data.get('goal')
        duration = data.get('duration')
        experience_level = data.get('experience_level')
        
        new_routine = SavedRoutine(
            user_id=current_user.id,
            routine_name=routine_name,
            routine_data=routine_data,
            goal=goal,
            duration=duration,
            experience_level=experience_level
        )
        
        db.session.add(new_routine)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Routine saved successfully!',
            'routine_id': new_routine.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error saving routine', 'details': str(e)}), 500

@app.route('/api/delete-routine/<int:routine_id>', methods=['DELETE'])
@login_required
def delete_routine(routine_id):
    """Delete a saved routine"""
    try:
        routine = SavedRoutine.query.filter_by(id=routine_id, user_id=current_user.id).first()
        if not routine:
            return jsonify({'error': 'Routine not found'}), 404
        
        db.session.delete(routine)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Routine deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error deleting routine'}), 500

@app.route('/api/start-session', methods=['POST'])
@login_required
def start_session():
    """Start yoga coaching session"""
    global yoga_coach
    
    try:
        if yoga_coach is None:
            yoga_coach = YogaCoachAPI()
        
        data = request.json
        yoga_coach.current_pose = data.get('pose')
        yoga_coach.pose_start_time = datetime.now()
        yoga_coach.best_score = 0
        
        return jsonify({'status': 'success', 'message': 'Session started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/get-stats')
def get_stats():
    """Get current session statistics"""
    global yoga_coach
    
    if yoga_coach:
        return jsonify({
            'current_pose': yoga_coach.current_pose,
            'best_score': yoga_coach.best_score,
            'session_data': yoga_coach.session_data
        })
    
    return jsonify({'error': 'No active session'})

@app.route('/api/process-frame', methods=['POST'])
def process_frame():
    """Process a single frame from webcam"""
    global yoga_coach
    
    try:
        if yoga_coach is None:
            return jsonify({'error': 'No active session'})
        
        # Get frame data from request
        file = request.files.get('frame')
        if not file:
            return jsonify({'error': 'No frame data'})
        
        # Read image
        img_bytes = file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Process frame
        _, score, feedback = yoga_coach.process_frame(frame)
        
        # Update session data
        yoga_coach.session_data.append({
            'timestamp': datetime.now().isoformat(),
            'score': score,
            'feedback': feedback
        })
        
        return jsonify({
            'score': score,
            'feedback': feedback,
            'best_score': yoga_coach.best_score
        })
        
    except Exception as e:
        print(f"Error processing frame: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/stop-session', methods=['POST'])
def stop_session():
    """Stop current session"""
    global yoga_coach
    
    if yoga_coach:
        yoga_coach.current_pose = None
        return jsonify({'status': 'success', 'message': 'Session stopped'})
    
    return jsonify({'error': 'No active session'})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  VEDAVISION - AI YOGA WELLNESS PLATFORM")
    print("="*60 + "\n")
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        print("✓ Database initialized")
    
    print("🌐 Starting web server...")
    print("📱 Open browser: http://localhost:5000")
    print("\n" + "="*60 + "\n")
    
    # For production, set debug=False and use a production WSGI server
    app.run(debug=True, host='0.0.0.0', port=5000)
