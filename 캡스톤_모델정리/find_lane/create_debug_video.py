#!/usr/bin/env python3
"""
차선 검출 디버그 영상 생성기
- 원본, BEV, 차선 마스크, 최종 결과를 함께 표시
- 차선 중심 위치 변화 그래프
"""
import cv2
import numpy as np
from pathlib import Path
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

def load_roi_config(video_name: str, output_dir: Path):
    config_path = output_dir / f"{video_name}_roi_config.json"
    if not config_path.exists():
        return None
    with open(config_path, 'r') as f:
        config = json.load(f)
    return np.float32(config['roi_points'])

def detect_lanes_improved(bev_frame, exclude_bottom_height=100):
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
    
    return (combined > 127).astype(np.uint8), white_mask, yellow_mask, edges

def find_lane_boundaries(lane_mask):
    if lane_mask.sum() == 0:
        return None, None, None
    
    height = lane_mask.shape[0]
    roi_bottom = int(height * 0.8)
    roi_top = int(height * 0.3)
    roi = lane_mask[roi_top:roi_bottom, :]
    
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
    
    lane_centers = []
    for group in lane_groups:
        weights_for_group = column_sums[group]
        if weights_for_group.sum() > 0:
            weighted_center = np.average(group, weights=weights_for_group)
            lane_centers.append(int(weighted_center))
    
    if len(lane_centers) == 0:
        return None, None, None
    
    left_lane_x = min(lane_centers) if len(lane_centers) > 0 else None
    right_lane_x = max(lane_centers) if len(lane_centers) > 1 else None
    
    if left_lane_x is not None and right_lane_x is not None:
        lane_center_x = int((left_lane_x + right_lane_x) / 2)
    else:
        lane_center_x = None
    
    return left_lane_x, right_lane_x, lane_center_x

