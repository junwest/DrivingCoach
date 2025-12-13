#!/usr/bin/env python3
"""
DrivingCoach AI Server
Flask API for real-time driving analysis
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import torch
import cv2
import numpy as np
import librosa
import base64
from pathlib import Path
import io
from PIL import Image

# Import AI models
from AudioCNN import AudioCNN, CLASS_NAMES as AUDIO_CLASS_NAMES
from lane_detect import UNet as LaneUNet, predict_mask as lane_predict_mask
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)  # Enable CORS for mobile app

# Model paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
YOLO_MODEL_PATH = MODELS_DIR / "YOLO.pt"
LANE_MODEL_PATH = MODELS_DIR / "lane_detect.pt"
AUDIO_MODEL_PATH = MODELS_DIR / "AudioCNN.pt"

# Global model instances
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
yolo_model = None
lane_model = None
audio_model = None

def load_models():
    """Load all AI models on startup"""
    global yolo_model, lane_model, audio_model
    
    print(f"🔧 Loading models on device: {device}")
    
    # Load YOLO
    if YOLO_MODEL_PATH.exists():
        yolo_model = YOLO(str(YOLO_MODEL_PATH))
        print("✅ YOLO model loaded")
    else:
        print("⚠️  YOLO model not found")
    
    # Load Lane Detection
    if LANE_MODEL_PATH.exists():
        lane_model = LaneUNet(n_channels=3, n_classes=1, bilinear=True).to(device)
        checkpoint = torch.load(LANE_MODEL_PATH, map_location=device)
        if isinstance(checkpoint, dict) and "model" in checkpoint:
            checkpoint = checkpoint["model"]
        lane_model.load_state_dict(checkpoint, strict=False)
        lane_model.eval()
        print("✅ Lane detection model loaded")
    else:
        print("⚠️  Lane detection model not found")
    
    # Load Audio CNN
    if AUDIO_MODEL_PATH.exists():
        audio_model = AudioCNN(num_classes=len(AUDIO_CLASS_NAMES)).to(device)
        checkpoint = torch.load(AUDIO_MODEL_PATH, map_location=device)
        if isinstance(checkpoint, dict) and "model" in checkpoint:
            checkpoint = checkpoint["model"]
        audio_model.load_state_dict(checkpoint, strict=False)
        audio_model.eval()
        print("✅ Audio model loaded")
    else:
        print("⚠️  Audio model not found")

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        "service": "DrivingCoach AI Server",
        "status": "running",
        "device": str(device),
        "models": {
            "yolo": yolo_model is not None,
            "lane": lane_model is not None,
            "audio": audio_model is not None
        }
    })

@app.route('/api/analyze/image', methods=['POST'])
def analyze_image():
    """
    Analyze single image for objects and lane detection
    
    Request body:
    {
        "image": "base64_encoded_image"
    }
    """
    try:
        data = request.json
        if 'image' not in data:
            return jsonify({"error": "No image provided"}), 400
        
        # Decode base64 image
        image_data = base64.b64decode(data['image'])
        image = Image.open(io.BytesIO(image_data))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        results = {}
        
        # YOLO detection
        if yolo_model:
            detections = yolo_model(frame, conf=0.3)
            objects = []
            for det in detections[0].boxes:
                cls_idx = int(det.cls[0])
                name = detections[0].names.get(cls_idx, "unknown")
                x1, y1, x2, y2 = map(int, det.xyxy[0])
                conf = float(det.conf[0])
                
                objects.append({
                    "class": name,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })
            results['objects'] = objects
        
        # Lane detection
        if lane_model:
            resized = cv2.resize(frame, (256, 256))
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            tensor = torch.from_numpy(rgb.transpose(2, 0, 1)).unsqueeze(0)
            mask = lane_predict_mask(lane_model, tensor, device, 0.5).squeeze()
            
            # Calculate lane center
            h = mask.shape[0]
            lower = mask[int(h * 0.7):]
            coords = np.column_stack(np.where(lower > 0.5))
            
            if coords.size > 0:
                center = float(coords[:, 1].mean())
                offset = center - (mask.shape[1] / 2)
                results['lane'] = {
                    "detected": True,
                    "center": center,
                    "offset": offset
                }
            else:
                results['lane'] = {"detected": False}
        
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze/audio', methods=['POST'])
def analyze_audio():
    """
    Analyze audio chunk for sound classification
    
    Request body:
    {
        "audio": "base64_encoded_wav",
        "sample_rate": 16000
    }
    """
    try:
        if not audio_model:
            return jsonify({"error": "Audio model not loaded"}), 503
        
        data = request.json
        if 'audio' not in data:
            return jsonify({"error": "No audio provided"}), 400
        
        # Decode audio
        audio_data = base64.b64decode(data['audio'])
        sr = data.get('sample_rate', 16000)
        
        # Load audio from bytes
        audio_array, _ = librosa.load(io.BytesIO(audio_data), sr=sr, duration=2.0)
        
        # Create mel spectrogram
        mel = librosa.feature.melspectrogram(
            y=audio_array,
            sr=sr,
            n_fft=1024,
            hop_length=256,
            n_mels=64
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)
        mel_db = (mel_db - mel_db.mean()) / (mel_db.std() + 1e-6)
        
        # Predict
        tensor = torch.tensor(mel_db, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(device)
        with torch.no_grad():
            logits = audio_model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()
        
        top_idx = int(np.argmax(probs))
        top_label = AUDIO_CLASS_NAMES[top_idx]
        top_prob = float(probs[top_idx])
        
        predictions = {
            AUDIO_CLASS_NAMES[i]: float(p) 
            for i, p in enumerate(probs)
        }
        
        return jsonify({
            "success": True,
            "results": {
                "label": top_label,
                "confidence": top_prob,
                "all_predictions": predictions
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze/scenario', methods=['POST'])
def analyze_scenario():
    """
    Complete scenario analysis
    
    Request body:
    {
        "features": {
            "horn": bool,
            "blinker": bool,
            "wiper": bool,
            "lane_change": bool,
            "pedestrian": bool,
            "tailgating": bool,
            "sudden_stop": bool,
            "left_signal": bool,
            "right_signal": bool
        }
    }
    """
    try:
        data = request.json
        features = data.get('features', {})
        
        # Scenario evaluation logic
        scenario_id = 0
        message = "정상 운행"
        
        # Event 10: Sudden stop with horn
        if features.get('horn') and features.get('sudden_stop'):
            scenario_id = 10
            message = "급정거 중 경적 감지: 위협 운전입니다."
        
        # Event 9: Horn with pedestrian
        elif features.get('horn') and features.get('pedestrian'):
            scenario_id = 9
            message = "보행자 근처에서 경적이 울렸습니다."
        
        # Event 5: Lane change without blinker
        elif features.get('lane_change') and not features.get('blinker'):
            scenario_id = 5
            message = "방향지시등 없이 차선을 변경했습니다."
        
        # Event 7: Wiper + hazard
        elif features.get('wiper') and features.get('left_signal') and features.get('right_signal'):
            scenario_id = 7
            message = "와이퍼+비상등 감지: 전조등/안개등을 켜 주세요."
        
        return jsonify({
            "success": True,
            "scenario": {
                "id": scenario_id,
                "message": message
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    load_models()
    print("\n" + "="*50)
    print("🚗 DrivingCoach AI Server Starting...")
    print(f"📍 Device: {device}")
    print("="*50 + "\n")
    
    # Run Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
