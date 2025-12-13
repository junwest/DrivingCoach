#!/usr/bin/env python3
"""
DrivingCoach AI Server (FastAPI + Async)
High-performance async API for real-time driving analysis
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
import cv2
import numpy as np
import librosa
import base64
from pathlib import Path
import io
from PIL import Image
from typing import List, Dict, Optional
import asyncio

# Import AI models
from AudioCNN import AudioCNN, CLASS_NAMES as AUDIO_CLASS_NAMES
from lane_detect import UNet as LaneUNet, predict_mask as lane_predict_mask
from ultralytics import YOLO

# FastAPI app
app = FastAPI(
    title="DrivingCoach AI API",
    description="Real-time driving behavior analysis using AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# Pydantic models for request/response validation
class ImageAnalysisRequest(BaseModel):
    image: str  # base64 encoded


class AudioAnalysisRequest(BaseModel):
    audio: str  # base64 encoded
    sample_rate: int = 16000


class ScenarioFeatures(BaseModel):
    horn: bool = False
    blinker: bool = False
    wiper: bool = False
    lane_change: bool = False
    pedestrian: bool = False
    tailgating: bool = False
    sudden_stop: bool = False
    left_signal: bool = False
    right_signal: bool = False


class ObjectDetection(BaseModel):
    class_name: str
    confidence: float
    bbox: List[int]


class LaneDetection(BaseModel):
    detected: bool
    center: Optional[float] = None
    offset: Optional[float] = None


class ImageAnalysisResponse(BaseModel):
    success: bool
    objects: List[ObjectDetection]
    lane: LaneDetection


class AudioAnalysisResponse(BaseModel):
    success: bool
    label: str
    confidence: float
    all_predictions: Dict[str, float]


class ScenarioResponse(BaseModel):
    success: bool
    scenario_id: int
    message: str


@app.on_event("startup")
async def load_models():
    """Load all AI models on startup"""
    global yolo_model, lane_model, audio_model
    
    print(f"\n{'='*60}")
    print(f"🔧 Loading AI models on device: {device}")
    print(f"{'='*60}\n")
    
    # Load YOLO (async wrapper for sync operation)
    if YOLO_MODEL_PATH.exists():
        await asyncio.to_thread(_load_yolo)
        print("✅ YOLO model loaded")
    else:
        print("⚠️  YOLO model not found")
    
    # Load Lane Detection
    if LANE_MODEL_PATH.exists():
        await asyncio.to_thread(_load_lane_model)
        print("✅ Lane detection model loaded")
    else:
        print("⚠️  Lane detection model not found")
    
    # Load Audio CNN
    if AUDIO_MODEL_PATH.exists():
        await asyncio.to_thread(_load_audio_model)
        print("✅ Audio model loaded")
    else:
        print("⚠️  Audio model not found")
    
    print(f"\n{'='*60}")
    print("🚀 DrivingCoach AI Server Ready!")
    print(f"{'='*60}\n")


def _load_yolo():
    """Synchronous YOLO loading"""
    global yolo_model
    yolo_model = YOLO(str(YOLO_MODEL_PATH))


def _load_lane_model():
    """Synchronous lane model loading"""
    global lane_model
    lane_model = LaneUNet(n_channels=3, n_classes=1, bilinear=True).to(device)
    checkpoint = torch.load(LANE_MODEL_PATH, map_location=device)
    if isinstance(checkpoint, dict) and "model" in checkpoint:
        checkpoint = checkpoint["model"]
    lane_model.load_state_dict(checkpoint, strict=False)
    lane_model.eval()


def _load_audio_model():
    """Synchronous audio model loading"""
    global audio_model
    audio_model = AudioCNN(num_classes=len(AUDIO_CLASS_NAMES)).to(device)
    checkpoint = torch.load(AUDIO_MODEL_PATH, map_location=device)
    if isinstance(checkpoint, dict) and "model" in checkpoint:
        checkpoint = checkpoint["model"]
    audio_model.load_state_dict(checkpoint, strict=False)
    audio_model.eval()


@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "DrivingCoach AI Server",
        "status": "running",
        "device": str(device),
        "models": {
            "yolo": yolo_model is not None,
            "lane": lane_model is not None,
            "audio": audio_model is not None
        }
    }


@app.post("/api/analyze/image", response_model=ImageAnalysisResponse)
async def analyze_image(request: ImageAnalysisRequest):
    """
    Analyze single image for objects and lane detection (async)
    """
    try:
        # Decode base64 image (I/O operation - run in thread)
        image_data = await asyncio.to_thread(base64.b64decode, request.image)
        image = await asyncio.to_thread(Image.open, io.BytesIO(image_data))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Run inference in parallel
        objects_task = asyncio.create_task(_detect_objects(frame))
        lane_task = asyncio.create_task(_detect_lane(frame))
        
        objects, lane = await asyncio.gather(objects_task, lane_task)
        
        return ImageAnalysisResponse(
            success=True,
            objects=objects,
            lane=lane
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _detect_objects(frame: np.ndarray) -> List[ObjectDetection]:
    """Async YOLO object detection"""
    if not yolo_model:
        return []
    
    # Run YOLO in thread (blocking operation)
    detections = await asyncio.to_thread(yolo_model, frame, conf=0.3)
    
    objects = []
    for det in detections[0].boxes:
        cls_idx = int(det.cls[0])
        name = detections[0].names.get(cls_idx, "unknown")
        x1, y1, x2, y2 = map(int, det.xyxy[0])
        conf = float(det.conf[0])
        
        objects.append(ObjectDetection(
            class_name=name,
            confidence=conf,
            bbox=[x1, y1, x2, y2]
        ))
    
    return objects


async def _detect_lane(frame: np.ndarray) -> LaneDetection:
    """Async lane detection"""
    if not lane_model:
        return LaneDetection(detected=False)
    
    # Preprocessing
    resized = cv2.resize(frame, (256, 256))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    tensor = torch.from_numpy(rgb.transpose(2, 0, 1)).unsqueeze(0)
    
    # Run model in thread
    mask = await asyncio.to_thread(
        lane_predict_mask, lane_model, tensor, device, 0.5
    )
    mask = mask.squeeze()
    
    # Calculate lane center
    h = mask.shape[0]
    lower = mask[int(h * 0.7):]
    coords = np.column_stack(np.where(lower > 0.5))
    
    if coords.size > 0:
        center = float(coords[:, 1].mean())
        offset = center - (mask.shape[1] / 2)
        return LaneDetection(
            detected=True,
            center=center,
            offset=offset
        )
    
    return LaneDetection(detected=False)


@app.post("/api/analyze/audio", response_model=AudioAnalysisResponse)
async def analyze_audio(request: AudioAnalysisRequest):
    """
    Analyze audio chunk for sound classification (async)
    """
    try:
        if not audio_model:
            raise HTTPException(status_code=503, detail="Audio model not loaded")
        
        # Decode audio (I/O operation)
        audio_data = await asyncio.to_thread(base64.b64decode, request.audio)
        
        # Load audio
        audio_array, _ = await asyncio.to_thread(
            librosa.load, 
            io.BytesIO(audio_data), 
            sr=request.sample_rate, 
            duration=2.0
        )
        
        # Create mel spectrogram (CPU-intensive - run in thread)
        predictions = await asyncio.to_thread(
            _process_audio, audio_array, request.sample_rate
        )
        
        top_idx = int(np.argmax(list(predictions.values())))
        top_label = AUDIO_CLASS_NAMES[top_idx]
        top_prob = predictions[top_label]
        
        return AudioAnalysisResponse(
            success=True,
            label=top_label,
            confidence=top_prob,
            all_predictions=predictions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _process_audio(audio_array: np.ndarray, sr: int) -> Dict[str, float]:
    """Synchronous audio processing and inference"""
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
    
    return {AUDIO_CLASS_NAMES[i]: float(p) for i, p in enumerate(probs)}


@app.post("/api/analyze/scenario", response_model=ScenarioResponse)
async def analyze_scenario(features: ScenarioFeatures):
    """
    Complete scenario analysis (lightweight, no need for thread)
    """
    try:
        scenario_id = 0
        message = "정상 운행"
        
        # Event 10: Sudden stop with horn
        if features.horn and features.sudden_stop:
            scenario_id = 10
            message = "급정거 중 경적 감지: 위협 운전입니다."
        
        # Event 9: Horn with pedestrian
        elif features.horn and features.pedestrian:
            scenario_id = 9
            message = "보행자 근처에서 경적이 울렸습니다."
        
        # Event 5: Lane change without blinker
        elif features.lane_change and not features.blinker:
            scenario_id = 5
            message = "방향지시등 없이 차선을 변경했습니다."
        
        # Event 7: Wiper + hazard
        elif features.wiper and features.left_signal and features.right_signal:
            scenario_id = 7
            message = "와이퍼+비상등 감지: 전조등/안개등을 켜 주세요."
        
        return ScenarioResponse(
            success=True,
            scenario_id=scenario_id,
            message=message
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000)
