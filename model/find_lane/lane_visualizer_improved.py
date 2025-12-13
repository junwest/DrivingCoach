#!/usr/bin/env python3
"""
차선 검출 시각화 도구 - 개선된 버전
=================================
- 향상된 차선 검출 (HSV + Edge Detection 결합)
- BEV 변환 시각화 개선
- 더 정확한 차선 경계 검출
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np


# BEV Transformation Parameters
H_MATRIX = np.array([
    [-3.97727273e-02, -3.24810606e-01, 1.00492424e02],
    [4.37257068e-16, -2.54829545e00, 7.89971591e02],
    [1.16574774e-18, -3.69318182e-03, 1.00000000e00],
])

# BEV 이미지에서 차량 위치
MY_CAR_BEV_X = 105
MY_CAR_BEV_Y = 400

# Visualization colors (BGR format)
COLOR_LANE_MASK = (255, 255, 255)  # White for detected lanes
COLOR_LEFT_LANE = (255, 0, 0)      # Blue for left lane
COLOR_RIGHT_LANE = (255, 0, 0)     # Blue for right lane
COLOR_VEHICLE_CENTER = (0, 0, 255)  # Red for vehicle center
COLOR_ROI = (0, 255, 255)          # Yellow for ROI


class ImprovedLaneDetector:
    """개선된 차선 검출 클래스 - HSV + Edge Detection 결합"""
    
    def __init__(self, detection_method: str = "combined"):
        """
        Args:
            detection_method: 'hsv', 'edge', 'combined', 'adaptive'
        """
        self.method = detection_method
        
        # HSV 범위 (튜닝된 파라미터)
        self.lower_white = np.array([0, 0, 150])
        self.upper_white = np.array([180, 60, 255])
        self.lower_yellow = np.array([10, 60, 60])
        self.upper_yellow = np.array([40, 255, 255])
        
    def detect_lanes(self, frame: np.ndarray) -> np.ndarray:
        """차선 마스크 검출"""
        if self.method == "hsv":
            return self._detect_hsv(frame)
        elif self.method == "edge":
            return self._detect_edge(frame)
        elif self.method == "combined":
            return self._detect_combined(frame)
        elif self.method == "adaptive":
            return self._detect_adaptive(frame)
        else:
            return self._detect_combined(frame)
    
    def _detect_hsv(self, frame: np.ndarray) -> np.ndarray:
        """HSV 기반 검출"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        white_mask = cv2.inRange(hsv, self.lower_white, self.upper_white)
        yellow_mask = cv2.inRange(hsv, self.lower_yellow, self.upper_yellow)
        
        combined = cv2.bitwise_or(white_mask, yellow_mask)
        
        # Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
        
        return (combined > 127).astype(np.uint8)
    
    def _detect_edge(self, frame: np.ndarray) -> np.ndarray:
        """엣지 기반 검출"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        return (edges > 127).astype(np.uint8)
    
    def _detect_combined(self, frame: np.ndarray) -> np.ndarray:
        """HSV + Edge 결합"""
        hsv_mask = self._detect_hsv(frame)
        edge_mask = self._detect_edge(frame)
        
        combined = cv2.bitwise_or(hsv_mask * 255, edge_mask * 255)
        
        # Morphological operations
        kernel = np.ones((5, 5), np.uint8)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
        
        return (combined > 127).astype(np.uint8)
    
    def _detect_adaptive(self, frame: np.ndarray) -> np.ndarray:
        """적응형 임계값"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return (thresh > 127).astype(np.uint8)


