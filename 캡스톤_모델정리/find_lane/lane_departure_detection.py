#!/usr/bin/env python3
"""
차선 이탈 감지 (차량 중심 기준)
================================
차량 중심 대비 가장 가까운 좌/우 차선을 찾아서
차량이 이 차선을 넘어가면 차선 이탈로 감지
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

def detect_lanes_improved(bev_frame, exclude_bottom_height=50):
    """차선 검출"""
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
    
    # 하단 마스킹
    mask = np.ones_like(combined)
    mask[h - exclude_bottom_height:, :] = 0
    combined = cv2.bitwise_and(combined, mask)
    
    return (combined > 127).astype(np.uint8)

def find_closest_lanes(lane_mask, vehicle_x):
    """
    차량 중심 대비 가장 가까운 왼쪽/오른쪽 차선 찾기
    
    Args:
        lane_mask: 차선 마스크
        vehicle_x: 차량 중심 x 좌표
    
    Returns:
        (left_lane_x, right_lane_x)
        각각 None일 수 있음
    """
    if lane_mask.sum() == 0:
        return None, None
    
    height = lane_mask.shape[0]
    
    # ROI 설정 (주로 하단 - 차선이 가장 명확한 영역)
    roi_bottom = int(height * 0.95)  # 거의 맨 아래까지
    roi_top = int(height * 0.6)  # 중간~아래
    roi = lane_mask[roi_top:roi_bottom, :]
    
    # 가중치 (아래쪽에 더 높은 가중치)
    weights = np.linspace(0.5, 1.0, roi.shape[0])[:, np.newaxis]
    weighted_roi = roi.astype(np.float32) * weights
    column_sums = weighted_roi.sum(axis=0)
    
    # 차선이 있는 열 찾기 (임계값 낮춤)
    lane_threshold = 1  # 더 낮은 임계값
    lane_columns = np.where(column_sums > lane_threshold)[0]
    
    if len(lane_columns) == 0:
        return None, None
    
    # 클러스터링 (더 관대하게)
    lane_groups = []
    current_group = [lane_columns[0]]
    
    for i in range(1, len(lane_columns)):
        if lane_columns[i] - lane_columns[i-1] <= 15:  # 더 큰 gap 허용
            current_group.append(lane_columns[i])
        else:
            if len(current_group) >= 1:  # 최소 1픽셀만 있어도 OK
                lane_groups.append(current_group)
            current_group = [lane_columns[i]]
    
    if len(current_group) >= 1:
        lane_groups.append(current_group)
    
    if len(lane_groups) == 0:
        return None, None
    
    # 각 그룹의 가중 중심
    lane_centers = []
    for group in lane_groups:
        weights_for_group = column_sums[group]
        if weights_for_group.sum() > 0:
            weighted_center = np.average(group, weights=weights_for_group)
            lane_centers.append(int(weighted_center))
    
    if len(lane_centers) == 0:
        return None, None
    
    # 차량 중심 기준으로 가장 가까운 왼쪽/오른쪽 차선 찾기
    left_lanes = [x for x in lane_centers if x < vehicle_x]
    right_lanes = [x for x in lane_centers if x > vehicle_x]
    
    # 가장 가까운 것 선택
    left_lane_x = max(left_lanes) if left_lanes else None  # 차량에 가장 가까운 왼쪽
    right_lane_x = min(right_lanes) if right_lanes else None  # 차량에 가장 가까운 오른쪽
    
    return left_lane_x, right_lane_x

def detect_lane_departure(vehicle_x, left_lane_x, right_lane_x, prev_state):
    """
    차선 이탈 감지
    
    Args:
        vehicle_x: 차량 중심
        left_lane_x: 왼쪽 차선 위치
        right_lane_x: 오른쪽 차선 위치
        prev_state: 이전 상태 ('normal', 'crossing_left', 'crossing_right')
    
    Returns:
        (is_departing, direction, new_state)
        direction: 'left' (왼쪽 차선 넘음), 'right' (오른쪽 차선 넘음), None
    """
    if left_lane_x is None or right_lane_x is None:
        return False, None, prev_state
    
    # 차량이 왼쪽 차선을 넘었는지 확인
    crossing_left = vehicle_x <= left_lane_x
    
    # 차량이 오른쪽 차선을 넘었는지 확인  
    crossing_right = vehicle_x >= right_lane_x
    
    # 상태 변화 감지
    is_departing = False
    direction = None
    new_state = 'normal'
    
    if crossing_left and prev_state != 'crossing_left':
        # 왼쪽 차선을 새로 넘음
        is_departing = True
        direction = 'left'
        new_state = 'crossing_left'
    elif crossing_right and prev_state != 'crossing_right':
        # 오른쪽 차선을 새로 넘음
        is_departing = True
        direction = 'right'
        new_state = 'crossing_right'
    elif crossing_left:
        new_state = 'crossing_left'
    elif crossing_right:
        new_state = 'crossing_right'
    else:
        new_state = 'normal'
    
    return is_departing, direction, new_state

def process_video_with_lane_departure(
    video_path: Path,
    output_path: Path,
    src_points: np.ndarray,
    lane_change_start_sec: float,
    lane_change_end_sec: float,
    vehicle_x: int = 200
):
    """차선 이탈 감지"""
    print(f"\n🎥 Processing: {video_path.name}")
    print(f"   Expected lane change: {lane_change_start_sec}s ~ {lane_change_end_sec}s")
    print(f"   Vehicle center: {vehicle_x}px")
    
    # BEV 변환
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
    departure_events = []
    prev_state = 'normal'
    
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
        
        # 차선 검출
        lane_mask = detect_lanes_improved(bev_frame, 50)
        
        # 가장 가까운 왼쪽/오른쪽 차선 찾기
        left_x, right_x = find_closest_lanes(lane_mask, vehicle_x)
        
        # 차선 이탈 감지
        is_departing, direction, prev_state = detect_lane_departure(
            vehicle_x, left_x, right_x, prev_state
        )
        
        if is_departing:
            departure_events.append((frame_count, direction))
        
        # 시각화
        overlay = bev_frame.copy()
        
        # 차선 마스크 오버레이
        lane_mask_color = np.zeros_like(overlay)
        lane_mask_color[lane_mask > 0] = [255, 255, 255]
        overlay = cv2.addWeighted(overlay, 0.6, lane_mask_color, 0.4, 0)
        
        h = overlay.shape[0]
        
        # 제외 영역 표시
        excluded_region = overlay[h - 50:, :].copy()
        excluded_region = cv2.addWeighted(excluded_region, 0.5, 
                                         np.full_like(excluded_region, 50), 0.5, 0)
        overlay[h - 50:, :] = excluded_region
        
        # 왼쪽 차선 그리기 (파란색)
        if left_x is not None:
            cv2.line(overlay, (left_x, 0), (left_x, h - 50), (255, 0, 0), 4)
            cv2.putText(overlay, "L", (left_x - 20, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # 오른쪽 차선 그리기 (파란색)
        if right_x is not None:
            cv2.line(overlay, (right_x, 0), (right_x, h - 50), (255, 0, 0), 4)
            cv2.putText(overlay, "R", (right_x - 20, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # 차량 중심선 (빨간색)
        cv2.line(overlay, (vehicle_x, 0), (vehicle_x, h - 50), (0, 0, 255), 3)
        cv2.putText(overlay, "CAR", (vehicle_x - 25, h - 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 차선 중심 (초록색)
        if left_x is not None and right_x is not None:
            center_x = int((left_x + right_x) / 2)
            cv2.line(overlay, (center_x, 0), (center_x, h - 50), (0, 255, 0), 2)
        
        # 정보 박스
        in_lane_change_zone = lc_start_frame <= frame_count <= lc_end_frame
        
        cv2.rectangle(overlay, (5, 5), (395, 150), (0, 0, 0), -1)
        cv2.rectangle(overlay, (5, 5), (395, 150), (255, 255, 255), 2)
        
        y_offset = 25
        cv2.putText(overlay, f"Time: {current_time:.2f}s", 
                   (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 25
        
        # 차선 위치
        if left_x is not None and right_x is not None:
            lane_width = right_x - left_x
            offset = vehicle_x - (left_x + right_x) / 2
            cv2.putText(overlay, f"Width: {lane_width}px  Offset: {offset:+.0f}px", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25
        
        # 상태 표시
        state_text = prev_state.replace('_', ' ').title()
        state_color = (0, 255, 0) if prev_state == 'normal' else (0, 165, 255)
        cv2.putText(overlay, f"State: {state_text}", 
                   (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, state_color, 1)
        y_offset += 25
        
        # 차선 이탈 표시
        if is_departing:
            direction_text = "LEFT" if direction == 'left' else "RIGHT"
            cv2.putText(overlay, f">>> CROSSING {direction_text} LANE <<<", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 예상 구간 표시
        if in_lane_change_zone:
            cv2.rectangle(overlay, (10, h - 50), (390, h - 110), (0, 165, 255), -1)
            cv2.putText(overlay, "Expected Zone", 
                       (100, h - 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 최근 이탈 표시
        if frame_count in [f for f, _ in departure_events[-5:]]:
            cv2.circle(overlay, (370, 30), 15, (0, 0, 255), -1)
        
        writer.write(overlay)
        
        frame_count += 1
        if frame_count % 30 == 0:
            status = "CHANGE_ZONE" if in_lane_change_zone else "NORMAL"
            depart_str = f"CROSSING_{direction.upper()}" if is_departing else prev_state
            left_str = f"L={left_x}" if left_x is not None else "L=None"
            right_str = f"R={right_x}" if right_x is not None else "R=None"
            print(f"  Frame {frame_count}/{total_frames} ({current_time:.1f}s) [{status}] {depart_str} ({left_str}, {right_str})")
    
    cap.release()
    writer.release()
    
    # 분석
    print(f"\n✅ Output saved: {output_path}")
    print(f"\n📊 차선 이탈 감지 분석:")
    
    if departure_events:
        # 방향별 그룹핑
        left_departures = [(f, d) for f, d in departure_events if d == 'left']
        right_departures = [(f, d) for f, d in departure_events if d == 'right']
        
        print(f"   왼쪽 차선 이탈: {len(left_departures)}회")
        for frame, _ in left_departures[:5]:  # 최대 5개만 표시
            time = frame / fps
            in_expected = lc_start_frame <= frame <= lc_end_frame
            status = "✅" if in_expected else "⚠️"
            print(f"     {status} {time:.2f}s (frame {frame})")
        
        print(f"   오른쪽 차선 이탈: {len(right_departures)}회")
        for frame, _ in right_departures[:5]:
            time = frame / fps
            in_expected = lc_start_frame <= frame <= lc_end_frame
            status = "✅" if in_expected else "⚠️"
            print(f"     {status} {time:.2f}s (frame {frame})")
    else:
        print("   감지 없음")
    
    return departure_events

def main():
    print("="*70)
    print(" 차선 이탈 감지 (차량 중심 기준)")
    print("="*70)
    
    data_dir = Path(__file__).resolve().parent.parent / "Data"
    output_dir = Path(__file__).resolve().parent
    
    videos = [
        {
            "path": data_dir / "이벤트 4.mp4",
            "name": "이벤트 4",
            "lane_change_start": 4.0,
            "lane_change_end": 6.0,
            "description": "오른쪽 → 왼쪽 (왼쪽 차선 넘음)"
        },
        {
            "path": data_dir / "이벤트 5.mp4",
            "name": "이벤트 5",
            "lane_change_start": 5.0,
            "lane_change_end": 8.0,
            "description": "왼쪽 → 오른쪽 (오른쪽 차선 넘음)"
        }
    ]
    
    for video_info in videos:
        print(f"\n{'='*70}")
        print(f"🎬 {video_info['name']}: {video_info['description']}")
        print(f"{'='*70}")
        
        roi_points = load_roi_config(video_info['name'], output_dir)
        if roi_points is None:
            print(f"❌ ROI config not found")
            continue
        
        output_path = output_dir / f"{video_info['name']}_departure.mp4"
        
        try:
            process_video_with_lane_departure(
                video_info['path'],
                output_path,
                roi_points,
                video_info['lane_change_start'],
                video_info['lane_change_end'],
                vehicle_x=200
            )
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("✅ 차선 이탈 감지 완료!")
    print("="*70)

if __name__ == "__main__":
    main()
