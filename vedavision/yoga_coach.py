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
        """Initialize pose detector"""
        print("Initializing AI Yoga Coach...")
        
        # Create pose landmarker with improved settings
        base_options = python.BaseOptions(model_asset_path='pose_landmarker.task')
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5)
        self.detector = vision.PoseLandmarker.create_from_options(options)
        
        self.current_pose = None
        self.frame_timestamp = 0
        self.feedback_buffer = []  # Smooth feedback
        self.score_buffer = []
        
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
        
        print("✓ Pose detector ready!")
    
    def calc_angle(self, a, b, c):
        """Calculate angle between 3 points"""
        if not all([a, b, c]):
            return 0
        rad = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(rad * 180.0 / np.pi)
        return 360 - angle if angle > 180 else angle
    
    def get_coords(self, landmark):
        """Extract x, y coordinates from landmark"""
        return [landmark.x, landmark.y] if landmark else None
    
    def evaluate_pose(self, landmarks):
        """Evaluate current yoga pose"""
        if not landmarks or not self.current_pose:
            return [], 0
        
        feedback = []
        score = 100
        lm = landmarks[0]  # First person
        
        # Check landmark visibility
        visible_count = sum(1 for l in lm if l.visibility > 0.5)
        if visible_count < 10:
            return ["⚠ Move closer to camera"], 50
        
        try:
            # Extract key body points
            l_shoulder = self.get_coords(lm[11])
            r_shoulder = self.get_coords(lm[12])
            l_elbow = self.get_coords(lm[13])
            r_elbow = self.get_coords(lm[14])
            l_wrist = self.get_coords(lm[15])
            r_wrist = self.get_coords(lm[16])
            l_hip = self.get_coords(lm[23])
            r_hip = self.get_coords(lm[24])
            l_knee = self.get_coords(lm[25])
            r_knee = self.get_coords(lm[26])
            l_ankle = self.get_coords(lm[27])
            r_ankle = self.get_coords(lm[28])
            
            # Universal checks with more forgiving thresholds
            if l_shoulder and r_shoulder:
                shoulder_tilt = abs(l_shoulder[1] - r_shoulder[1])
                if shoulder_tilt > 0.12:  # More forgiving
                    feedback.append("⚠ Level shoulders")
                    score -= 10
                elif shoulder_tilt < 0.05:
                    feedback.append("✓ Shoulders level!")
            
            if l_hip and r_hip:
                hip_tilt = abs(l_hip[1] - r_hip[1])
                if hip_tilt > 0.12:  # More forgiving
                    feedback.append("⚠ Level hips")
                    score -= 10
                elif hip_tilt < 0.05:
                    feedback.append("✓ Hips level!")
            
            # Pose-specific evaluation with gradual feedback
            if self.current_pose == 'warrior2':
                # Front knee check with wider tolerance
                if l_knee and l_hip and l_ankle:
                    angle = self.calc_angle(l_hip, l_knee, l_ankle)
                    if 75 <= angle <= 105:  # Wider acceptable range
                        feedback.append("✓ Perfect knee!")
                    elif angle < 70:
                        feedback.append("⚠ Knee too deep - raise up")
                        score -= 12
                    elif angle < 75:
                        feedback.append("→ Slight adjustment - knee higher")
                        score -= 5
                    elif angle > 110:
                        feedback.append("⚠ Bend knee deeper (90°)")
                        score -= 12
                    else:
                        feedback.append("→ Almost there - bend slightly")
                        score -= 5
                
                # Arms extension with gradual feedback
                if l_shoulder and l_elbow and l_wrist:
                    arm = self.calc_angle(l_shoulder, l_elbow, l_wrist)
                    if arm >= 155:  # More forgiving
                        feedback.append("✓ Arms extended!")
                    elif arm >= 140:
                        feedback.append("→ Extend arms more")
                        score -= 5
                    else:
                        feedback.append("⚠ Straighten arms")
                        score -= 8
            
            elif self.current_pose == 'tree':
                # Standing leg check with better tolerance
                if r_knee and r_hip and r_ankle:
                    leg = self.calc_angle(r_hip, r_knee, r_ankle)
                    if leg >= 160:  # More forgiving
                        feedback.append("✓ Leg straight!")
                    elif leg >= 150:
                        feedback.append("→ Straighten leg slightly")
                        score -= 8
                    else:
                        feedback.append("⚠ Straighten standing leg")
                        score -= 15
                
                # Balance indicator with visual feedback
                if l_hip and r_hip:
                    balance = abs(l_hip[1] - r_hip[1])
                    if balance < 0.06:
                        feedback.append("✓ Great balance!")
                    elif balance < 0.10:
                        feedback.append("→ Good - keep steady")
                        score -= 3
            
            elif self.current_pose == 'mountain':
                # Vertical alignment with better tolerance
                if l_shoulder and l_hip and l_ankle:
                    offset = abs(l_shoulder[0] - l_hip[0]) + abs(l_hip[0] - l_ankle[0])
                    if offset < 0.12:  # More forgiving
                        feedback.append("✓ Perfect alignment!")
                    elif offset < 0.18:
                        feedback.append("→ Adjust posture slightly")
                        score -= 8
                    else:
                        feedback.append("⚠ Align body vertically")
                        score -= 15
                
                # Leg straightness with gradual feedback
                if l_knee and l_hip and l_ankle:
                    leg = self.calc_angle(l_hip, l_knee, l_ankle)
                    if leg >= 160:  # More forgiving
                        feedback.append("✓ Legs straight!")
                    elif leg >= 150:
                        feedback.append("→ Straighten legs more")
                        score -= 6
                    else:
                        feedback.append("⚠ Straighten your legs")
                        score -= 12
            
            elif self.current_pose == 'triangle':
                # Both legs straight with better feedback
                if l_knee and l_hip and l_ankle:
                    left = self.calc_angle(l_hip, l_knee, l_ankle)
                    if left >= 160:  # More forgiving
                        feedback.append("✓ Legs straight!")
                    elif left >= 150:
                        feedback.append("→ Straighten legs more")
                        score -= 8
                    else:
                        feedback.append("⚠ Keep legs straight")
                        score -= 15
            
            elif self.current_pose == 'down_dog':
                # Hips higher than shoulders with gradual feedback
                if l_hip and l_shoulder:
                    hip_height = l_shoulder[1] - l_hip[1]  # Positive = hips higher
                    if hip_height > 0.15:  # Good inverted V
                        feedback.append("✓ Perfect V shape!")
                    elif hip_height > 0.05:
                        feedback.append("→ Lift hips slightly higher")
                        score -= 8
                    else:
                        feedback.append("⚠ Lift hips higher")
                        score -= 18
        
        except:
            feedback = ["Analyzing..."]
        
        if len(feedback) == 0:
            feedback.append("✓ Excellent form!")
        
        # Smooth score over frames
        self.score_buffer.append(score)
        if len(self.score_buffer) > 5:
            self.score_buffer.pop(0)
        smoothed_score = int(sum(self.score_buffer) / len(self.score_buffer))
        
        return feedback[:3], max(smoothed_score, 0)
    
    def draw_skeleton(self, frame, landmarks):
        """Draw pose skeleton with visibility checking"""
        h, w, _ = frame.shape
        lm = landmarks[0]
        
        # Skeleton connections
        connections = [
            (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
            (11, 23), (12, 24), (23, 24),
            (23, 25), (25, 27), (24, 26), (26, 28)
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
        
        # Draw joints with visibility indicator
        for idx in [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]:
            if idx < len(lm) and lm[idx].visibility > 0.5:
                x, y = int(lm[idx].x * w), int(lm[idx].y * h)
                confidence = lm[idx].visibility
                # Color indicates confidence
                color = (100, int(100 + confidence * 155), 100)
                size = 7 if confidence > 0.7 else 5
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
        print("\n✓ AI Pose Detection: ACTIVE")
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
        print("❌ Error: pose_landmarker.task not found!")
        print("\nThis file should be in the same folder.")
        print("The model has been downloaded. Please restart the program.\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
        print("Make sure your webcam is connected and accessible.\n")

if __name__ == "__main__":
    main()
