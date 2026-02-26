# 🧘 VedaVision - AI Yoga Posture Coach

An intelligent yoga posture correction tool that uses computer vision to analyze your yoga poses in real-time and provide instant feedback to help you perfect your form!

## ✨ Features

- **Real-time Pose Detection**: Uses MediaPipe to track your body movements
- **5 Classic Yoga Poses**: Support for Tree, Warrior II, Triangle, Downward Dog, and Mountain poses
- **Instant Feedback**: Get immediate corrections on your posture
- **Scoring System**: Track your form with a 0-100 score
- **Visual Guidance**: See your skeleton overlay and alignment in real-time
- **Easy Controls**: Simple keyboard shortcuts to switch between poses

## 📋 Prerequisites

- Python 3.8 or higher
- Webcam
- Good lighting
- About 6-8 feet of space in front of your camera

## 🚀 Installation

1. **Clone or navigate to this directory**
   ```bash
   cd "c:\Users\Sania Rajput\OneDrive\Desktop\vedavision"
   ```

2. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

   This will install:
   - OpenCV (for video processing)
   - MediaPipe (for pose detection)
   - NumPy (for calculations)

## 🎮 How to Use

1. **Start the application**
   ```bash
   python yoga_coach.py
   ```

2. **Select a yoga pose**
   - Press `1` for Tree Pose
   - Press `2` for Warrior II
   - Press `3` for Triangle Pose
   - Press `4` for Downward Dog
   - Press `5` for Mountain Pose

3. **Get into the pose**
   - Make sure your full body is visible in the frame
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
Inverted V-shape with hips as the highest point.

### 5. Mountain Pose (Tadasana) ⛰️
Standing pose with perfect vertical alignment.

See [pose_guide.md](pose_guide.md) for detailed instructions and common mistakes.

## 💡 Tips for Best Results

1. **Lighting**: Practice in a well-lit room (natural light is best)
2. **Camera Placement**: 
   - Distance: 6-8 feet away
   - Height: Chest level
   - Angle: Straight on (not angled up or down)
3. **Clothing**: Wear fitted clothing for better body detection
4. **Background**: Practice against a plain, uncluttered background
5. **Space**: Ensure you have enough room to move freely

## 🎯 How It Works

The application uses **MediaPipe Pose**, a machine learning solution that detects 33 body landmarks in real-time. It then:

1. Calculates angles between joints (shoulders, elbows, hips, knees)
2. Measures distances between body parts
3. Compares your current pose against ideal yoga pose parameters
4. Provides specific, actionable feedback
5. Generates a score based on your alignment

## ⚠️ Important Safety Notes

- This tool is meant to **supplement**, not replace, a qualified yoga instructor
- Always warm up before practicing
- Listen to your body - never force a pose
- If you feel pain (not just discomfort), stop immediately
- Consult with a healthcare provider if you have any injuries or concerns

## 🛠️ Troubleshooting

**Camera not working?**
- Check that your webcam is properly connected
- Ensure no other application is using the camera
- Try running as administrator

**Pose not being detected?**
- Make sure your entire body is visible in the frame
- Improve lighting in your practice area
- Remove clutter from the background
- Wear contrasting clothing

**App running slowly?**
- Close other applications to free up resources
- Reduce video resolution by modifying the code
- Ensure you have a stable CPU

## 🔧 Customization

Want to add your own poses or adjust the thresholds? Check out the `yoga_coach.py` file:

- Add new poses in the `poses` dictionary
- Adjust angle tolerances in the `check_*_pose` methods
- Modify scoring weights to suit your preferences

## 📚 Future Enhancements

Potential features to add:
- [ ] More yoga poses (Warrior I, Chair, Cobra, etc.)
- [ ] Session recording and replay
- [ ] Progress tracking over time
- [ ] Voice feedback
- [ ] Mobile app version
- [ ] Multi-person detection for group classes

## 🙏 Credits

Built with:
- [MediaPipe](https://mediapipe.dev/) by Google
- [OpenCV](https://opencv.org/)
- Lots of ☕ and 🧘

## 📝 License

This project is open source and available for personal use. Feel free to modify and extend it!

---

**Namaste! 🙏 Enjoy your practice!**

For questions or suggestions, feel free to reach out or contribute to the project.
