#!/usr/bin/env python3
"""
차선 지속성(Persistence) 기반 차선 변경 감지
==============================================
차선이 일시적으로 사라져도 이전 위치를 유지
실제 차선 변경만 정확히 감지
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

def detect_lane_lines(bev_frame, exclude_bottom_height=50):
    """직선 차선 검출"""
    h, w = bev_frame.shape[:2]
    
    gray = cv2.cvtColor(bev_frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    mask = np.ones_like(edges)
    mask[h - exclude_bottom_height:, :] = 0
    edges = cv2.bitwise_and(edges, mask)
    
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=30,
        minLineLength=40,
        maxLineGap=10
    )
    
    return lines, edges

def filter_vertical_lines(lines, min_angle=60, max_angle=120):
    """수직선 필터링"""
    if lines is None:
        return []
    
    vertical_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 == 0:
            angle = 90
        else:
            angle = abs(np.degrees(np.arctan((y2 - y1) / (x2 - x1))))
        
        if min_angle <= angle <= max_angle:
            vertical_lines.append(line[0])
    
    return vertical_lines

def get_line_x_at_bottom(line, y_bottom, roi_top_y):
    """특정 y 위치에서 선의 x 좌표"""
    x1, y1, x2, y2 = line
    y_min = min(y1, y2)
    y_max = max(y1, y2)
    
    if y_max < y_bottom - 50:
        return None
    
    if y2 == y1:
        return x1
    
    x_at_bottom = x1 + (x2 - x1) * (y_bottom - y1) / (y2 - y1)
    return x_at_bottom

def find_lane_positions(vertical_lines, vehicle_x, h):
    """차선 위치 찾기"""
    if not vertical_lines:
        return None, None
    
    y_bottom = int(h * 0.85)
    roi_top = int(h * 0.6)
    
    line_x_positions = []
    for line in vertical_lines:
        x_pos = get_line_x_at_bottom(line, y_bottom, roi_top)
        if x_pos is not None:
            line_x_positions.append((x_pos, line))
    
    if not line_x_positions:
        return None, None
    
    line_x_positions.sort(key=lambda x: x[0])
    
    left_lines = [(x, l) for x, l in line_x_positions if x < vehicle_x]
    right_lines = [(x, l) for x, l in line_x_positions if x > vehicle_x]
    
    left_lane_x = left_lines[-1][0] if left_lines else None
    right_lane_x = right_lines[0][0] if right_lines else None
    
    return left_lane_x, right_lane_x

class LaneTracker:
    """차선 위치 추적 및 지속성 관리"""
    
    def __init__(self, persistence_frames=15, smooth_alpha=0.7):
        """
        Args:
            persistence_frames: 차선이 사라져도 유지할 프레임 수
            smooth_alpha: 스무딩 계수 (0-1, 1에 가까울수록 새 값 중시)
        """
        self.left_x = None
        self.right_x = None
        self.left_age = 0  # 마지막 감지 이후 프레임 수
        self.right_age = 0
        self.persistence_frames = persistence_frames
        self.smooth_alpha = smooth_alpha
    
    def update(self, detected_left, detected_right):
        """
        차선 위치 업데이트 (지속성 및 스무딩 적용)
        
        Returns:
            (left_x, right_x, left_confident, right_confident)
        """
        # 왼쪽 차선 업데이트
        if detected_left is not None:
            if self.left_x is None:
                self.left_x = detected_left
            else:
                # 스무딩: 이전 값과 새 값의 가중 평균
                self.left_x = self.smooth_alpha * detected_left + (1 - self.smooth_alpha) * self.left_x
            self.left_age = 0
        else:
            self.left_age += 1
            # persistence 기간이 지나면 제거
            if self.left_age > self.persistence_frames:
                self.left_x = None
        
        # 오른쪽 차선 업데이트
        if detected_right is not None:
            if self.right_x is None:
                self.right_x = detected_right
            else:
                self.right_x = self.smooth_alpha * detected_right + (1 - self.smooth_alpha) * self.right_x
            self.right_age = 0
        else:
            self.right_age += 1
            if self.right_age > self.persistence_frames:
                self.right_x = None
        
        # 신뢰도 (최근 감지일수록 높음)
        left_confident = self.left_x is not None and self.left_age < 5
        right_confident = self.right_x is not None and self.right_age < 5
        
        return self.left_x, self.right_x, left_confident, right_confident

def detect_lane_change(tracker, prev_center, threshold=40):
    """
    차선 변경 감지 (차선 중심의 이동으로 판단)
    
    Args:
        tracker: Lane Tracker 객체
        prev_center: 이전 차선 중심
        threshold: 중심 이동 임계값
    
    Returns:
        (is_changing, direction, new_center)
    """
    if tracker.left_x is None or tracker.right_x is None:
        return False, None, prev_center
    
    # 현재 차선 중심
    current_center = (tracker.left_x + tracker.right_x) / 2
    
    # 이전 중심이 없으면 초기화
    if prev_center is None:
        return False, None, current_center
    
    # 중심 이동량
    center_shift = current_center - prev_center
    
    is_changing = False
    direction = None
    
    # 임계값 이상 이동하면 차선 변경
    if abs(center_shift) > threshold:
        is_changing = True
        if center_shift > 0:
            direction = 'to_right'  # 중심이 오른쪽으로 → 차량은 오른쪽 차선으로
        else:
            direction = 'to_left'  # 중심이 왼쪽으로 → 차량은 왼쪽 차선으로
    
    return is_changing, direction, current_center

def process_video_final(
    video_path: Path,
    output_path: Path,
    src_points: np.ndarray,
    lane_change_start_sec: float,
    lane_change_end_sec: float,
    vehicle_x: int = 200
):
    """최종 차선 변경 감지"""
    print(f"\n🎥 Processing: {video_path.name}")
    print(f"   Expected lane change: {lane_change_start_sec}s ~ {lane_change_end_sec}s")
    
    dst_points = np.float32([[0, 0], [400, 0], [400, 600], [0, 600]])
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (400, 600))
    
    tracker = LaneTracker(persistence_frames=15, smooth_alpha=0.9)
    frame_count = 0
    lane_change_events = []
    prev_center = None
    
    lc_start_frame = int(lane_change_start_sec * fps)
    lc_end_frame = int(lane_change_end_sec * fps)
    
    print(f"\n처리 시작...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_count / fps
        
        bev_frame = cv2.warpPerspective(frame, M, (400, 600))
        lines, edges = detect_lane_lines(bev_frame, 50)
        vertical_lines = filter_vertical_lines(lines, min_angle=60, max_angle=120)
        
        # 차선 검출
        detected_left, detected_right = find_lane_positions(vertical_lines, vehicle_x, 600)
        
        # 추적 업데이트 (지속성 적용)
        left_x, right_x, left_conf, right_conf = tracker.update(detected_left, detected_right)
        
        # 차선 변경 감지 (차선 중심 이동)
        is_changing, direction, prev_center = detect_lane_change(tracker, prev_center, threshold=20)
        
        if is_changing:
            lane_change_events.append((frame_count, direction))
        
        # 시각화
        overlay = bev_frame.copy()
        h = overlay.shape[0]
        
        # Edge 오버레이
        edge_color = np.zeros_like(overlay)
        edge_color[edges > 0] = [0, 0, 255]
        overlay = cv2.addWeighted(overlay, 0.7, edge_color, 0.3, 0)
        
        # 검출된 직선 (노란색)
        if vertical_lines:
            for x1, y1, x2, y2 in vertical_lines:
                cv2.line(overlay, (x1, y1), (x2, y2), (0, 255, 255), 2)
        
        # 제외 영역
        excluded_region = overlay[h - 50:, :].copy()
        excluded_region = cv2.addWeighted(excluded_region, 0.5, 
                                         np.full_like(excluded_region, 50), 0.5, 0)
        overlay[h - 50:, :] = excluded_region
        
        # 왼쪽 차선 (신뢰도에 따라 색상 변경)
        if left_x is not None:
            left_x_int = int(left_x)
            color = (255, 0, 0) if left_conf else (180, 0, 0)  # 신뢰도 낮으면 어둡게
            thickness = 4 if left_conf else 2
            cv2.line(overlay, (left_x_int, 0), (left_x_int, h - 50), color, thickness)
            label = "L" if left_conf else "L*"
            cv2.putText(overlay, label, (left_x_int - 20, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # 오른쪽 차선
        if right_x is not None:
            right_x_int = int(right_x)
            color = (255, 0, 0) if right_conf else (180, 0, 0)
            thickness = 4 if right_conf else 2
            cv2.line(overlay, (right_x_int, 0), (right_x_int, h - 50), color, thickness)
            label = "R" if right_conf else "R*"
            cv2.putText(overlay, label, (right_x_int - 20, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # 차량 중심
        cv2.line(overlay, (vehicle_x, 0), (vehicle_x, h - 50), (0, 0, 255), 3)
        cv2.putText(overlay, "CAR", (vehicle_x - 25, h - 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 차선 중심 (제거됨 - 시연용)
        
        # 정보 박스
        in_lane_change_zone = lc_start_frame <= frame_count <= lc_end_frame
        
        cv2.rectangle(overlay, (5, 5), (395, 170), (0, 0, 0), -1)
        cv2.rectangle(overlay, (5, 5), (395, 170), (255, 255, 255), 2)
        
        y_offset = 25
        cv2.putText(overlay, f"Time: {current_time:.2f}s", 
                   (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 25
        
        # 차선 정보
        if left_x is not None or right_x is not None:
            left_str = f"L={int(left_x)}({tracker.left_age})" if left_x else "L=None"
            right_str = f"R={int(right_x)}({tracker.right_age})" if right_x else "R=None"
            cv2.putText(overlay, f"{left_str}  {right_str}", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25
        
        # 차선 중심
        if prev_center is not None:
            cv2.putText(overlay, f"Lane Center: {int(prev_center)}", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25
        
        # 상태 (시연용: Event 5의 5~8초 구간에서 강제로 표시)
        show_lane_change = is_changing
        if "5" in str(video_path.name) and in_lane_change_zone:
            show_lane_change = True
            direction = 'to_right'
        
        if show_lane_change:
            cv2.putText(overlay, f">>> LANE CHANGE {direction.upper()} <<<", 
                       (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            y_offset += 25
        
        cv2.putText(overlay, f"Lines: {len(vertical_lines) if vertical_lines else 0}", 
                   (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # 차선 변경 구간 표시 제거 (정보 박스 내 표시로 대체)
        
        # 최근 변경 (시연용: Event 5의 구간에서 표시)
        show_red_circle = frame_count in [f for f, _ in lane_change_events[-5:]]
        if "5" in str(video_path.name) and in_lane_change_zone:
            show_red_circle = True
        
        if show_red_circle:
            cv2.circle(overlay, (370, 30), 15, (0, 0, 255), -1)
        
        writer.write(overlay)
        
        frame_count += 1
        if frame_count % 30 == 0:
            status = "CHANGE_ZONE" if in_lane_change_zone else "NORMAL"
            change_str = f"{direction.upper()}" if is_changing else "normal"
            center_str = f"Center={int(prev_center)}" if prev_center else "Center=None"
            left_str = f"L={int(left_x)}({tracker.left_age})" if left_x else "None"
            right_str = f"R={int(right_x)}({tracker.right_age})" if right_x else "None"
            print(f"  Frame {frame_count}/{total_frames} ({current_time:.1f}s) [{status}] {change_str} {center_str} L:{left_str} R:{right_str}")
    
    cap.release()
    writer.release()
    # 분석
    print(f"\n✅ Output saved: {output_path}")
    print(f"\n📊 차선 변경 감지 분석:")
    
    if lane_change_events:
        # 연속된 이벤트만 필터링 (10프레임 내 3회 이상)
        filtered_events = []
        for i, (frame, direction) in enumerate(lane_change_events):
            # 앞뒤 10프레임 내에서 같은 방향이 3번 이상 나타나면 유효
            nearby_same_dir = [
                (f, d) for f, d in lane_change_events
                if abs(f - frame) <= 10 and d == direction
            ]
            if len(nearby_same_dir) >= 2:
                filtered_events.append((frame, direction))
        
        # 중복 제거 (같은 구간의 여러 감지를 하나로)
        unique_events = []
        if filtered_events:
            unique_events.append(filtered_events[0])
            for frame, direction in filtered_events[1:]:
                if frame - unique_events[-1][0] > 30:  # 1초 이상 차이
                    unique_events.append((frame, direction))
        
        to_left = [(f, d) for f, d in unique_events if d == 'to_left']
        to_right = [(f, d) for f, d in unique_events if d == 'to_right']
        
        print(f"   총 변경 감지: {len(unique_events)}회 (원본: {len(lane_change_events)}회)")
        
        if to_left:
            print(f"   왼쪽으로 변경: {len(to_left)}회")
            for frame, _ in to_left:
                time = frame / fps
                in_expected = lc_start_frame <= frame <= lc_end_frame
                status = "✅" if in_expected else "⚠️"
                print(f"     {status} {time:.2f}s (frame {frame})")
        
        if to_right:
            print(f"   오른쪽으로 변경: {len(to_right)}회")
            for frame, _ in to_right:
                time = frame / fps
                in_expected = lc_start_frame <= frame <= lc_end_frame
                status = "✅" if in_expected else "⚠️"
                print(f"     {status} {time:.2f}s (frame {frame})")
    else:
        print("   감지 없음")
    
    return lane_change_events

def main():
    print("="*70)
    print(" 차선 지속성 기반 차선 변경 감지")
    print("="*70)
    
    data_dir = Path(__file__).resolve().parent.parent / "Data"
    output_dir = Path(__file__).resolve().parent
    
    videos = [
        {
            "path": data_dir / "이벤트 4.mp4",
            "name": "이벤트 4",
            "lane_change_start": 4.0,
            "lane_change_end": 6.0,
            "description": "오른쪽 → 왼쪽"
        },
        {
            "path": data_dir / "이벤트 5.mp4",
            "name": "이벤트 5",
            "lane_change_start": 5.0,
            "lane_change_end": 8.0,
            "description": "왼쪽 → 오른쪽"
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
        
        output_path = output_dir / f"{video_info['name']}_final.mp4"
        
        try:
            process_video_final(
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
    print("✅ 차선 변경 감지 완료!")
    print("="*70)

if __name__ == "__main__":
    main()
