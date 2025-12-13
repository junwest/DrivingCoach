#!/usr/bin/env python3
"""
Debug script to check lane detection on a single frame
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2
import numpy as np
import torch
from lane_detect import UNet as LaneUNet
from lane_detect import predict_mask

# Load model
model_path = Path(__file__).resolve().parent.parent / "models" / "lane_detect.pt"
device = torch.device("cpu")

print(f"Loading model from: {model_path}")
model = LaneUNet(n_channels=3, n_classes=1, bilinear=True).to(device)

checkpoint = torch.load(model_path, map_location=device)
if isinstance(checkpoint, dict) and "model" in checkpoint:
    checkpoint = checkpoint["model"]
model.load_state_dict(checkpoint, strict=False)
model.eval()

print("Model loaded successfully")

# Load a test frame from Event 4
video_path = Path(__file__).resolve().parent.parent / "Data" / "이벤트 4.mp4"
cap = cv2.VideoCapture(str(video_path))

# Get a frame from the middle
cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
ret, frame = cap.read()
cap.release()

if not ret:
    print("Failed to read frame")
    sys.exit(1)

print(f"Frame shape: {frame.shape}")

# BEV transformation
H_MATRIX = np.array([
    [-3.97727273e-02, -3.24810606e-01, 1.00492424e02],
    [4.37257068e-16, -2.54829545e00, 7.89971591e02],
    [1.16574774e-18, -3.69318182e-03, 1.00000000e00],
])

bev_frame = cv2.warpPerspective(frame, H_MATRIX, (210, 600), flags=cv2.INTER_LINEAR)
print(f"BEV frame shape: {bev_frame.shape}")

# Save BEV frame for visual inspection
debug_dir = Path(__file__).resolve().parent
cv2.imwrite(str(debug_dir / "debug_bev.jpg"), bev_frame)
print(f"Saved BEV frame to: {debug_dir / 'debug_bev.jpg'}")

# Predict lane mask
resized = cv2.resize(bev_frame, (256, 256))
rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
tensor = torch.from_numpy(rgb.transpose(2, 0, 1)).unsqueeze(0)

mask = predict_mask(model, tensor, device, 0.5)
mask_squeezed = mask.squeeze()

print(f"Mask shape: {mask_squeezed.shape}")
print(f"Mask min: {mask_squeezed.min()}, max: {mask_squeezed.max()}")
print(f"Mask non-zero pixels: {np.sum(mask_squeezed > 0.5)}")

# Resize back to BEV size
mask_resized = cv2.resize(
    mask_squeezed.astype(np.float32), 
    (210, 600), 
    interpolation=cv2.INTER_NEAREST
)

# Save mask for visual inspection
mask_viz = (mask_resized * 255).astype(np.uint8)
cv2.imwrite(str(debug_dir / "debug_mask.jpg"), mask_viz)
print(f"Saved mask to: {debug_dir / 'debug_mask.jpg'}")

# Create overlay
overlay = bev_frame.copy()
overlay[mask_resized > 0.5] = [255, 255, 255]
cv2.imwrite(str(debug_dir / "debug_overlay.jpg"), overlay)
print(f"Saved overlay to: {debug_dir / 'debug_overlay.jpg'}")

print("\nDone! Check the debug images.")
