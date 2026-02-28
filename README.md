# 🧘 VedaVision - AI Yoga Wellness Platform

Your personal AI-powered yoga coach that provides real-time posture guidance and personalized practice routines!

## 🌟 Features

- **AI-Powered Coaching**: Advanced pose detection with instant feedback
- **Personalized Routines**: Get custom yoga sequences based on your goals
- **Real-time Guidance**: Visual feedback on your posture and form
- **5 Classic Yoga Poses**: Tree, Warrior II, Triangle, Downward Dog, and Mountain poses
- **Smart Scoring**: Track your progress with intelligent performance scoring
- **Beautiful Interface**: Modern, intuitive web design

## 🚀 Quick Start

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sania0607/vedavision
   cd vedavision
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download AI Model**
   The pose detection model will be downloaded automatically on first run.

4. **Set up API Key**
   ```bash
   cp .env.example .env
   # Edit .env and add your Gemini API key
   ```
   Get your free API key at: https://makersuite.google.com/app/apikey

5. **Start the application**
   ```bash
   python app.py
   ```
   
6. **Open in browser**
   Navigate to: http://localhost:5000

## 🎯 How to Use

### Yoga Coach
1. Click "Start Practice" in the navigation menu
2. Allow camera access when prompted
3. Select a yoga pose from the menu
4. Follow the on-screen guidance
5. Watch your score improve as you perfect your form!

### Personalized Routines
1. Click "My Routine" in the navigation menu
2. Tell us your goals (flexibility, strength, stress relief, etc.)
3. Select your experience level
4. Choose your session duration
5. Let AI create a custom yoga sequence just for you!

## 📋 System Requirements

- Python 3.8 or higher
- Webcam (for pose detection)
   - Follow the on-screen feedback to correct your posture
   - Watch your score improve as you adjust!

4. **Exit**
   - Press `Q` to quit the application

## 📊 Understanding the Feedback

### Score Interpretation
- **80-100** 🟢 Excellent! Your form is great
- **60-79** 🟡 Good, but needs minor adjustments
- **0-59** 🔴 Needs significant correction

### Feedback Messages
The app provides specific guidance such as:
- "Keep shoulders level"
- "Straighten standing leg"
- "Bend front knee more"
- "Align body vertically"

## 🧘 Supported Poses

### 1. Tree Pose (Vrksasana) 🌳
Balance on one leg with the other foot resting on your inner thigh.

### 2. Warrior II (Virabhadrasana II) ⚔️
Strong standing pose with arms extended and front knee bent at 90 degrees.

### 3. Triangle Pose (Trikonasana) 📐
Side stretch with straight legs and torso tilted to one side.

### 4. Downward Facing Dog (Adho Mukha Svanasana) 🐕
Inverted V-shape with hips as the highest point.- Good lighting
- 6-8 feet of space in front of camera

## 🧘 Supported Yoga Poses

1. **Tree Pose (Vrksasana)** - Balance and focus
2. **Warrior II (Virabhadrasana II)** - Strength and stability
3. **Triangle Pose (Trikonasana)** - Flexibility and stretch
4. **Downward Dog (Adho Mukha Svanasana)** - Full body stretch
5. **Mountain Pose (Tadasana)** - Foundation and alignment

## 💡 Tips for Best Results

1. **Lighting**: Practice in a well-lit room
2. **Camera Distance**: 6-8 feet away at chest level
3. **Clothing**: Wear fitted clothing for accurate detection
4. **Background**: Plain, uncluttered background works best
5. **Space**: Ensure full body is visible in frame

## ⚠️ Safety First

- This tool supplements, not replaces, professional instruction
- Always warm up before practicing
- Listen to your body - never force a pose
- Stop if you feel pain
- Consult healthcare provider if you have injuries

## 🛠️ Troubleshooting

**Camera not working?**
- Check webcam connection
- Ensure no other app is using the camera
- Allow camera permissions in browser

**Pose not detected?**
- Ensure entire body is visible
- Improve room lighting
- Remove background clutter
- Wear contrasting clothing



## 🙏 Acknowledgments

Built with:
- MediaPipe by Google
- OpenCV
- Flask
- Google Gemini AI

---

**Namaste! 🙏 Start your yoga journey today!**

Visit: http://localhost:5000 after running the app
