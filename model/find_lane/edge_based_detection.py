#!/usr/bin/env python3
"""
Edge 기반 차선 변경 감지
======================
차량 중심 부근의 edge 강도를 모니터링하여 차선 변경 감지
"""
import cv2
import numpy as np
from pathlib import Path
import json

def load_roi_config(video_name: str, output_dir: Path):
    config_path = output_dir / f"{video_name}_roi_config.json"
    if not config_path.exists():
        return None
    with open(config_path, 'r') as f:
        config = json.load(f)
    return np.float32(config['roi_points'])

def detect_lanes_and_edges(bev_frame, exclude_bottom_height=100):
    """차선 및 Edge 검출"""
    h, w = bev_frame.shape[:2]
    
    # Edge detection
    gray = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    # 하단 마스킹
    mask = np.ones_like(edges)
    mask[h - exclude_bottom_height:, :] = 0
    edges = cv2.bitwise_and(edges, mask)
    
    return edges

def calculate_center_edge_intensity(edges, center_x, width=20):
    """
    차량 중심 부근의 edge 강도 계산
    
    Args:
        edges: Edge 이미지
        center_x: 차량 중심 x 좌표
        width: 중심 좌우로 체크할 너비
    
    Returns:
        edge 강도 (0-1 정규화)
    """
    h, w = edges.shape
    
    # 차량 중심 부근의 ROI
    x1 = max(0, center_x - width)
    x2 = min(w, center_x + width)
    
    # 중간 영역만 체크 (30-80%)
    y1 = int(h * 0.3)
    y2 = int(h * 0.8)
    
    roi = edges[y1:y2, x1:x2]
    
    # Edge 픽셀 비율
    total_pixels = roi.shape[0] * roi.shape[1]
    edge_pixels = np.sum(roi > 0)
    
    if total_pixels == 0:
        return 0.0
    
    intensity = edge_pixels / total_pixels
    
    return intensity

def detect_lane_crossing(edge_intensity_history, threshold=0.15, min_duration=3):
    """
    Edge 강도 이력으로 차선 횡단 감지
    
    Args:
        edge_intensity_history: [(frame, intensity), ...]
        threshold: Edge 강도 임계값
        min_duration: 최소 지속 프레임 수
    
    Returns:
        차선 횡단 여부
    """
    if len(edge_intensity_history) < min_duration:
        return False
    
    # 최근 프레임들의 강도
    recent_intensities = [intensity for _, intensity in edge_intensity_history[-min_duration:]]
    
    # 모두 임계값 이상이면 차선 횡단 중
    crossing = all(intensity > threshold for intensity in recent_intensities)
    
    return crossing

