"""
VedaVision - AI Yoga Posture Coach
Real-time yoga pose correction using MediaPipe
"""

import cv2
import numpy as np
import math
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class YogaCoach:
    def __init__(self):
        """Initialize pose detector with 3D Vector Calculus and Temporal Filtering"""
        print("Initializing AI Yoga Coach with BlazePose HEAVY model...")
        print("Loading: 3D Vector Calculus + Temporal Filtering...")
        
        # Create BlazePose landmarker with HEAVY model for maximum accuracy
        base_options = python.BaseOptions(model_asset_path='pose_landmarker_heavy.task')
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.7,  # Higher confidence for accuracy
            min_pose_presence_confidence=0.7,   # Ensure person is clearly visible
            min_tracking_confidence=0.7)        # Better tracking consistency
        self.detector = vision.PoseLandmarker.create_from_options(options)
        
        self.current_pose = None
        self.frame_timestamp = 0
        self.feedback_buffer = []  # Smooth feedback
        self.score_buffer = []
        
        # Temporal Filtering: Exponential Moving Average for landmark smoothing
        self.landmark_history = {}  # Store previous landmark positions
        self.alpha = 0.3  # EMA smoothing factor (0.3 = 30% new, 70% history)
        
        # Temporal Filtering: Outlier rejection
        self.max_jump_threshold = 0.15  # Max allowed sudden movement
        
        # Advanced score smoothing with weighted temporal filter
        self.score_weights = [0.1, 0.15, 0.2, 0.25, 0.3]  # Recent frames weighted more
        
        # Yoga poses database
        self.poses = {
            '1': {
                'name': 'Tree Pose',
                'sanskrit': 'Vrksasana',
                'key': 'tree',
                'tips': ['Stand on one leg', 'Foot on inner thigh', 'Keep balance', 'Hands in prayer']
            },
            '2': {
                'name': 'Warrior II',
                'sanskrit': 'Virabhadrasana II',
                'key': 'warrior2',
                'tips': ['Front knee 90°', 'Back leg straight', 'Arms extended', 'Chest open']
            },
            '3': {
                'name': 'Triangle',
                'sanskrit': 'Trikonasana',
                'key': 'triangle',
                'tips': ['Legs straight', 'Reach sideways', 'Open chest', 'Hand to shin']
            },
            '4': {
                'name': 'Downward Dog',
                'sanskrit': 'Adho Mukha Svanasana',
                'key': 'down_dog',
                'tips': ['Form inverted V', 'Hips high', 'Legs straight', 'Relax head']
            },
            '5': {
                'name': 'Mountain',
                'sanskrit': 'Tadasana',
                'key': 'mountain',
                'tips': ['Stand tall', 'Feet together', 'Shoulders back', 'Breathe deeply']
            }
        }
        
        print("✓ BlazePose HEAVY model loaded - Maximum accuracy enabled!")
        print("✓ 3D Vector Calculus: ACTIVE")
        print("✓ Temporal Filtering: ACTIVE (EMA + Outlier Rejection)")
    
    def calc_angle(self, a, b, c):
        """Calculate angle between 3 points with BlazePose precision (2D fallback)"""
        if not all([a, b, c]):
            return 0
        # Use high-precision calculation for BlazePose landmarks
        a = np.array(a, dtype=np.float64)
        b = np.array(b, dtype=np.float64)
        c = np.array(c, dtype=np.float64)
        
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180 else angle
    
    def calc_angle_3d(self, a, b, c):
        """Calculate 3D angle using Vector Calculus (dot product method)
        More accurate than 2D as it accounts for depth.
        """
        if not all([a, b, c]) or len(a) < 3 or len(b) < 3 or len(c) < 3:
            return self.calc_angle(a, b, c)  # Fallback to 2D
        
        # Create 3D vectors
        a = np.array(a, dtype=np.float64)
        b = np.array(b, dtype=np.float64)
        c = np.array(c, dtype=np.float64)
        
        # Vector from b to a and b to c
        ba = a - b
        bc = c - b
        
        # Calculate angle using dot product: cos(θ) = (ba · bc) / (|ba| × |bc|)
        dot_product = np.dot(ba, bc)
        magnitude_ba = np.linalg.norm(ba)
        magnitude_bc = np.linalg.norm(bc)
        
        if magnitude_ba == 0 or magnitude_bc == 0:
            return 0
        
        cos_angle = dot_product / (magnitude_ba * magnitude_bc)
        # Clamp to [-1, 1] to avoid numerical errors
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        angle = np.arccos(cos_angle) * 180.0 / np.pi
        return angle
    
    def calc_distance(self, a, b):
        """Calculate Euclidean distance between two points (2D)"""
        if not all([a, b]):
            return 0
        return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)
    
    def calc_distance_3d(self, a, b):
        """Calculate 3D Euclidean distance using Vector Calculus
        Accounts for depth, more accurate for body measurements.
        """
        if not all([a, b]) or len(a) < 3 or len(b) < 3:
            return self.calc_distance(a, b)  # Fallback to 2D
        
        a = np.array(a, dtype=np.float64)
        b = np.array(b, dtype=np.float64)
        return np.linalg.norm(a - b)
    
    def calc_body_plane_normal(self, shoulder_l, shoulder_r, hip_l, hip_r):
        """Calculate body plane orientation using cross product (Vector Calculus)
        Returns normal vector indicating body rotation in 3D space.
        """
        if not all([shoulder_l, shoulder_r, hip_l, hip_r]):
            return None
        if any(len(p) < 3 for p in [shoulder_l, shoulder_r, hip_l, hip_r]):
            return None
        
        # Create vectors in the body plane
        shoulder_vec = np.array(shoulder_r, dtype=np.float64) - np.array(shoulder_l, dtype=np.float64)
        torso_vec = np.array(hip_l, dtype=np.float64) - np.array(shoulder_l, dtype=np.float64)
        
        # Cross product gives normal to the plane
        normal = np.cross(shoulder_vec, torso_vec)
        
        # Normalize
        magnitude = np.linalg.norm(normal)
        if magnitude == 0:
            return None
        
        return normal / magnitude
    
    def get_coords(self, landmark):
        """Extract x, y coordinates from BlazePose landmark with visibility check"""
        if landmark and landmark.visibility > 0.7:  # Higher threshold for accuracy
            return [landmark.x, landmark.y]
        return None
    
    def get_landmark_safe(self, lm, idx):
        """Safely get landmark with visibility and presence checks (2D)"""
        if idx < len(lm) and lm[idx].visibility > 0.7 and lm[idx].presence > 0.7:
            return [lm[idx].x, lm[idx].y]
        return None
    
    def get_landmark_3d(self, lm, idx):
        """Get 3D landmark (x, y, z) with Temporal Filtering
        Includes: Exponential Moving Average + Outlier Rejection
        """
        if idx >= len(lm) or lm[idx].visibility < 0.7 or lm[idx].presence < 0.7:
            return None
        
        # Current 3D position
        current_pos = np.array([lm[idx].x, lm[idx].y, lm[idx].z], dtype=np.float64)
        
        # Temporal Filtering: Exponential Moving Average
        if idx in self.landmark_history:
            prev_pos = self.landmark_history[idx]
            
            # Outlier Rejection: Check if movement is too sudden
            movement = np.linalg.norm(current_pos - prev_pos)
            if movement > self.max_jump_threshold:
                # Likely a tracking error, use more of the history
                filtered_pos = self.alpha * 0.3 * current_pos + (1 - self.alpha * 0.3) * prev_pos
            else:
                # Normal movement, apply standard EMA
                filtered_pos = self.alpha * current_pos + (1 - self.alpha) * prev_pos
            
            self.landmark_history[idx] = filtered_pos
            return filtered_pos.tolist()
        else:
            # First time seeing this landmark
            self.landmark_history[idx] = current_pos
            return current_pos.tolist()
    
    def evaluate_pose(self, landmarks):
        """Evaluate current yoga pose"""
        if not landmarks or not self.current_pose:
            return [], 0
        
        feedback = []
        score = 60  # Start at 60, earn points for correct form
        lm = landmarks[0]  # First person
        
        # Check landmark visibility with BlazePose precision
        visible_count = sum(1 for l in lm if l.visibility > 0.7 and l.presence > 0.7)
        if visible_count < 12:  # Need more visible landmarks for accuracy
            return ["⚠ Move closer - need clear view"], 25
        
        try:
            # Extract key BlazePose body points (33 total landmarks)
            # Using 3D coordinates with Temporal Filtering
            nose = self.get_landmark_3d(lm, 0)
            l_eye = self.get_landmark_3d(lm, 2)
            r_eye = self.get_landmark_3d(lm, 5)
            l_ear = self.get_landmark_3d(lm, 7)
            r_ear = self.get_landmark_3d(lm, 8)
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
            l_heel = self.get_landmark_3d(lm, 29)
            r_heel = self.get_landmark_3d(lm, 30)
            l_foot = self.get_landmark_3d(lm, 31)
            r_foot = self.get_landmark_3d(lm, 32)
            
            # Calculate body plane orientation (3D Vector Calculus)
            body_normal = self.calc_body_plane_normal(l_shoulder, r_shoulder, l_hip, r_hip)
            body_rotation = 0
            if body_normal is not None:
                # Calculate rotation from front-facing (normal should be [0, 0, -1])
                front_vector = np.array([0, 0, -1])
                body_rotation = np.arccos(np.clip(np.dot(body_normal, front_vector), -1, 1)) * 180 / np.pi
            
            # BlazePose precision checks - earn points for accurate form
            if l_shoulder and r_shoulder:
                shoulder_tilt = abs(l_shoulder[1] - r_shoulder[1])
                if shoulder_tilt > 0.08:  # Stricter with BlazePose accuracy
                    feedback.append("⚠ Level shoulders")
                    score -= 15
                elif shoulder_tilt < 0.03:  # More precise threshold
                    feedback.append("✓ Shoulders perfectly level!")
                    score += 12
            
            if l_hip and r_hip:
                hip_tilt = abs(l_hip[1] - r_hip[1])
                if hip_tilt > 0.08:  # Stricter with BlazePose
                    feedback.append("⚠ Level hips")
                    score -= 15
                elif hip_tilt < 0.03:  # More precise
                    feedback.append("✓ Hips perfectly level!")
                    score += 12
            
            # Pose-specific evaluation with comprehensive checks
            if self.current_pose == 'warrior2':
                pose_detected = False
                
                # BlazePose accurate stance width check
                if l_ankle and r_ankle and l_foot and r_foot:
                    # Use both ankle and foot landmarks for precision
                    stance_width = max(abs(l_ankle[0] - r_ankle[0]), abs(l_foot[0] - r_foot[0]))
                    if stance_width < 0.35:  # Stricter requirement
                        feedback.append("⚠ Stance too narrow - spread legs wider")
                        score -= 20
                    elif stance_width > 0.45:
                        pose_detected = True
                        feedback.append("✓ Perfect wide stance!")
                        score += 15
                    else:
                        pose_detected = True
                        score += 8
                
                # BlazePose precise front knee angle check (3D Vector Calculus)
                if l_knee and l_hip and l_ankle:
                    angle = self.calc_angle_3d(l_hip, l_knee, l_ankle)
                    if angle > 135:  # Stricter - too straight = not in pose
                        feedback.append("⚠ BEND front knee to 90°")
                        score -= 30
                    elif 88 <= angle <= 92:  # Perfect 90 degrees with tight tolerance
                        feedback.append("✓ PERFECT 90° knee angle!")
                        score += 20
                    elif 82 <= angle <= 98:  # Good range
                        feedback.append("✓ Great knee angle!")
                        score += 12
                    elif 75 <= angle <= 105:  # Acceptable
                        feedback.append("→ Fine-tune knee angle")
                        score += 5
                    else:
                        feedback.append("⚠ Adjust knee bend significantly")
                        score -= 15
                
                # BlazePose precise back leg straightness (3D Vector Calculus)
                if r_knee and r_hip and r_ankle:
                    back_leg = self.calc_angle_3d(r_hip, r_knee, r_ankle)
                    if back_leg < 155:
                        feedback.append("⚠ Straighten back leg more")
                        score -= 18
                    elif back_leg >= 170:  # Very straight
                        feedback.append("✓ Back leg perfect!")
                        score += 15
                    else:
                        score += 8
                
                # BlazePose precise arm extension and alignment (3D Vector Calculus)
                if l_shoulder and l_elbow and l_wrist and r_shoulder and r_elbow and r_wrist:
                    left_arm = self.calc_angle_3d(l_shoulder, l_elbow, l_wrist)
                    right_arm = self.calc_angle_3d(r_shoulder, r_elbow, r_wrist)
                    arms_wide = self.calc_distance_3d(l_wrist, r_wrist)
                    
                    # Check arm extension (3D distance)
                    if arms_wide < 0.60:  # 3D distance is more accurate
                        feedback.append("⚠ EXTEND arms wider")
                        score -= 25
                    elif left_arm >= 165 and right_arm >= 165:  # Very straight
                        # Check if arms are horizontal
                        arm_height_diff = abs(l_wrist[1] - r_wrist[1])
                        if arm_height_diff < 0.05:
                            feedback.append("✓ Arms PERFECT horizontal!")
                            score += 20
                        else:
                            feedback.append("✓ Arms extended!")
                            score += 12
                    elif left_arm >= 155 or right_arm >= 155:
                        feedback.append("→ Straighten arms more")
                        score += 3
                    else:
                        feedback.append("⚠ Both arms need straightening")
                        score -= 10
            
            elif self.current_pose == 'tree':
                # BlazePose precise leg raise detection
                if l_knee and r_knee and l_hip and r_hip and l_ankle and r_ankle:
                    # Check vertical distance between knee and hip
                    left_knee_height = l_hip[1] - l_knee[1]  # Positive = knee higher than hip
                    right_knee_height = r_hip[1] - r_knee[1]
                    
                    left_raised = left_knee_height > 0.15
                    right_raised = right_knee_height > 0.15
                    
                    if not (left_raised or right_raised):
                        feedback.append("⚠ RAISE one leg high (foot to thigh)")
                        score -= 35
                    elif left_raised or right_raised:
                        # Check if raised knee is bent properly (3D Vector Calculus)
                        if left_raised:
                            knee_bend = self.calc_angle_3d(l_hip, l_knee, l_ankle)
                            if 40 <= knee_bend <= 80:
                                feedback.append("✓ Perfect tree leg position!")
                                score += 20
                            else:
                                feedback.append("✓ Leg raised!")
                                score += 12
                        else:
                            knee_bend = self.calc_angle_3d(r_hip, r_knee, r_ankle)
                            if 40 <= knee_bend <= 80:
                                feedback.append("✓ Perfect tree leg position!")
                                score += 20
                            else:
                                feedback.append("✓ Leg raised!")
                                score += 12
                
                # BlazePose precise standing leg check (3D Vector Calculus)
                if r_knee and r_hip and r_ankle:
                    leg = self.calc_angle_3d(r_hip, r_knee, r_ankle)
                    if leg >= 172:  # Very straight requirement
                        feedback.append("✓ Standing leg PERFECT!")
                        score += 18
                    elif leg >= 165:
                        feedback.append("✓ Standing leg good!")
                        score += 10
                    elif leg >= 155:
                        feedback.append("→ Straighten leg more")
                        score += 3
                    else:
                        feedback.append("⚠ Standing leg must be straight")
                        score -= 20
                
                # Balance check
                if l_hip and r_hip:
                    balance = abs(l_hip[1] - r_hip[1])
                    if balance < 0.05:
                        feedback.append("✓ Perfect balance!")
                        score += 10
                    elif balance > 0.15:
                        feedback.append("⚠ Work on balance")
                        score -= 10
            
            elif self.current_pose == 'mountain':
                # Vertical alignment - CRITICAL for mountain pose
                if l_shoulder and l_hip and l_ankle:
                    offset = abs(l_shoulder[0] - l_hip[0]) + abs(l_hip[0] - l_ankle[0])
                    if offset < 0.08:
                        feedback.append("✓ Perfect alignment!")
                        score += 20
                    elif offset < 0.15:
                        feedback.append("→ Adjust posture")
                        score += 5
                    else:
                        feedback.append("⚠ Body not vertical")
                        score -= 20
                
                # Both legs MUST be straight (3D Vector Calculus)
                if l_knee and l_hip and l_ankle and r_knee and r_hip and r_ankle:
                    left_leg = self.calc_angle_3d(l_hip, l_knee, l_ankle)
                    right_leg = self.calc_angle_3d(r_hip, r_knee, r_ankle)
                    if left_leg >= 165 and right_leg >= 165:
                        feedback.append("✓ Legs perfect!")
                        score += 15
                    elif left_leg < 150 or right_leg < 150:
                        feedback.append("⚠ Straighten both legs")
                        score -= 20
                    else:
                        feedback.append("→ Straighten legs more")
                        score += 5
                
                # Feet should be together or close
                if l_ankle and r_ankle:
                    feet_distance = abs(l_ankle[0] - r_ankle[0])
                    if feet_distance > 0.15:
                        feedback.append("⚠ Bring feet closer")
                        score -= 10
            
            elif self.current_pose == 'triangle':
                # Wide stance required
                if l_ankle and r_ankle:
                    stance = abs(l_ankle[0] - r_ankle[0])
                    if stance < 0.35:
                        feedback.append("⚠ Widen stance")
                        score -= 20
                    else:
                        score += 10
                
                # BOTH legs MUST be straight (3D Vector Calculus)
                if l_knee and l_hip and l_ankle and r_knee and r_hip and r_ankle:
                    left_leg = self.calc_angle_3d(l_hip, l_knee, l_ankle)
                    right_leg = self.calc_angle_3d(r_hip, r_knee, r_ankle)
                    if left_leg >= 165 and right_leg >= 165:
                        feedback.append("✓ Legs straight!")
                        score += 20
                    elif left_leg < 150 or right_leg < 150:
                        feedback.append("⚠ STRAIGHTEN legs")
                        score -= 25
                    else:
                        feedback.append("→ Straighten more")
                        score += 5
                
                # Body should be tilted sideways
                if l_shoulder and r_shoulder:
                    shoulder_height_diff = abs(l_shoulder[1] - r_shoulder[1])
                    if shoulder_height_diff < 0.15:
                        feedback.append("⚠ Tilt body more to side")
                        score -= 15
                    else:
                        score += 10
            
            elif self.current_pose == 'down_dog':
                # Hips MUST be highest point - critical check
                if l_hip and l_shoulder and l_ankle:
                    hip_height = l_shoulder[1] - l_hip[1]  # Positive = hips higher
                    if hip_height <= 0:  # Hips not higher than shoulders
                        feedback.append("⚠ NOT in pose - LIFT hips high")
                        score -= 35
                    elif hip_height > 0.20:
                        feedback.append("✓ Perfect inverted V!")
                        score += 25
                    elif hip_height > 0.10:
                        feedback.append("→ Lift hips higher")
                        score += 10
                    else:
                        feedback.append("⚠ Hips must be highest point")
                        score -= 15
                
                # Legs should be straight (3D Vector Calculus)
                if l_knee and l_hip and l_ankle:
                    leg = self.calc_angle_3d(l_hip, l_knee, l_ankle)
                    if leg >= 160:
                        feedback.append("✓ Legs straight!")
                        score += 10
                    elif leg < 140:
                        feedback.append("⚠ Straighten legs")
                        score -= 15
        
        except:
            feedback = ["Analyzing..."]
        
        if len(feedback) == 0:
            feedback.append("→ Getting into position...")
        
        # Temporal Filtering: Weighted moving average for score smoothing
        self.score_buffer.append(score)
        if len(self.score_buffer) > 5:
            self.score_buffer.pop(0)
        
        # Apply weighted average (recent frames weighted more heavily)
        if len(self.score_buffer) == 5:
            smoothed_score = int(sum(s * w for s, w in zip(self.score_buffer, self.score_weights)))
        else:
            # Fall back to simple average if not enough history
            smoothed_score = int(sum(self.score_buffer) / len(self.score_buffer))
        
        # Cap score between 0-100
        final_score = max(0, min(100, smoothed_score))
        
        # Add overall feedback based on score
        if final_score >= 85:
            feedback.insert(0, "✓ Excellent form!")
        elif final_score >= 70:
            feedback.insert(0, "→ Good, minor adjustments")
        elif final_score >= 50:
            feedback.insert(0, "⚠ Needs improvement")
        else:
            feedback.insert(0, "⚠ Not in correct pose")
        
        return feedback[:4], final_score
    
    def draw_skeleton(self, frame, landmarks):
        """Draw pose skeleton with visibility checking"""
        h, w, _ = frame.shape
        lm = landmarks[0]
        
        # BlazePose complete skeleton connections (33 landmarks)
        connections = [
            # Face
            (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
            # Torso
            (11, 12), (11, 23), (12, 24), (23, 24),
            # Arms
            (11, 13), (13, 15), (12, 14), (14, 16),
            # Legs
            (23, 25), (25, 27), (27, 29), (29, 31),  # Left leg with foot
            (24, 26), (26, 28), (28, 30), (30, 32),  # Right leg with foot
        ]
        
        # Draw lines only if both points are visible
        for start, end in connections:
            if start < len(lm) and end < len(lm):
                if lm[start].visibility > 0.5 and lm[end].visibility > 0.5:
                    pt1 = (int(lm[start].x * w), int(lm[start].y * h))
                    pt2 = (int(lm[end].x * w), int(lm[end].y * h))
                    # Color based on visibility
                    confidence = (lm[start].visibility + lm[end].visibility) / 2
                    color = (50, int(150 + confidence * 105), 50)
                    thickness = 3 if confidence > 0.7 else 2
                    cv2.line(frame, pt1, pt2, color, thickness)
        
        # Draw all BlazePose joints with visibility indicator
        key_points = [0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
        for idx in key_points:
            if idx < len(lm) and lm[idx].visibility > 0.5:
                x, y = int(lm[idx].x * w), int(lm[idx].y * h)
                confidence = lm[idx].visibility
                presence = lm[idx].presence
                # Color indicates confidence - brighter = more confident
                color = (int(50 + confidence * 100), int(100 + confidence * 155), int(50 + presence * 100))
                size = 8 if confidence > 0.8 else 6 if confidence > 0.7 else 4
                cv2.circle(frame, (x, y), size, color, -1)
                cv2.circle(frame, (x, y), size + 1, (255, 255, 255), 2)
        
        return frame
    
    def draw_interface(self, frame, detected, feedback, score):
        """Draw UI overlay"""
        h, w, _ = frame.shape
        
        # Top panel
        panel = frame.copy()
        cv2.rectangle(panel, (10, 10), (w-10, 200), (30, 30, 30), -1)
        frame = cv2.addWeighted(panel, 0.8, frame, 0.2, 0)
        
        if self.current_pose:
            pose_data = next((p for p in self.poses.values() if p['key'] == self.current_pose), None)
            if pose_data:
                # Pose name
                cv2.putText(frame, f"{pose_data['name']}", (25, 50),
                           cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2)
                cv2.putText(frame, f"({pose_data['sanskrit']})", (25, 80),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
                
                if detected:
                    # Score
                    color = (0, 255, 0) if score >= 80 else (0, 255, 255) if score >= 60 else (0, 150, 255)
                    cv2.putText(frame, f"Score: {score}%", (25, 125),
                               cv2.FONT_HERSHEY_DUPLEX, 0.9, color, 2)
                    
                    # Feedback
                    y = 165
                    for msg in feedback:
                        c = (100, 255, 100) if '✓' in msg else (150, 180,255)
                        cv2.putText(frame, msg, (25, y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, c, 2)
                        y += 35
                else:
                    cv2.putText(frame, "Step into frame!", (25, 140),
                               cv2.FONT_HERSHEY_DUPLEX, 0.9, (100, 200, 255), 2)
        else:
            cv2.putText(frame, "CHOOSE A YOGA POSE", (25, 60),
                       cv2.FONT_HERSHEY_DUPLEX, 1.2, (100, 200, 255), 3)
            cv2.putText(frame, "Press 1-5 to select", (25, 115),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)
            cv2.putText(frame, "Stand 6-8 feet from camera", (25, 160),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 1)
        
        # Bottom controls    
        bottom = frame.copy()
        y = h - 100
        cv2.rectangle(bottom, (10, y), (w-10, h-10), (30, 30, 30), -1)
        frame = cv2.addWeighted(bottom, 0.8, frame, 0.2, 0)
        
        cv2.putText(frame, "CONTROLS:", (20, y+30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.putText(frame, "1-Tree | 2-Warrior II | 3-Triangle | 4-Down Dog | 5-Mountain | Q-Quit",
                   (20, y+65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        
        return frame
    
    def process(self, frame):
        """Process video frame"""
        self.frame_timestamp += 1
        feedback, score, detected = [], 0, False
        
        # Convert to MediaPipe format
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        # Detect pose
        try:
            result = self.detector.detect_for_video(mp_img, self.frame_timestamp)
            
            if result.pose_landmarks:
                detected = True
                frame = self.draw_skeleton(frame, result.pose_landmarks)
                
                if self.current_pose:
                    feedback, score = self.evaluate_pose(result.pose_landmarks)
        except:
            pass
        
        # Draw UI
        frame = self.draw_interface(frame, detected, feedback, score)
        return frame
    
    def run(self):
        """Main application loop"""
        cam = cv2.VideoCapture(0)
        
        if not cam.isOpened():
            print("\n❌ Cannot access webcam!")
            print("\nFix:")
            print("  1. Check camera permissions (Settings > Privacy > Camera)")
            print("  2. Close other apps using camera")
            print("  3. Reconnect webcam\n")
            return
        
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print("\n" + "="*60)
        print("🧘 VEDAVISION - YOGA POSTURE COACH")
        print("="*60)
        print("\n✓ AI Pose Detection: BlazePose HEAVY (Max Accuracy)")
        print("✓ Tracking: 33 body landmarks with precision")
        print("✓ 3D Vector Calculus: Depth-aware angle calculation")
        print("✓ Temporal Filtering: EMA smoothing + outlier rejection")
        print("\nYoga Poses:")
        for key, pose in self.poses.items():
            print(f"  {key} - {pose['name']}")
        print("  Q - Quit\n")
        print("="*60)
        print("\n📹 Camera active! Get into position...\n")
        
        while True:
            ret, frame = cam.read()
            if not ret:
                print("Frame capture failed")
                break
            
            frame = cv2.flip(frame, 1)  # Mirror mode
            frame = self.process(frame)
            cv2.imshow('VedaVision Yoga Coach', frame)
            
            key = cv2.waitKey(5) & 0xFF
            
            if key == ord('q') or key == ord('Q'):
                break
            elif chr(key) in self.poses:
                self.current_pose = self.poses[chr(key)]['key']
                print(f"\n✓ {self.poses[chr(key)]['name']} selected")
        
        cam.release()
        cv2.destroyAllWindows()
        print("\n🙏 Namaste! Great practice.\n")

def main():
    print("\n" + "="*60)
    print("  VEDAVISION - AI YOGA POSTURE CORRECTION")
    print("="*60 + "\n")
    
    try:
        coach = YogaCoach()
        coach.run()
    except FileNotFoundError:
        print("❌ Error: pose_landmarker_heavy.task not found!")
        print("\nBlazePose HEAVY model file should be in the same folder.")
        print("Download from: https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
        print("Make sure your webcam is connected and accessible.\n")

if __name__ == "__main__":
    main()
