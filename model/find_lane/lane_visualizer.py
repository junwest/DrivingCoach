#!/usr/bin/env python3
"""
Lane Detection Visualization Tool (Updated with CV-based detection)
---------------------------------
BEV 전처리를 통한 차선 검출 및 시각화 도구.
- 차선 검출 (흰색/노란색 마스킹 - Computer Vision 기반)
- 왼쪽/오른쪽 차선 경계 (파란색)
- 차량 중심 (빨간색)
- 차선 거리 및 이탈률 계산
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


class CVLaneDetector:
    """Computer Vision 기반 차선 검출 클래스"""
    
    def __init__(self):
        # HSV 범위로 흰색과 노란색 차선 검출
        # 흰색 범위
        self.lower_white = np.array([0, 0, 180])
        self.upper_white = np.array([180, 50, 255])
        
        # 노란색 범위
        self.lower_yellow = np.array([15, 80, 80])
        self.upper_yellow = np.array([35, 255, 255])
        
    def detect_lanes(self, frame: np.ndarray) -> np.ndarray:
        """
        프레임으로부터 차선 마스크를 추출
        
        Returns:
            Binary mask (0 or 1)
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 흰색 마스크
        white_mask = cv2.inRange(hsv, self.lower_white, self.upper_white)
        
        # 노란색 마스크
        yellow_mask = cv2.inRange(hsv, self.lower_yellow, self.upper_yellow)
        
        # 두 마스크 합치기
        combined_mask = cv2.bitwise_or(white_mask, yellow_mask)
        
        # Morphological operations to clean up
        kernel = np.ones((5, 5), np.uint8)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        
        # Convert to binary (0 or 1)
        binary_mask = (combined_mask > 127).astype(np.uint8)
        
        return binary_mask


