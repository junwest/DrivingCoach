#!/usr/bin/env python3
"""
인터랙티브 비디오 디버거 - 프레임 추출 및 확인
"""
import cv2
import numpy as np
from pathlib import Path
import json

def load_roi_config(video_name: str, output_dir: Path):
    """ROI 설정 로드"""
    config_path = output_dir / f"{video_name}_roi_config.json"
    if not config_path.exists():
        return None
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return np.float32(config['roi_points'])

def extract_debug_frames():
    """디버그용 프레임 추출"""
    data_dir = Path(__file__).resolve().parent.parent / "Data"
    output_dir = Path(__file__).resolve().parent
    
    videos = [
        {
            "path": data_dir / "이벤트 4.mp4",
            "name": "이벤트 4",
            "frame_sec": 5.0  # 차선 변경 중간
        },
        {
            "path": data_dir / "이벤트 5.mp4",
            "name": "이벤트 5",
            "frame_sec": 6.5  # 차선 변경 중간
        }
    ]
    
    for video_info in videos:
        print(f"\n{'='*60}")
        print(f"🎬 {video_info['name']}")
        print(f"{'='*60}")
        
        # ROI 로드
        roi_points = load_roi_config(video_info['name'], output_dir)
        if roi_points is None:
            print(f"❌ ROI config not found for {video_info['name']}")
            continue
        
        print(f"ROI Points: {roi_points.tolist()}")
        
        # 비디오 로드
        cap = cv2.VideoCapture(str(video_info['path']))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        # 특정 프레임으로 이동
        frame_num = int(video_info['frame_sec'] * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print(f"❌ Failed to read frame")
            continue
        
        # 원본 프레임 저장
        original_path = output_dir / f"{video_info['name']}_original.jpg"
        cv2.imwrite(str(original_path), frame)
        print(f"✅ Original frame saved: {original_path}")
        
        # ROI 표시한 프레임 저장
        roi_frame = frame.copy()
        for i in range(4):
            pt1 = tuple(roi_points[i].astype(int))
            pt2 = tuple(roi_points[(i + 1) % 4].astype(int))
            cv2.line(roi_frame, pt1, pt2, (0, 255, 0), 3)
            cv2.circle(roi_frame, pt1, 8, (0, 0, 255), -1)
            cv2.putText(roi_frame, str(i+1), 
                       tuple((roi_points[i] + [15, -15]).astype(int)),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
        
        roi_vis_path = output_dir / f"{video_info['name']}_roi_visual.jpg"
        cv2.imwrite(str(roi_vis_path), roi_frame)
        print(f"✅ ROI visualization saved: {roi_vis_path}")
        
        # BEV 변환
        dst_points = np.float32([
            [0, 0],
            [400, 0],
            [400, 600],
            [0, 600]
        ])
        
        M = cv2.getPerspectiveTransform(roi_points, dst_points)
        bev_frame = cv2.warpPerspective(frame, M, (400, 600))
        
        bev_path = output_dir / f"{video_info['name']}_bev.jpg"
        cv2.imwrite(str(bev_path), bev_frame)
        print(f"✅ BEV frame saved: {bev_path}")
        
        # 차선 검출
        hsv = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2HSV)
        
        # 흰색
        lower_white = np.array([0, 0, 150])
        upper_white = np.array([180, 60, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # 노란색
        lower_yellow = np.array([10, 60, 60])
        upper_yellow = np.array([40, 255, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # Edge
        gray = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # 결합
        hsv_combined = cv2.bitwise_or(white_mask, yellow_mask)
        combined = cv2.bitwise_or(hsv_combined, edges)
        
        # Morphological
        kernel = np.ones((5, 5), np.uint8)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
        
        # 마스크 저장
        mask_path = output_dir / f"{video_info['name']}_lane_mask.jpg"
        cv2.imwrite(str(mask_path), combined)
        print(f"✅ Lane mask saved: {mask_path}")
        
        # 오버레이
        overlay = bev_frame.copy()
        overlay[combined > 127] = [255, 255, 255]
        
        overlay_path = output_dir / f"{video_info['name']}_overlay.jpg"
        cv2.imwrite(str(overlay_path), overlay)
        print(f"✅ Overlay saved: {overlay_path}")
        
        # 통계
        total_pixels = combined.shape[0] * combined.shape[1]
        lane_pixels = np.sum(combined > 127)
        percentage = 100 * lane_pixels / total_pixels
        
        print(f"\n📊 Statistics:")
        print(f"   Frame size: {frame.shape[1]}x{frame.shape[0]}")
        print(f"   BEV size: {bev_frame.shape[1]}x{bev_frame.shape[0]}")
        print(f"   Lane pixels: {lane_pixels}/{total_pixels} ({percentage:.1f}%)")

    print("\n" + "="*60)
    print("✅ 디버그 이미지 생성 완료!")
    print("="*60)
    print("\n확인할 이미지:")
    print("  *_original.jpg    - 원본 프레임")
    print("  *_roi_visual.jpg  - ROI 표시")
    print("  *_bev.jpg         - BEV 변환 결과")
    print("  *_lane_mask.jpg   - 차선 마스크")
    print("  *_overlay.jpg     - 오버레이")

if __name__ == "__main__":
    extract_debug_frames()
