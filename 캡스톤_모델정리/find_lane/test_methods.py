#!/usr/bin/env python3
"""
차선 검출 개선 도구 - 다양한 방법 비교
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2
import numpy as np

# BEV transformation
H_MATRIX = np.array([
    [-3.97727273e-02, -3.24810606e-01, 1.00492424e02],
    [4.37257068e-16, -2.54829545e00, 7.89971591e02],
    [1.16574774e-18, -3.69318182e-03, 1.00000000e00],
])

MY_CAR_BEV_X = 105
MY_CAR_BEV_Y = 400

def method1_hsv_basic(bev_frame):
    """기본 HSV 방법"""
    hsv = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2HSV)
    
    # 흰색
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([180, 50, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # 노란색
    lower_yellow = np.array([15, 80, 80])
    upper_yellow = np.array([35, 255, 255])
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    combined = cv2.bitwise_or(white_mask, yellow_mask)
    return combined

def method2_hsv_tuned(bev_frame):
    """튜닝된 HSV 방법 (파라미터 완화)"""
    hsv = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2HSV)
    
    # 흰색 - 더 넓은 범위
    lower_white = np.array([0, 0, 150])  # 밝기 낮춤
    upper_white = np.array([180, 60, 255])  # 채도 증가
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # 노란색 - 더 넓은 범위
    lower_yellow = np.array([10, 60, 60])  # 모든 범위 완화
    upper_yellow = np.array([40, 255, 255])
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    combined = cv2.bitwise_or(white_mask, yellow_mask)
    
    # Morphological operations
    kernel = np.ones((3, 3), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
    
    return combined

def method3_edge_based(bev_frame):
    """엣지 기반 방법 (Canny + 형태학)"""
    gray = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2GRAY)
    
    # Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Canny edge detection
    edges = cv2.Canny(blurred, 50, 150)
    
    # Morphological operations to connect edges
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    
    return edges

def method4_combined(bev_frame):
    """결합 방법 (HSV + Edge)"""
    hsv_mask = method2_hsv_tuned(bev_frame)
    edge_mask = method3_edge_based(bev_frame)
    
    # 두 방법 결합
    combined = cv2.bitwise_or(hsv_mask, edge_mask)
    
    # Morphological operations
    kernel = np.ones((5, 5), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
    
    return combined

def method5_adaptive_threshold(bev_frame):
    """적응형 임계값 방법"""
    gray = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2GRAY)
    
    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Morphological operations
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return thresh

# Load test frame
video_path = Path(__file__).resolve().parent.parent / "Data" / "이벤트 4.mp4"
cap = cv2.VideoCapture(str(video_path))
cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
ret, frame = cap.read()
cap.release()

if not ret:
    print("Failed to read frame")
    sys.exit(1)

# Apply BEV
bev_frame = cv2.warpPerspective(frame, H_MATRIX, (210, 600), flags=cv2.INTER_LINEAR)

# Test all methods
debug_dir = Path(__file__).resolve().parent
results = {
    "1_hsv_basic": method1_hsv_basic(bev_frame),
    "2_hsv_tuned": method2_hsv_tuned(bev_frame),
    "3_edge_based": method3_edge_based(bev_frame),
    "4_combined": method4_combined(bev_frame),
    "5_adaptive": method5_adaptive_threshold(bev_frame),
}

# Save all results
cv2.imwrite(str(debug_dir / "original_bev.jpg"), bev_frame)
print("Saved: original_bev.jpg")

for name, mask in results.items():
    cv2.imwrite(str(debug_dir / f"method_{name}.jpg"), mask)
    
    # Create overlay
    overlay = bev_frame.copy()
    overlay[mask > 127] = [255, 255, 255]
    cv2.imwrite(str(debug_dir / f"overlay_{name}.jpg"), overlay)
    
    # Count pixels
    pixel_count = np.sum(mask > 127)
    percentage = 100 * pixel_count / (mask.shape[0] * mask.shape[1])
    print(f"{name}: {pixel_count} pixels ({percentage:.1f}%)")

print(f"\nAll test images saved to: {debug_dir}")
print("\n추천:")
print("- 각 방법의 overlay 이미지를 확인하세요")
print("- 가장 잘 작동하는 방법을 선택하세요")
print("- 필요시 파라미터를 조정하세요")