def create_debug_composite(original, bev, white_mask, yellow_mask, edges, lane_mask, 
                          left_x, right_x, center_x, current_time, center_history):
    """4개 패널 + 그래프를 합친 디버그 영상"""
    # 각 이미지를 작은 크기로 조정
    h, w = 300, 400
    
    # 1. 원본 (BEV)
    panel1 = cv2.resize(bev, (w, h))
    cv2.putText(panel1, "1. BEV Transform", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 2. 흰색 차선 마스크
    panel2 = cv2.cvtColor(white_mask, cv2.COLOR_GRAY2BGR)
    panel2 = cv2.resize(panel2, (w, h))
    cv2.putText(panel2, "2. White Lanes", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 3. 노란색 차선 마스크
    panel3 = cv2.cvtColor(yellow_mask, cv2.COLOR_GRAY2BGR)
    panel3 = cv2.resize(panel3, (w, h))
    cv2.putText(panel3, "3. Yellow Lanes", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 4. Edge 검출
    panel4 = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    panel4 = cv2.resize(panel4, (w, h))
    cv2.putText(panel4, "4. Edge Detection", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 5. 최종 마스크
    panel5 = cv2.cvtColor(lane_mask * 255, cv2.COLOR_GRAY2BGR)
    panel5 = cv2.resize(panel5, (w, h))
    cv2.putText(panel5, "5. Combined Mask", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 6. 차선 검출 결과
    panel6 = cv2.resize(bev, (w, h))
    if left_x is not None:
        left_x_scaled = int(left_x * w / 400)
        cv2.line(panel6, (left_x_scaled, 0), (left_x_scaled, h), (255, 0, 0), 3)
    if right_x is not None:
        right_x_scaled = int(right_x * w / 400)
        cv2.line(panel6, (right_x_scaled, 0), (right_x_scaled, h), (255, 0, 0), 3)
    if center_x is not None:
        center_x_scaled = int(center_x * w / 400)
        cv2.line(panel6, (center_x_scaled, 0), (center_x_scaled, h), (0, 255, 0), 3)
    cv2.putText(panel6, "6. Lane Detection", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 왼쪽: 4개 패널 (2x2)
    top_row = np.hstack([panel1, panel2])
    mid_row = np.hstack([panel3, panel4])
    bottom_row = np.hstack([panel5, panel6])
    left_side = np.vstack([top_row, mid_row, bottom_row])
    
    # 오른쪽: 그래프 (차선 중심 변화)
    fig = plt.figure(figsize=(8, 9))
    ax = fig.add_subplot(111)
    
    if len(center_history) > 0:
        times, centers = zip(*center_history)
        ax.plot(times, centers, 'g-', linewidth=2, label='Lane Center')
        ax.axhline(y=200, color='r', linestyle='--', alpha=0.5, label='Target Center')
        ax.scatter([current_time], [center_x if center_x else 200], 
                  c='red', s=100, zorder=5, label='Current')
    
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Lane Center Position (px)', fontsize=12)
    ax.set_title('Lane Center Tracking', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_ylim([0, 400])
    
    # 그래프를 이미지로 변환
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    buf = canvas.buffer_rgba()
    graph_image = np.asarray(buf)
    graph_image = cv2.cvtColor(graph_image, cv2.COLOR_RGBA2BGR)
    plt.close(fig)
    
    # 그래프를 왼쪽과 같은 높이로 조정
    graph_image = cv2.resize(graph_image, (800, h * 3))
    
    # 최종 합성
    composite = np.hstack([left_side, graph_image])
    
    # 상단에 정보 추가
    info = np.zeros((80, composite.shape[1], 3), dtype=np.uint8)
    cv2.putText(info, f"Time: {current_time:.2f}s", (20, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    if left_x is not None and right_x is not None:
        lane_width = right_x - left_x
        cv2.putText(info, f"Lane Width: {lane_width}px", (20, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    
    if center_x is not None:
        cv2.putText(info, f"Center: {center_x}px", (300, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1)
    
    final = np.vstack([info, composite])
    
    return final

def process_debug_video(video_path: Path, output_path: Path, src_points: np.ndarray):
    print(f"\n🎥 Creating debug video: {video_path.name}")
    
    dst_points = np.float32([[0, 0], [400, 0], [400, 600], [0, 600]])
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 첫 프레임으로 출력 크기 결정
    ret, first_frame = cap.read()
    if not ret:
        raise RuntimeError("Cannot read first frame")
    
    bev_frame = cv2.warpPerspective(first_frame, M, (400, 600))
    lane_mask, white, yellow, edges = detect_lanes_improved(bev_frame, 100)
    left_x, right_x, center_x = find_lane_boundaries(lane_mask)
    debug_frame = create_debug_composite(first_frame, bev_frame, white, yellow, edges,
                                         lane_mask, left_x, right_x, center_x, 0, [])
    
    out_height, out_width = debug_frame.shape[:2]
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 처음으로 되돌림
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (out_width, out_height))
    
    frame_count = 0
    center_history = []
    
    print(f"Output size: {out_width}x{out_height}")
    print(f"Processing {total_frames} frames...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_count / fps
        
        # BEV 변환
        bev_frame = cv2.warpPerspective(frame, M, (400, 600))
        
        # 차선 검출
        lane_mask, white, yellow, edges = detect_lanes_improved(bev_frame, 100)
        left_x, right_x, center_x = find_lane_boundaries(lane_mask)
        
        # 이력 기록
        if center_x is not None:
            center_history.append((current_time, center_x))
            # 최근 150프레임만 유지 (5초)
            if len(center_history) > 150:
                center_history = center_history[-150:]
        
        # 디버그 합성 이미지 생성
        debug_frame = create_debug_composite(
            frame, bev_frame, white, yellow, edges, lane_mask,
            left_x, right_x, center_x, current_time, center_history
        )
        
        writer.write(debug_frame)
        
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"  Frame {frame_count}/{total_frames} ({current_time:.1f}s)")
    
    cap.release()
    writer.release()
    
    print(f"✅ Debug video saved: {output_path}")

def main():
    print("="*70)
    print(" 차선 검출 디버그 영상 생성")
    print("="*70)
    
    data_dir = Path(__file__).resolve().parent.parent / "Data"
    output_dir = Path(__file__).resolve().parent
    
    videos = [
        {"path": data_dir / "이벤트 4.mp4", "name": "이벤트 4"},
        {"path": data_dir / "이벤트 5.mp4", "name": "이벤트 5"}
    ]
    
    for video_info in videos:
        print(f"\n{'='*70}")
        print(f"🎬 {video_info['name']}")
        print(f"{'='*70}")
        
        roi_points = load_roi_config(video_info['name'], output_dir)
        if roi_points is None:
            print(f"❌ ROI config not found")
            continue
        
        output_path = output_dir / f"{video_info['name']}_debug.mp4"
        
        try:
            process_debug_video(video_info['path'], output_path, roi_points)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("✅ 디버그 영상 생성 완료!")
    print("="*70)
    print("\n생성된 파일:")
    print("  - 이벤트 4_debug.mp4")
    print("  - 이벤트 5_debug.mp4")
    print("\n각 영상은 6개 패널 + 차선 중심 그래프를 포함합니다:")
    print("  1. BEV Transform")
    print("  2. White Lanes")
    print("  3. Yellow Lanes")
    print("  4. Edge Detection")
    print("  5. Combined Mask")
    print("  6. Lane Detection Result")
    print("  + Lane Center Tracking Graph")

if __name__ == "__main__":
    main()