class BEVLaneAnalyzer:
    """BEV 변환 및 차선 분석 클래스"""
    
    def __init__(
        self, 
        lane_detector: ImprovedLaneDetector, 
        bev_size: Tuple[int, int] = (210, 600),
        show_debug: bool = False
    ):
        self.lane_detector = lane_detector
        self.bev_width, self.bev_height = bev_size
        self.show_debug = show_debug
        
    def apply_bev_transform(self, frame: np.ndarray) -> np.ndarray:
        """프레임에 BEV 변환 적용"""
        bev = cv2.warpPerspective(
            frame, 
            H_MATRIX, 
            (self.bev_width, self.bev_height),
            flags=cv2.INTER_LINEAR
        )
        return bev
    
    def find_lane_boundaries(
        self, 
        lane_mask: np.ndarray, 
        vehicle_x: int,
        roi_y_range: Tuple[int, int] = None
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        차량 중심을 기준으로 가장 가까운 왼쪽/오른쪽 차선 경계 찾기
        
        Args:
            lane_mask: 차선 마스크 (이진 이미지)
            vehicle_x: 차량 중심 x 좌표
            roi_y_range: ROI y 범위 (start, end), None이면 기본값 사용
            
        Returns:
            (left_lane_x, right_lane_x) 튜플. 없으면 None
        """
        if lane_mask.sum() == 0:
            return None, None
        
        # 관심 영역(ROI) 설정
        if roi_y_range is None:
            roi_y_start = max(0, MY_CAR_BEV_Y - 250)  # 범위 확대
            roi_y_end = MY_CAR_BEV_Y
        else:
            roi_y_start, roi_y_end = roi_y_range
        
        roi = lane_mask[roi_y_start:roi_y_end, :]
        
        # 각 열의 차선 픽셀 개수를 가중치로 계산 (아래쪽에 더 높은 가중치)
        weights = np.linspace(0.5, 1.0, roi.shape[0])[:, np.newaxis]
        weighted_roi = roi.astype(np.float32) * weights
        column_sums = weighted_roi.sum(axis=0)
        
        # 차선이 있는 열 찾기
        lane_threshold = 3  # 임계값 낮춤
        lane_columns = np.where(column_sums > lane_threshold)[0]
        
        if len(lane_columns) == 0:
            return None, None
        
        # 연속된 차선 영역을 찾기 위해 clustering
        lane_groups = []
        current_group = [lane_columns[0]]
        
        for i in range(1, len(lane_columns)):
            if lane_columns[i] - lane_columns[i-1] <= 8:  # 클러스터링 gap 증가
                current_group.append(lane_columns[i])
            else:
                if len(current_group) >= 2:  # 최소 2픽셀로 완화
                    lane_groups.append(current_group)
                current_group = [lane_columns[i]]
        
        if len(current_group) >= 2:
            lane_groups.append(current_group)
        
        if len(lane_groups) == 0:
            return None, None
        
        # 각 그룹의 가중 중심 계산 (픽셀 강도 고려)
        lane_centers = []
        for group in lane_groups:
            weights_for_group = column_sums[group]
            if weights_for_group.sum() > 0:
                weighted_center = np.average(group, weights=weights_for_group)
                lane_centers.append(int(weighted_center))
        
        if len(lane_centers) == 0:
            return None, None
        
        # 차량 중심 기준으로 왼쪽/오른쪽 차선 찾기
        left_lanes = [x for x in lane_centers if x < vehicle_x]
        right_lanes = [x for x in lane_centers if x > vehicle_x]
        
        # 가장 가까운 왼쪽/오른쪽 차선
        left_lane_x = max(left_lanes) if len(left_lanes) > 0 else None
        right_lane_x = min(right_lanes) if len(right_lanes) > 0 else None
        
        return left_lane_x, right_lane_x
    
    def calculate_lane_metrics(
        self, 
        left_lane_x: Optional[int], 
        right_lane_x: Optional[int], 
        vehicle_x: int,
        pixels_per_meter: float = 20.0
    ) -> Tuple[float, float, bool, bool]:
        """차선 거리 및 이탈률 계산"""
        lane_detected = False
        lane_normal = False
        lane_width_m = 0.0
        departure_rate = 0.0
        
        if left_lane_x is not None and right_lane_x is not None:
            lane_detected = True
            
            lane_width_px = right_lane_x - left_lane_x
            lane_width_m = lane_width_px / pixels_per_meter
            
            lane_center_x = (left_lane_x + right_lane_x) / 2
            offset_px = vehicle_x - lane_center_x
            
            if lane_width_px > 0:
                departure_rate = offset_px / lane_width_px
            
            # 정상 범위 판단 (±35%로 완화)
            lane_normal = abs(departure_rate) < 0.35
        
        elif left_lane_x is not None or right_lane_x is not None:
            lane_detected = True
            lane_normal = False
            
            if left_lane_x is not None:
                offset_px = vehicle_x - left_lane_x
                departure_rate = offset_px / 60.0
            else:
                offset_px = vehicle_x - right_lane_x
                departure_rate = offset_px / 60.0
        
        return lane_width_m, departure_rate, lane_detected, lane_normal
    
    def process_frame(
        self, 
        frame: np.ndarray
    ) -> Tuple[np.ndarray, dict]:
        """프레임 처리 및 시각화 오버레이 생성"""
        # 1. BEV 변환
        bev_frame = self.apply_bev_transform(frame)
        
        # 2. 차선 검출
        lane_mask = self.lane_detector.detect_lanes(bev_frame)
        
        # 3. 차선 경계 찾기
        left_lane_x, right_lane_x = self.find_lane_boundaries(lane_mask, MY_CAR_BEV_X)
        
        # 4. 메트릭 계산
        lane_width_m, departure_rate, lane_detected, lane_normal = self.calculate_lane_metrics(
            left_lane_x, right_lane_x, MY_CAR_BEV_X
        )
        
        # 5. 시각화
        overlay = self._create_visualization(
            bev_frame, lane_mask, left_lane_x, right_lane_x
        )
        
        # 6. 텍스트 오버레이
        self._add_text_overlay(
            overlay, lane_width_m, departure_rate, lane_detected, lane_normal
        )
        
        metrics = {
            'lane_width_m': lane_width_m,
            'departure_rate': departure_rate,
            'lane_detected': lane_detected,
            'lane_normal': lane_normal,
            'left_lane_x': left_lane_x,
            'right_lane_x': right_lane_x,
        }
        
        return overlay, metrics
    
    def _create_visualization(
        self, 
        bev_frame: np.ndarray, 
        lane_mask: np.ndarray,
        left_lane_x: Optional[int],
        right_lane_x: Optional[int]
    ) -> np.ndarray:
        """시각화 오버레이 생성"""
        overlay = bev_frame.copy()
        
        # ROI 영역 표시 (디버그용)
        if self.show_debug:
            roi_y_start = max(0, MY_CAR_BEV_Y - 250)
            cv2.rectangle(
                overlay,
                (0, roi_y_start),
                (overlay.shape[1] - 1, MY_CAR_BEV_Y),
                COLOR_ROI,
                2
            )
        
        # 차선 마스크 오버레이 (반투명)
        lane_mask_color = np.zeros_like(overlay)
        lane_mask_color[lane_mask > 0] = COLOR_LANE_MASK
        overlay = cv2.addWeighted(overlay, 0.6, lane_mask_color, 0.4, 0)
        
        # 왼쪽 차선 경계선
        if left_lane_x is not None:
            cv2.line(
                overlay,
                (left_lane_x, MY_CAR_BEV_Y - 250),
                (left_lane_x, MY_CAR_BEV_Y),
                COLOR_LEFT_LANE,
                4
            )
            cv2.putText(
                overlay, "L", 
                (left_lane_x - 15, MY_CAR_BEV_Y - 260),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_LEFT_LANE, 2
            )
        
        # 오른쪽 차선 경계선
        if right_lane_x is not None:
            cv2.line(
                overlay,
                (right_lane_x, MY_CAR_BEV_Y - 250),
                (right_lane_x, MY_CAR_BEV_Y),
                COLOR_RIGHT_LANE,
                4
            )
            cv2.putText(
                overlay, "R", 
                (right_lane_x - 15, MY_CAR_BEV_Y - 260),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_RIGHT_LANE, 2
            )
        
        # 차선 중심선 (두 차선이 모두 검출된 경우)
        if left_lane_x is not None and right_lane_x is not None:
            lane_center = int((left_lane_x + right_lane_x) / 2)
            cv2.line(
                overlay,
                (lane_center, MY_CAR_BEV_Y - 250),
                (lane_center, MY_CAR_BEV_Y),
                (0, 255, 0),  # Green
                2,
                cv2.LINE_AA
            )
        
        # 차량 중심 (빨간색)
        cv2.circle(overlay, (MY_CAR_BEV_X, MY_CAR_BEV_Y), 10, COLOR_VEHICLE_CENTER, -1)
        cv2.circle(overlay, (MY_CAR_BEV_X, MY_CAR_BEV_Y), 12, (255, 255, 255), 2)
        
        # 차량 레이블
        cv2.putText(
            overlay, "CAR", 
            (MY_CAR_BEV_X - 20, MY_CAR_BEV_Y + 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_VEHICLE_CENTER, 2
        )
        
        # 차량에서 차선까지 연결선
        if left_lane_x is not None:
            cv2.line(
                overlay,
                (MY_CAR_BEV_X, MY_CAR_BEV_Y),
                (left_lane_x, MY_CAR_BEV_Y),
                (200, 200, 200),
                1,
                cv2.LINE_AA
            )
        if right_lane_x is not None:
            cv2.line(
                overlay,
                (MY_CAR_BEV_X, MY_CAR_BEV_Y),
                (right_lane_x, MY_CAR_BEV_Y),
                (200, 200, 200),
                1,
                cv2.LINE_AA
            )
        
        return overlay
    
    def _add_text_overlay(
        self,
        frame: np.ndarray,
        lane_width_m: float,
        departure_rate: float,
        lane_detected: bool,
        lane_normal: bool
    ) -> None:
        """텍스트 정보 오버레이"""
        y_offset = 30
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        
        # 배경 박스
        cv2.rectangle(frame, (5, 5), (frame.shape[1] - 5, 145), (0, 0, 0), -1)
        cv2.rectangle(frame, (5, 5), (frame.shape[1] - 5, 145), (255, 255, 255), 2)
        
        # Lane Detection Status
        status_text = "DETECTED" if lane_detected else "NOT DETECTED"
        status_color = (0, 255, 0) if lane_detected else (0, 0, 255)
        cv2.putText(frame, f"Lane: {status_text}", (15, y_offset), font, font_scale, status_color, thickness)
        y_offset += 30
        
        if lane_detected:
            # Lane Normal Status
            normal_text = "NORMAL" if lane_normal else "ABNORMAL"
            normal_color = (0, 255, 0) if lane_normal else (0, 165, 255)
            cv2.putText(frame, f"Status: {normal_text}", (15, y_offset), font, font_scale, normal_color, thickness)
            y_offset += 30
            
            # Lane Width
            if lane_width_m > 0:
                width_text = f"Width: {lane_width_m:.2f}m"
                cv2.putText(frame, width_text, (15, y_offset), font, font_scale, (255, 255, 255), thickness)
                y_offset += 30
            
            # Departure Rate
            departure_text = f"Depart: {departure_rate:+.1%}"
            departure_color = (0, 255, 0) if abs(departure_rate) < 0.35 else (0, 165, 255)
            cv2.putText(frame, departure_text, (15, y_offset), font, font_scale, departure_color, thickness)


def process_video(
    video_path: Path,
    output_path: Path,
    detection_method: str = "combined",
    show_debug: bool = False
) -> None:
    """비디오 처리 및 오버레이 생성"""
    print(f"🎥 Processing: {video_path.name}")
    print(f"   Method: {detection_method}")
    
    # Initialize
    lane_detector = ImprovedLaneDetector(detection_method)
    analyzer = BEVLaneAnalyzer(lane_detector, show_debug=show_debug)
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Create output writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (210, 600))
    
    frame_count = 0
    detected_count = 0
    normal_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process frame
        overlay, metrics = analyzer.process_frame(frame)
        
        # Write output
        writer.write(overlay)
        
        if metrics['lane_detected']:
            detected_count += 1
        if metrics['lane_normal']:
            normal_count += 1
        
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"  Frame {frame_count}/{total_frames} - "
                  f"Detected: {metrics['lane_detected']}, "
                  f"Normal: {metrics['lane_normal']}, "
                  f"Depart: {metrics['departure_rate']:+.1%}")
    
    cap.release()
    writer.release()
    
    print(f"✅ Output saved: {output_path}")
    print(f"   Detection rate: {detected_count}/{frame_count} ({100*detected_count/max(1,frame_count):.1f}%)")
    print(f"   Normal rate: {normal_count}/{frame_count} ({100*normal_count/max(1,frame_count):.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Improved Lane Detection Visualization")
    parser.add_argument(
        "--videos",
        nargs="+",
        required=True,
        help="Input video paths"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Output directory"
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["hsv", "edge", "combined", "adaptive"],
        default="combined",
        help="Detection method"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug ROI"
    )
    
    args = parser.parse_args()
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    for video_path in args.videos:
        video_path = Path(video_path)
        if not video_path.exists():
            print(f"⚠️  Video not found: {video_path}")
            continue
        
        output_path = args.output_dir / f"{video_path.stem}_improved.mp4"
        
        try:
            process_video(video_path, output_path, args.method, args.debug)
        except Exception as e:
            print(f"❌ Error processing {video_path.name}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
