#!/usr/bin/env python3
"""
인터랙티브 ROI 선택 및 차선 변경 감지 도구 (자동 진행 버전)
========================================
1. 4개의 점을 클릭하여 ROI 정의
2. 자동으로 BEV 변환 적용
3. 차선 검출 및 시각화
4. 차선 변경 자동 감지
"""

import cv2
import numpy as np
from pathlib import Path
import json

# Global variables
points = []
frame_original = None

def mouse_callback(event, x, y, flags, param):
    """마우스 클릭 이벤트 핸들러"""
    global points, frame_original
    
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(points) < 4:
            points.append([x, y])
            print(f"점 {len(points)}: ({x}, {y})")
            
            # Draw point
            cv2.circle(frame_original, (x, y), 5, (0, 255, 0), -1)
            cv2.putText(
                frame_original, 
                str(len(points)), 
                (x + 10, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (0, 255, 0), 
                2
            )
            
            # Draw line between points
            if len(points) > 1:
                cv2.line(
                    frame_original, 
                    tuple(points[-2]), 
                    tuple(points[-1]), 
                    (0, 255, 0), 
                    2
                )
            
            cv2.imshow("Select ROI Points", frame_original)
            
            if len(points) == 4:
                # Close the polygon
                cv2.line(
                    frame_original, 
                    tuple(points[-1]), 
                    tuple(points[0]), 
                    (0, 255, 0), 
                    2
                )
                cv2.imshow("Select ROI Points", frame_original)
                print("\n✅ 4개 점 선택 완료! 2초 후 자동으로 진행됩니다...")
                cv2.waitKey(2000)  # 2초 대기 후 자동 진행
                cv2.destroyAllWindows()

def select_roi_points(frame):
    """4개의 ROI 포인트를 선택"""
    global points, frame_original
    
    points = []
    frame_original = frame.copy()
    
    cv2.namedWindow("Select ROI Points")
    cv2.setMouseCallback("Select ROI Points", mouse_callback)
    
    print("\n" + "="*60)
    print("ROI 선택 가이드")
    print("="*60)
    print("차선을 포함하는 사각형 영역을 지정하세요:")
    print("1. 좌상단 (왼쪽 위)")
    print("2. 우상단 (오른쪽 위)")
    print("3. 우하단 (오른쪽 아래)")
    print("4. 좌하단 (왼쪽 아래)")
    print("\n마우스로 순서대로 4개의 점을 클릭하세요.")
    print("="*60 + "\n")
    
    cv2.imshow("Select ROI Points", frame_original)
    
    # 4개 점이 선택될 때까지 대기
    while len(points) < 4:
        cv2.waitKey(100)
    
    return np.float32(points)

def compute_bev_transform(src_points, dst_width=400, dst_height=600):
    """BEV 변환 매트릭스 계산"""
    dst_points = np.float32([
        [0, 0],                      # 좌상단
        [dst_width, 0],              # 우상단
        [dst_width, dst_height],     # 우하단
        [0, dst_height]              # 좌하단
    ])
    
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    return M, dst_width, dst_height

def detect_lanes_improved(bev_frame):
    """개선된 차선 검출"""
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
    
    return (combined > 127).astype(np.uint8)

def find_lane_boundaries(lane_mask, roi_bottom=None):
    """차선 경계 찾기"""
    if lane_mask.sum() == 0:
        return None, None, None
    
    height = lane_mask.shape[0]
    
    if roi_bottom is None:
        roi_bottom = int(height * 0.9)
    roi_top = int(height * 0.4)
    
    roi = lane_mask[roi_top:roi_bottom, :]
    
    # 가중치 (아래쪽에 더 높은 가중치)
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

def process_video_with_lane_change_detection(
    video_path: Path,
    output_path: Path,
    src_points: np.ndarray,
    lane_change_start_sec: float,
    lane_change_end_sec: float,
    dst_width: int = 400,
    dst_height: int = 600
):
    """비디오 처리 및 차선 변경 감지"""
    print(f"\n🎥 Processing: {video_path.name}")
    print(f"   Lane change: {lane_change_start_sec}s ~ {lane_change_end_sec}s")
    
    # BEV 변환 매트릭스 계산
    M, w, h = compute_bev_transform(src_points, dst_width, dst_height)
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Create output writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))
    
    frame_count = 0
    lane_change_detected = []
    prev_lane_center = None
    
    # 차선 변경 구간 프레임 범위
    lc_start_frame = int(lane_change_start_sec * fps)
    lc_end_frame = int(lane_change_end_sec * fps)
    
    print(f"\n처리 시작 (총 {total_frames} 프레임)...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_count / fps
        
        # BEV 변환
        bev_frame = cv2.warpPerspective(frame, M, (w, h))
        
        # 차선 검출
        lane_mask = detect_lanes_improved(bev_frame)
        
        # 차선 경계 찾기
        left_x, right_x, center_x = find_lane_boundaries(lane_mask)
        
        # 시각화
        overlay = bev_frame.copy()
        
        # 차선 마스크 오버레이
        lane_mask_color = np.zeros_like(overlay)
        lane_mask_color[lane_mask > 0] = [255, 255, 255]
        overlay = cv2.addWeighted(overlay, 0.6, lane_mask_color, 0.4, 0)
        
        # 차선 변경 구간 확인
        in_lane_change_zone = lc_start_frame <= frame_count <= lc_end_frame
        
        # 차선 경계 그리기
        if left_x is not None:
            cv2.line(overlay, (left_x, 0), (left_x, h), (255, 0, 0), 4)
            cv2.putText(overlay, "LEFT", (left_x - 40, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        if right_x is not None:
            cv2.line(overlay, (right_x, 0), (right_x, h), (255, 0, 0), 4)
            cv2.putText(overlay, "RIGHT", (right_x - 45, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # 차선 중심선
        if center_x is not None:
            cv2.line(overlay, (center_x, 0), (center_x, h), (0, 255, 0), 3)
            cv2.putText(overlay, "CENTER", (center_x - 45, h - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 차선 변경 감지
            if prev_lane_center is not None:
                center_shift = abs(center_x - prev_lane_center)
                if center_shift > 20 and in_lane_change_zone:
                    lane_change_detected.append(frame_count)
            
            prev_lane_center = center_x
        
        # 정보 박스
        box_height = 150
        cv2.rectangle(overlay, (5, 5), (w - 5, box_height), (0, 0, 0), -1)
        cv2.rectangle(overlay, (5, 5), (w - 5, box_height), (255, 255, 255), 2)
        
        y_offset = 30
        cv2.putText(overlay, f"Time: {current_time:.2f}s / {total_frames/fps:.2f}s", 
                   (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 30
        
        if left_x is not None and right_x is not None:
            lane_width = right_x - left_x
            cv2.putText(overlay, f"Lane Width: {lane_width}px", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 30
        
        if center_x is not None:
            cv2.putText(overlay, f"Center: {center_x}px", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 30
        
        # 차선 변경 구간 표시
        if in_lane_change_zone:
            cv2.putText(overlay, ">>> LANE CHANGE ZONE <<<", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        
        # 감지된 차선 변경 표시
        if frame_count in lane_change_detected[-10:]:
            cv2.rectangle(overlay, (10, h - 60), (w - 10, h - 10), (0, 0, 255), -1)
            cv2.putText(overlay, "!!! CHANGE DETECTED !!!", 
                       (w//2 - 120, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        writer.write(overlay)
        
        frame_count += 1
        if frame_count % 30 == 0:
            status = "LANE_CHANGE" if in_lane_change_zone else "NORMAL"
            print(f"  Frame {frame_count}/{total_frames} ({current_time:.1f}s) [{status}]")
    
    cap.release()
    writer.release()
    
    print(f"\n✅ Output saved: {output_path}")
    print(f"   Total frames: {total_frames}")
    print(f"   Lane changes detected: {len(lane_change_detected)} times")
    
    return lane_change_detected

def save_roi_config(video_name: str, points: np.ndarray, output_dir: Path):
    """ROI 설정 저장"""
    config_path = output_dir / f"{video_name}_roi_config.json"
    
    config = {
        "video_name": video_name,
        "roi_points": points.tolist(),
        "description": "ROI points: top-left, top-right, bottom-right, bottom-left"
    }
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"💾 ROI config saved: {config_path}")

def load_roi_config(config_path: Path):
    """ROI 설정 로드"""
    if not config_path.exists():
        return None
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return np.float32(config['roi_points'])

def main():
    print("="*70)
    print(" 인터랙티브 ROI 선택 및 차선 변경 감지 도구")
    print("="*70)
    
    # 비디오 경로
    data_dir = Path(__file__).resolve().parent.parent / "Data"
    output_dir = Path(__file__).resolve().parent
    
    videos = [
        {
            "path": data_dir / "이벤트 4.mp4",
            "name": "이벤트 4",
            "lane_change_start": 4.0,
            "lane_change_end": 6.0,
            "description": "오른쪽 → 왼쪽 차선 변경"
        },
        {
            "path": data_dir / "이벤트 5.mp4",
            "name": "이벤트 5",
            "lane_change_start": 5.0,
            "lane_change_end": 8.0,
            "description": "왼쪽 → 오른쪽 차선 변경"
        }
    ]
    
    for video_info in videos:
        print(f"\n{'='*70}")
        print(f"🎬 {video_info['name']}: {video_info['description']}")
        print(f"   차선 변경 구간: {video_info['lane_change_start']}s ~ {video_info['lane_change_end']}s")
        print(f"{'='*70}")
        
        # 비디오 로드
        video_path = video_info['path']
        cap = cv2.VideoCapture(str(video_path))
        
        # 첫 프레임 가져오기
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print(f"❌ Failed to read video: {video_path}")
            continue
        
        # ROI 설정 로드 또는 선택
        config_path = output_dir / f"{video_info['name']}_roi_config.json"
        roi_points = load_roi_config(config_path)
        
        if roi_points is not None:
            print(f"\n✅ Loaded ROI config from: {config_path}")
            print(f"   Points: {roi_points.tolist()}")
            use_existing = input("기존 ROI 사용? (y/n, 기본 y): ").strip().lower()
            
            if use_existing == 'n':
                roi_points = select_roi_points(frame)
                save_roi_config(video_info['name'], roi_points, output_dir)
        else:
            print(f"\n⚠️  ROI config not found. Please select ROI points.")
            roi_points = select_roi_points(frame)
            save_roi_config(video_info['name'], roi_points, output_dir)
        
        # 비디오 처리
        output_path = output_dir / f"{video_info['name']}_interactive.mp4"
        
        lane_changes = process_video_with_lane_change_detection(
            video_path,
            output_path,
            roi_points,
            video_info['lane_change_start'],
            video_info['lane_change_end'],
            dst_width=400,
            dst_height=600
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
