#!/usr/bin/env python3
"""
개선된 비디오 처리 - 핸들 마스킹 포함
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

def detect_lanes_improved(bev_frame, exclude_bottom_height=100):
    """개선된 차선 검출 - 하단 영역 제외"""
    h, w = bev_frame.shape[:2]
    
    hsv = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2HSV)
    
    # 흰색
    lower_white = np.array([0, 0, 150])
    upper_white = np.array([180, 60, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # 노란색
    lower_yellow = np.array([10, 60, 60])
    upper_yellow = np.array([40, 255, 255])
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    # Edge detection
    gray = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    # 결합
    hsv_combined = cv2.bitwise_or(white_mask, yellow_mask)
    combined = cv2.bitwise_or(hsv_combined, edges)
    
    # Morphological operations
    kernel = np.ones((5, 5), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
    
    # 하단 영역 마스킹 (핸들 제외)
    mask = np.ones_like(combined)
    mask[h - exclude_bottom_height:, :] = 0  # 하단 100픽셀 제외
    combined = cv2.bitwise_and(combined, mask)
    
    return (combined > 127).astype(np.uint8)

def find_lane_boundaries(lane_mask, roi_bottom=None):
    """차선 경계 찾기"""
    if lane_mask.sum() == 0:
        return None, None, None
    
    height = lane_mask.shape[0]
    
    if roi_bottom is None:
        roi_bottom = int(height * 0.8)  # 더 위쪽만 사용
    roi_top = int(height * 0.3)
    
    roi = lane_mask[roi_top:roi_bottom, :]
    
    # 가중치
    weights = np.linspace(0.5, 1.0, roi.shape[0])[:, np.newaxis]
    weighted_roi = roi.astype(np.float32) * weights
    column_sums = weighted_roi.sum(axis=0)
    
    lane_threshold = 3
    lane_columns = np.where(column_sums > lane_threshold)[0]
    
    if len(lane_columns) == 0:
        return None, None, None
    
    # 클러스터링
    lane_groups = []
    current_group = [lane_columns[0]]
    
    for i in range(1, len(lane_columns)):
        if lane_columns[i] - lane_columns[i-1] <= 8:
            current_group.append(lane_columns[i])
        else:
            if len(current_group) >= 2:
                lane_groups.append(current_group)
            current_group = [lane_columns[i]]
    
    if len(current_group) >= 2:
        lane_groups.append(current_group)
    
    if len(lane_groups) == 0:
        return None, None, None
    
    # 각 그룹의 가중 중심
    lane_centers = []
    for group in lane_groups:
        weights_for_group = column_sums[group]
        if weights_for_group.sum() > 0:
            weighted_center = np.average(group, weights=weights_for_group)
            lane_centers.append(int(weighted_center))
    
    if len(lane_centers) == 0:
        return None, None, None
    
    # 가장 왼쪽과 오른쪽 차선
    left_lane_x = min(lane_centers) if len(lane_centers) > 0 else None
    right_lane_x = max(lane_centers) if len(lane_centers) > 1 else None
    
    # 차선 중심
    if left_lane_x is not None and right_lane_x is not None:
        lane_center_x = int((left_lane_x + right_lane_x) / 2)
    else:
        lane_center_x = None
    
    return left_lane_x, right_lane_x, lane_center_x

def process_video(
    video_path: Path,
    output_path: Path,
    src_points: np.ndarray,
    lane_change_start_sec: float,
    lane_change_end_sec: float,
    exclude_bottom: int = 100  # 하단 제외 높이
):
    """비디오 처리 - 핸들 영역 제외"""
    print(f"\n🎥 Processing: {video_path.name}")
    print(f"   Lane change: {lane_change_start_sec}s ~ {lane_change_end_sec}s")
    print(f"   Exclude bottom: {exclude_bottom}px (steering wheel)")
    
    # BEV 변환 매트릭스
    dst_points = np.float32([[0, 0], [400, 0], [400, 600], [0, 600]])
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (400, 600))
    
    frame_count = 0
    lane_change_detected = []
    prev_lane_center = None
    
    lc_start_frame = int(lane_change_start_sec * fps)
    lc_end_frame = int(lane_change_end_sec * fps)
    
    print(f"\n처리 시작 (총 {total_frames} 프레임)...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_count / fps
        
        # BEV 변환
        bev_frame = cv2.warpPerspective(frame, M, (400, 600))
        
        # 차선 검출 (하단 제외)
        lane_mask = detect_lanes_improved(bev_frame, exclude_bottom)
        
        # 차선 경계 찾기
        left_x, right_x, center_x = find_lane_boundaries(lane_mask)
        
        # 시각화
        overlay = bev_frame.copy()
        
        # 제외 영역 표시 (반투명 회색)
        h = overlay.shape[0]
        excluded_region = overlay[h - exclude_bottom:, :].copy()
        excluded_region = cv2.addWeighted(excluded_region, 0.5, 
                                         np.full_like(excluded_region, 50), 0.5, 0)
        overlay[h - exclude_bottom:, :] = excluded_region
        
        # 차선 마스크 오버레이
        lane_mask_color = np.zeros_like(overlay)
        lane_mask_color[lane_mask > 0] = [255, 255, 255]
        overlay = cv2.addWeighted(overlay, 0.6, lane_mask_color, 0.4, 0)
        
        in_lane_change_zone = lc_start_frame <= frame_count <= lc_end_frame
        
        # 차선 경계 그리기
        if left_x is not None:
            cv2.line(overlay, (left_x, 0), (left_x, h - exclude_bottom), (255, 0, 0), 4)
            cv2.putText(overlay, "LEFT", (left_x - 40, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        if right_x is not None:
            cv2.line(overlay, (right_x, 0), (right_x, h - exclude_bottom), (255, 0, 0), 4)
            cv2.putText(overlay, "RIGHT", (right_x - 45, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # 차선 중심선
        if center_x is not None:
            cv2.line(overlay, (center_x, 0), (center_x, h - exclude_bottom), (0, 255, 0), 3)
            
            # 차선 변경 감지
            if prev_lane_center is not None:
                center_shift = abs(center_x - prev_lane_center)
                if center_shift > 20 and in_lane_change_zone:
                    lane_change_detected.append(frame_count)
            
            prev_lane_center = center_x
        
        # 정보 박스
        cv2.rectangle(overlay, (5, 5), (395, 130), (0, 0, 0), -1)
        cv2.rectangle(overlay, (5, 5), (395, 130), (255, 255, 255), 2)
        
        y_offset = 25
        cv2.putText(overlay, f"Time: {current_time:.2f}s", 
                   (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 25
        
        if left_x is not None and right_x is not None:
            lane_width = right_x - left_x
            cv2.putText(overlay, f"Width: {lane_width}px", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25
        
        if center_x is not None:
            cv2.putText(overlay, f"Center: {center_x}px", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25
        
        if in_lane_change_zone:
            cv2.putText(overlay, ">>> LANE CHANGE ZONE <<<", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        
        # 차선 변경 감지 표시
        if frame_count in lane_change_detected[-5:]:
            cv2.rectangle(overlay, (10, h - exclude_bottom - 50), (390, h - exclude_bottom - 10), 
                         (0, 0, 255), -1)
            cv2.putText(overlay, "CHANGE DETECTED!", 
                       (40, h - exclude_bottom - 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        writer.write(overlay)
        
        frame_count += 1
        if frame_count % 30 == 0:
            status = "LANE_CHANGE" if in_lane_change_zone else "NORMAL"
            print(f"  Frame {frame_count}/{total_frames} ({current_time:.1f}s) [{status}]")
    
    cap.release()
    writer.release()
    
    print(f"\n✅ Output saved: {output_path}")
    print(f"   Lane changes detected: {len(lane_change_detected)} times")
    
    return lane_change_detected

def main():
    print("="*70)
    print(" 개선된 비디오 처리 (핸들 영역 제외)")
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
        
        # ROI 로드
        roi_points = load_roi_config(video_info['name'], output_dir)
        if roi_points is None:
            print(f"❌ ROI config not found for {video_info['name']}")
            continue
        
        print(f"ROI Points: {roi_points.tolist()}")
        
        # 비디오 처리
        output_path = output_dir / f"{video_info['name']}_final.mp4"
        
        lane_changes = process_video(
            video_info['path'],
            output_path,
            roi_points,
            video_info['lane_change_start'],
            video_info['lane_change_end'],
            exclude_bottom=100  # 핸들 영역 제외
        )
        
        print(f"\n📊 분석 결과:")
        print(f"   차선 변경 감지 횟수: {len(lane_changes)}")
        if lane_changes:
            fps = 30
            times = [f / fps for f in lane_changes]
            print(f"   감지 시간: {min(times):.2f}s ~ {max(times):.2f}s")
    
    print("\n" + "="*70)
    print("✅ 모든 비디오 처리 완료!")
    print("="*70)

if __name__ == "__main__":
    main()