def process_video_with_edge_detection(
    video_path: Path,
    output_path: Path,
    src_points: np.ndarray,
    lane_change_start_sec: float,
    lane_change_end_sec: float,
    vehicle_center_x: int = 200  # BEV에서 차량 중심 x 좌표
):
    """Edge 기반 차선 변경 감지"""
    print(f"\n🎥 Processing: {video_path.name}")
    print(f"   Expected lane change: {lane_change_start_sec}s ~ {lane_change_end_sec}s")
    
    # BEV 변환
    dst_points = np.float32([[0, 0], [400, 0], [400, 600], [0, 600]])
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (800, 600))
    
    frame_count = 0
    edge_intensity_history = []
    lane_crossings = []
    
    lc_start_frame = int(lane_change_start_sec * fps)
    lc_end_frame = int(lane_change_end_sec * fps)
    
    print(f"\n처리 시작...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_count / fps
        
        # BEV 변환
        bev_frame = cv2.warpPerspective(frame, M, (400, 600))
        
        # Edge 검출
        edges = detect_lanes_and_edges(bev_frame, 100)
        
        # 중심 edge 강도 계산
        edge_intensity = calculate_center_edge_intensity(edges, vehicle_center_x, width=30)
        
        # 이력 저장
        edge_intensity_history.append((frame_count, edge_intensity))
        if len(edge_intensity_history) > 150:  # 5초치만 유지
            edge_intensity_history = edge_intensity_history[-150:]
        
        # 차선 횡단 감지
        is_crossing = detect_lane_crossing(edge_intensity_history, threshold=0.15, min_duration=5)
        
        if is_crossing:
            lane_crossings.append(frame_count)
        
        # 시각화
        # 좌측: BEV + Edge 오버레이
        left_panel = bev_frame.copy()
        
        # Edge를 빨간색으로 오버레이
        edge_color = np.zeros_like(left_panel)
        edge_color[edges > 0] = [0, 0, 255]  # 빨간색
        left_panel = cv2.addWeighted(left_panel, 0.7, edge_color, 0.3, 0)
        
        # 차량 중심 영역 표시 (초록색 박스)
        h = left_panel.shape[0]
        cv2.rectangle(left_panel, 
                     (vehicle_center_x - 30, int(h * 0.3)),
                     (vehicle_center_x + 30, int(h * 0.8)),
                     (0, 255, 0), 2)
        
        # 우측: Edge만 표시
        right_panel = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # 합성
        combined = np.hstack([left_panel, right_panel])
        
        # 정보 박스
        in_lane_change_zone = lc_start_frame <= frame_count <= lc_end_frame
        
        cv2.rectangle(combined, (5, 5), (795, 120), (0, 0, 0), -1)
        cv2.rectangle(combined, (5, 5), (795, 120), (255, 255, 255), 2)
        
        y_offset = 30
        cv2.putText(combined, f"Time: {current_time:.2f}s", 
                   (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 30
        
        # Edge 강도 표시
        intensity_color = (0, 255, 0) if edge_intensity < 0.15 else (0, 165, 255)
        cv2.putText(combined, f"Edge Intensity: {edge_intensity:.3f}", 
                   (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, intensity_color, 2)
        y_offset += 30
        
        # 차선 횡단 상태
        if is_crossing:
            cv2.putText(combined, ">>> CROSSING LANE <<<", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # 예상 구간 표시
        if in_lane_change_zone:
            cv2.rectangle(combined, (10, 550), (790, 590), (0, 165, 255), -1)
            cv2.putText(combined, "Expected Lane Change Zone", 
                       (200, 575), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 최근 감지 표시
        if frame_count in lane_crossings[-10:]:
            cv2.circle(combined, (750, 50), 20, (0, 0, 255), -1)
            cv2.putText(combined, "DETECTED", 
                       (620, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        writer.write(combined)
        
        frame_count += 1
        if frame_count % 30 == 0:
            status = "CHANGE_ZONE" if in_lane_change_zone else "NORMAL"
            crossing_str = "CROSSING!" if is_crossing else "normal"
            print(f"  Frame {frame_count}/{total_frames} ({current_time:.1f}s) [{status}] {crossing_str} intensity={edge_intensity:.3f}")
    
    cap.release()
    writer.release()
    
    # 분석 결과
    print(f"\n✅ Output saved: {output_path}")
    print(f"\n📊 차선 횡단 감지 분석:")
    print(f"   총 횡단 감지: {len(set(lane_crossings))} 프레임")
    
    if lane_crossings:
        # 연속된 구간으로 그룹핑
        crossing_events = []
        current_event_start = lane_crossings[0]
        current_event_end = lane_crossings[0]
        
        for i in range(1, len(lane_crossings)):
            if lane_crossings[i] - lane_crossings[i-1] <= 2:  # 2프레임 이내면 연속
                current_event_end = lane_crossings[i]
            else:
                crossing_events.append((current_event_start, current_event_end))
                current_event_start = lane_crossings[i]
                current_event_end = lane_crossings[i]
        
        crossing_events.append((current_event_start, current_event_end))
        
        print(f"   감지된 횡단 이벤트: {len(crossing_events)}회")
        for i, (start, end) in enumerate(crossing_events):
            start_time = start / fps
            end_time = end / fps
            in_expected = lc_start_frame <= start <= lc_end_frame
            status = "✅ 예상 구간" if in_expected else "⚠️ 예상 외"
            print(f"     {i+1}. {start_time:.2f}s ~ {end_time:.2f}s ({end-start+1} frames) {status}")
    
    return lane_crossings

def main():
    print("="*70)
    print(" Edge 기반 차선 변경 감지")
    print("="*70)
    
    data_dir = Path(__file__).resolve().parent.parent / "Data"
    output_dir = Path(__file__).resolve().parent
    
    videos = [
        {
            "path": data_dir / "이벤트 4.mp4",
            "name": "이벤트 4",
            "lane_change_start": 4.0,
            "lane_change_end": 6.0,
        },
        {
            "path": data_dir / "이벤트 5.mp4",
            "name": "이벤트 5",
            "lane_change_start": 5.0,
            "lane_change_end": 8.0,
        }
    ]
    
    for video_info in videos:
        print(f"\n{'='*70}")
        print(f"🎬 {video_info['name']}")
        print(f"{'='*70}")
        
        roi_points = load_roi_config(video_info['name'], output_dir)
        if roi_points is None:
            print(f"❌ ROI config not found")
            continue
        
        output_path = output_dir / f"{video_info['name']}_edge_detection.mp4"
        
        try:
            process_video_with_edge_detection(
                video_info['path'],
                output_path,
                roi_points,
                video_info['lane_change_start'],
                video_info['lane_change_end'],
                vehicle_center_x=200  # BEV 중심
            )
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("✅ Edge 기반 차선 변경 감지 완료!")
    print("="*70)

if __name__ == "__main__":
    main()