class BEVLaneAnalyzer:
    """BEV 변환 및 차선 분석 클래스"""
    
    def __init__(self, lane_detector: CVLaneDetector, bev_size: Tuple[int, int] = (210, 600)):
        self.lane_detector = lane_detector
        self.bev_width, self.bev_height = bev_size
        
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
        vehicle_x: int
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        차량 중심을 기준으로 가장 가까운 왼쪽/오른쪽 차선 경계 찾기
        
        Args:
            lane_mask: 차선 마스크 (이진 이미지)
            vehicle_x: 차량 중심 x 좌표
            
        Returns:
            (left_lane_x, right_lane_x) 튜플. 없으면 None
        """
        if lane_mask.sum() == 0:
            return None, None
        
        # 차량 앞쪽 영역에서만 분석 (관심 영역)
        roi_y_start = max(0, MY_CAR_BEV_Y - 200)
        roi_y_end = MY_CAR_BEV_Y
        roi = lane_mask[roi_y_start:roi_y_end, :]
        
        # 각 열(column)의 차선 픽셀 개수 계산
        column_sums = roi.sum(axis=0)
        
        # 차선이 있는 열 찾기 (최소 5개 픽셀 이상)
        lane_threshold = 5
        lane_columns = np.where(column_sums > lane_threshold)[0]
        
        if len(lane_columns) == 0:
            return None, None
        
        # 연속된 차선 영역을 찾기 위해 clustering
        # 차선은 보통 좌우로 분리되어 있음
        lane_groups = []
        current_group = [lane_columns[0]]
        
        for i in range(1, len(lane_columns)):
            if lane_columns[i] - lane_columns[i-1] <= 5:  # 5픽셀 이내면 같은 그룹
                current_group.append(lane_columns[i])
            else:
                if len(current_group) >= 3:  # 최소 3픽셀 이상의 그룹만 유효
                    lane_groups.append(current_group)
                current_group = [lane_columns[i]]
        
        # 마지막 그룹 추가
        if len(current_group) >= 3:
            lane_groups.append(current_group)
        
        if len(lane_groups) == 0:
            return None, None
        
        # 각 그룹의 중심 계산
        lane_centers = [int(np.mean(group)) for group in lane_groups]
        
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
        """
        차선 거리 및 이탈률 계산
        
        Args:
            left_lane_x: 왼쪽 차선 x 좌표
            right_lane_x: 오른쪽 차선 x 좌표
            vehicle_x: 차량 중심 x 좌표
            pixels_per_meter: 픽셀당 미터 변환 비율
            
        Returns:
            (lane_width_m, departure_rate, lane_detected, lane_normal)
        """
        lane_detected = False
        lane_normal = False
        lane_width_m = 0.0
        departure_rate = 0.0
        
        if left_lane_x is not None and right_lane_x is not None:
            lane_detected = True
            
            # 차선 폭 계산 (미터)
            lane_width_px = right_lane_x - left_lane_x
            lane_width_m = lane_width_px / pixels_per_meter
            
            # 차선 중심 계산
            lane_center_x = (left_lane_x + right_lane_x) / 2
            
            # 차량이 차선 중심에서 얼마나 떨어져 있는지 (픽셀)
            offset_px = vehicle_x - lane_center_x
            
            # 이탈률 계산 (차량이 차선 중심에서 벗어난 정도를 차선 폭의 비율로)
            # 0에 가까우면 중앙, ±0.5 이상이면 차선 경계에 근접
            if lane_width_px > 0:
                departure_rate = offset_px / lane_width_px
            
            # 정상 범위 판단 (±30% 이내면 정상)
            lane_normal = abs(departure_rate) < 0.3
        
        elif left_lane_x is not None or right_lane_x is not None:
            # 한쪽 차선만 검출된 경우
            lane_detected = True
            lane_normal = False  # 한쪽만 보이면 비정상으로 간주
            
            if left_lane_x is not None:
                offset_px = vehicle_x - left_lane_x
                # 왼쪽 차선만 있으면 대략적 거리만 계산
                departure_rate = offset_px / 60.0  # 가정된 차선 폭 절반
            else:
                offset_px = vehicle_x - right_lane_x
                departure_rate = offset_px / 60.0
        
        return lane_width_m, departure_rate, lane_detected, lane_normal
    
    def process_frame(
        self, 
        frame: np.ndarray
    ) -> Tuple[np.ndarray, dict]:
        """
        프레임을 처리하고 시각화 오버레이 생성
        
        Returns:
            (overlay_frame, metrics_dict)
        """
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
        # BEV 프레임을 기본으로 사용
        overlay = bev_frame.copy()
        
        # 차선 마스크를 흰색으로 오버레이 (반투명)
        lane_mask_color = np.zeros_like(overlay)
        lane_mask_color[lane_mask > 0] = COLOR_LANE_MASK
        overlay = cv2.addWeighted(overlay, 0.6, lane_mask_color, 0.4, 0)
        
        # 왼쪽 차선 경계선 (파란색)
        if left_lane_x is not None:
            cv2.line(
                overlay,
                (left_lane_x, MY_CAR_BEV_Y - 200),
                (left_lane_x, MY_CAR_BEV_Y),
                COLOR_LEFT_LANE,
                3
            )
            # 차선 레이블
            cv2.putText(
                overlay, "L", 
                (left_lane_x - 10, MY_CAR_BEV_Y - 210),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_LEFT_LANE, 2
            )
        
        # 오른쪽 차선 경계선 (파란색)
        if right_lane_x is not None:
            cv2.line(
                overlay,
                (right_lane_x, MY_CAR_BEV_Y - 200),
                (right_lane_x, MY_CAR_BEV_Y),
                COLOR_RIGHT_LANE,
                3
            )
            # 차선 레이블
            cv2.putText(
                overlay, "R", 
                (right_lane_x - 10, MY_CAR_BEV_Y - 210),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_RIGHT_LANE, 2
            )
        
        # 차량 중심 (빨간색 원)
        cv2.circle(overlay, (MY_CAR_BEV_X, MY_CAR_BEV_Y), 8, COLOR_VEHICLE_CENTER, -1)
        cv2.circle(overlay, (MY_CAR_BEV_X, MY_CAR_BEV_Y), 10, (255, 255, 255), 2)
        
        # 차량 레이블
        cv2.putText(
            overlay, "Vehicle", 
            (MY_CAR_BEV_X - 30, MY_CAR_BEV_Y + 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_VEHICLE_CENTER, 2
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
        font_scale = 0.6
        thickness = 2
        
        # Lane Detection Status
        status_text = "Lane: DETECTED" if lane_detected else "Lane: NOT DETECTED"
        status_color = (0, 255, 0) if lane_detected else (0, 0, 255)
        cv2.putText(frame, status_text, (10, y_offset), font, font_scale, status_color, thickness)
        y_offset += 30
        
        if lane_detected:
            # Lane Normal Status
            normal_text = "Status: NORMAL" if lane_normal else "Status: ABNORMAL"
            normal_color = (0, 255, 0) if lane_normal else (0, 165, 255)
            cv2.putText(frame, normal_text, (10, y_offset), font, font_scale, normal_color, thickness)
            y_offset += 30
            
            # Lane Width
            if lane_width_m > 0:
                width_text = f"Width: {lane_width_m:.2f}m"
                cv2.putText(frame, width_text, (10, y_offset), font, font_scale, (255, 255, 255), thickness)
                y_offset += 30
            
            # Departure Rate
            departure_text = f"Departure: {departure_rate:+.1%}"
            departure_color = (0, 255, 0) if abs(departure_rate) < 0.3 else (0, 165, 255)
            cv2.putText(frame, departure_text, (10, y_offset), font, font_scale, departure_color, thickness)


def process_video(
    video_path: Path,
    output_path: Path
) -> None:
    """비디오 처리 및 오버레이 생성"""
    print(f"🎥 Processing: {video_path.name}")
    
    # Initialize
    lane_detector = CVLaneDetector()
    analyzer = BEVLaneAnalyzer(lane_detector)
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Create output writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (210, 600))
    
    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
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
                  f"Departure: {metrics['departure_rate']:+.1%}")
    
    cap.release()
    writer.release()
    
    print(f"✅ Output saved: {output_path}")
    print(f"   Detection rate: {detected_count}/{frame_count} ({100*detected_count/max(1,frame_count):.1f}%)")
    print(f"   Normal rate: {normal_count}/{frame_count} ({100*normal_count/max(1,frame_count):.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Lane Detection Visualization Tool")
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
        help="Output directory for processed videos"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each video
    for video_path in args.videos:
        video_path = Path(video_path)
        if not video_path.exists():
            print(f"⚠️  Video not found: {video_path}")
            continue
        
        output_path = args.output_dir / f"{video_path.stem}_lane_overlay.mp4"
        
        try:
            process_video(video_path, output_path)
        except Exception as e:
            print(f"❌ Error processing {video_path.name}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
