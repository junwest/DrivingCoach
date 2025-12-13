#!/usr/bin/env python3
"""
개선된 Edge 기반 차선 변경 감지
================================
하단 중앙의 edge 위치 추적 및 이동 방향 감지
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

def detect_edges(bev_frame, exclude_bottom_height=100):
    """Edge 검출"""
    h, w = bev_frame.shape[:2]
    
    gray = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    # 하단 마스킹
    mask = np.ones_like(edges)
    mask[h - exclude_bottom_height:, :] = 0
    edges = cv2.bitwise_and(edges, mask)
    
    return edges

def find_bottom_edge_position(edges, bottom_roi_height=120, exclude_bottom=100):
    """
    하단 중앙의 edge 위치 찾기
    
    Returns:
        edge_x: Edge의 x 좌표 (없으면 None)
        edge_strength: Edge 강도
    """
    h, w = edges.shape
    
    # 하단 ROI 설정 (핸들 바로 위)
    roi_y_start = h - exclude_bottom - bottom_roi_height
    roi_y_end = h - exclude_bottom
    
    # 중앙 부근만 체크 (전체 폭의 20-80%)
    roi_x_start = int(w * 0.2)
    roi_x_end = int(w * 0.8)
    
    roi = edges[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
    
    if roi.sum() == 0:
        return None, 0.0
    
    # 각 열의 edge 픽셀 수
    column_sums = roi.sum(axis=0)
    
    # Edge가 가장 강한 위치 찾기
    if column_sums.max() == 0:
        return None, 0.0
    
    # 상위 20% 이상의 edge만 고려
    threshold = column_sums.max() * 0.2
    significant_columns = np.where(column_sums > threshold)[0]
    
    if len(significant_columns) == 0:
        return None, 0.0
    
    # 가중 평균으로 edge 중심 계산
    weights = column_sums[significant_columns]
    edge_x_relative = np.average(significant_columns, weights=weights)
    
    # 실제 x 좌표로 변환
    edge_x = roi_x_start + int(edge_x_relative)
    
    # Edge 강도 (0-1)
    edge_strength = column_sums.max() / (roi.shape[0] * 255)
    
    return edge_x, edge_strength

def detect_lane_change_from_edge_movement(edge_position_history, min_movement=40):
    """
    Edge 위치 이력으로 차선 변경 감지
    
    Args:
        edge_position_history: [(frame, x_position), ...]
        min_movement: 최소 이동 거리 (픽셀)
    
    Returns:
        (is_changing, direction)
        direction: 'left_to_right', 'right_to_left', None
    """
    if len(edge_position_history) < 10:
        return False, None
    
    # 최근 30프레임 (약 1초)
    recent = edge_position_history[-30:]
    
    # 필터링: None 제거
    valid_positions = [(f, x) for f, x in recent if x is not None]
    
    if len(valid_positions) < 5:
        return False, None
    
    # 시작과 끝 위치
    start_positions = [x for _, x in valid_positions[:5]]
    end_positions = [x for _, x in valid_positions[-5:]]
    
    start_avg = np.mean(start_positions)
    end_avg = np.mean(end_positions)
    
    movement = end_avg - start_avg
    
    # 이동이 충분히 큰지 확인
    if abs(movement) > min_movement:
        if movement > 0:
            return True, 'left_to_right'  # 왼쪽에서 오른쪽으로
        else:
            return True, 'right_to_left'  # 오른쪽에서 왼쪽으로
    
    return False, None

def process_video_with_edge_tracking(
    video_path: Path,
    output_path: Path,
    src_points: np.ndarray,
    lane_change_start_sec: float,
    lane_change_end_sec: float
):
    """Edge 위치 추적 기반 차선 변경 감지"""
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
    edge_position_history = []
    lane_change_events = []
    
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
        edges = detect_edges(bev_frame, 100)
        
        # 하단 edge 위치 찾기
        edge_x, edge_strength = find_bottom_edge_position(edges, bottom_roi_height=120, exclude_bottom=100)
        
        # 이력 저장
        edge_position_history.append((frame_count, edge_x))
        if len(edge_position_history) > 150:
            edge_position_history = edge_position_history[-150:]
        
        # 차선 변경 감지
        is_changing, direction = detect_lane_change_from_edge_movement(edge_position_history, min_movement=40)
        
        if is_changing:
            lane_change_events.append((frame_count, direction))
        
        # 시각화
        # 좌측: BEV + Edge
        left_panel = bev_frame.copy()
        edge_color = np.zeros_like(left_panel)
        edge_color[edges > 0] = [0, 0, 255]
        left_panel = cv2.addWeighted(left_panel, 0.7, edge_color, 0.3, 0)
        
        # 하단 ROI 표시
        h, w = left_panel.shape[:2]
        roi_y_start = h - 100 - 120
        roi_y_end = h - 100
        roi_x_start = int(w * 0.2)
        roi_x_end = int(w * 0.8)
        
        cv2.rectangle(left_panel, (roi_x_start, roi_y_start), (roi_x_end, roi_y_end), (0, 255, 0), 2)
        
        # Edge 위치 표시
        if edge_x is not None:
            cv2.circle(left_panel, (edge_x, (roi_y_start + roi_y_end) // 2), 8, (255, 0, 255), -1)
            cv2.line(left_panel, (edge_x, roi_y_start), (edge_x, roi_y_end), (255, 0, 255), 2)
        
        # 우측: Edge만
        right_panel = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(right_panel, (roi_x_start, roi_y_start), (roi_x_end, roi_y_end), (0, 255, 0), 2)
        
        if edge_x is not None:
            cv2.circle(right_panel, (edge_x, (roi_y_start + roi_y_end) // 2), 8, (255, 0, 255), -1)
        
        # 합성
        combined = np.hstack([left_panel, right_panel])
        
        # 정보 박스
        in_lane_change_zone = lc_start_frame <= frame_count <= lc_end_frame
        
        cv2.rectangle(combined, (5, 5), (795, 150), (0, 0, 0), -1)
        cv2.rectangle(combined, (5, 5), (795, 150), (255, 255, 255), 2)
        
        y_offset = 30
        cv2.putText(combined, f"Time: {current_time:.2f}s", 
                   (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 30
        
        # Edge 위치
        if edge_x is not None:
            cv2.putText(combined, f"Edge X: {edge_x}px  Strength: {edge_strength:.3f}", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        else:
            cv2.putText(combined, "Edge: Not detected", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)
        y_offset += 30
        
        # 차선 변경 상태
        if is_changing:
            direction_text = "LEFT→RIGHT" if direction == 'left_to_right' else "RIGHT→LEFT"
            cv2.putText(combined, f">>> {direction_text} <<<", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # 예상 구간
        if in_lane_change_zone:
            cv2.rectangle(combined, (10, 550), (790, 590), (0, 165, 255), -1)
            cv2.putText(combined, "Expected Lane Change Zone", 
                       (200, 575), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 최근 감지
        if frame_count in [f for f, _ in lane_change_events[-10:]]:
            cv2.circle(combined, (750, 50), 20, (0, 0, 255), -1)
            cv2.putText(combined, "DETECTED", 
                       (620, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        writer.write(combined)
        
        frame_count += 1
        if frame_count % 30 == 0:
            status = "CHANGE_ZONE" if in_lane_change_zone else "NORMAL"
            edge_str = f"x={edge_x}" if edge_x else "none"
            change_str = direction if is_changing else "normal"
            print(f"  Frame {frame_count}/{total_frames} ({current_time:.1f}s) [{status}] edge:{edge_str} {change_str}")
    
    cap.release()
    writer.release()
    
    # 분석
    print(f"\n✅ Output saved: {output_path}")
    print(f"\n📊 차선 변경 감지 분석:")
    
    if lane_change_events:
        # 연속된 이벤트 그룹핑
        groups = []
        current_group = {'start': lane_change_events[0][0], 'end': lane_change_events[0][0], 'direction': lane_change_events[0][1]}
        
        for i in range(1, len(lane_change_events)):
            frame, direction = lane_change_events[i]
            if frame - lane_change_events[i-1][0] <= 5 and direction == current_group['direction']:
                current_group['end'] = frame
            else:
                groups.append(current_group)
                current_group = {'start': frame, 'end': frame, 'direction': direction}
        
        groups.append(current_group)
        
        print(f"   감지된 차선 변경: {len(groups)}회")
        for i, group in enumerate(groups):
            start_time = group['start'] / fps
            end_time = group['end'] / fps
            dir_text = "왼쪽→오른쪽" if group['direction'] == 'left_to_right' else "오른쪽→왼쪽"
            in_expected = lc_start_frame <= group['start'] <= lc_end_frame
            status = "✅ 예상 구간" if in_expected else "⚠️ 예상 외"
            duration = group['end'] - group['start'] + 1
            print(f"     {i+1}. {start_time:.2f}s~{end_time:.2f}s ({duration}f) {dir_text} {status}")
    else:
        print("   감지 없음")
    
    return lane_change_events

def main():
    print("="*70)
    print(" 개선된 Edge 기반 차선 변경 감지 (위치 추적)")
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
        
        output_path = output_dir / f"{video_info['name']}_edge_tracking.mp4"
        
        try:
            process_video_with_edge_tracking(
                video_info['path'],
                output_path,
                roi_points,
                video_info['lane_change_start'],
                video_info['lane_change_end']
            )
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("✅ Edge 추적 기반 차선 변경 감지 완료!")
    print("="*70)

if __name__ == "__main__":
    main()
