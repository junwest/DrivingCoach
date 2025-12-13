#!/usr/bin/env python3
"""
간단한 ROI 선택 - Event 5만
"""
import cv2
import numpy as np
from pathlib import Path
import json

points = []
frame_display = None

def mouse_callback(event, x, y, flags, param):
    global points, frame_display
    
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append([x, y])
        
        frame_display = param['frame'].copy()
        
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        labels = ["1:좌상", "2:우상", "3:우하", "4:좌하"]
        
        for i, pt in enumerate(points):
            cv2.circle(frame_display, tuple(pt), 8, colors[i], -1)
            cv2.circle(frame_display, tuple(pt), 10, (255, 255, 255), 2)
            cv2.putText(frame_display, labels[i], (pt[0] + 15, pt[1] - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, colors[i], 2)
        
        if len(points) > 1:
            for i in range(len(points) - 1):
                cv2.line(frame_display, tuple(points[i]), tuple(points[i+1]), (0, 255, 0), 2)
        
        if len(points) == 4:
            cv2.line(frame_display, tuple(points[3]), tuple(points[0]), (0, 255, 0), 2)
            cv2.putText(frame_display, "Complete! Press SPACE", (frame_display.shape[1]//2 - 150, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        
        cv2.imshow("ROI Selection - Event 5", frame_display)

# 비디오 로드
data_dir = Path(__file__).resolve().parent.parent / "Data"
output_dir = Path(__file__).resolve().parent

video_path = data_dir / "이벤트 5.mp4"
cap = cv2.VideoCapture(str(video_path))
cap.set(cv2.CAP_PROP_POS_FRAMES, int(6.0 * 30))
ret, frame = cap.read()
cap.release()

if ret:
    print("="*60)
    print("Event 5 ROI 선택")
    print("="*60)
    print("순서: 1.좌상단 → 2.우상단 → 3.우하단 → 4.좌하단")
    print("완료 후 SPACE 키를 누르세요")
    print("="*60)
    
    frame_display = frame.copy()
    
    cv2.namedWindow("ROI Selection - Event 5")
    cv2.setMouseCallback("ROI Selection - Event 5", mouse_callback, {'frame': frame})
    cv2.imshow("ROI Selection - Event 5", frame_display)
    
    while True:
        key = cv2.waitKey(100)
        
        if key == 32 and len(points) == 4:  # Space
            break
        elif key == ord('r') or key == ord('R'):
            points = []
            frame_display = frame.copy()
            cv2.imshow("ROI Selection - Event 5", frame_display)
    
    cv2.destroyAllWindows()
    
    if len(points) == 4:
        roi_points = np.float32(points)
        
        print(f"\n선택된 ROI 포인트: {points}")
        
        # 저장
        config_path = output_dir / "이벤트 5_roi_config.json"
        config = {
            "video_name": "이벤트 5",
            "roi_points": roi_points.tolist(),
            "description": "ROI points: top-left, top-right, bottom-right, bottom-left"
        }
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ ROI config saved: {config_path}")
        
        # BEV 미리보기
        dst_points = np.float32([[0, 0], [400, 0], [400, 600], [0, 600]])
        M = cv2.getPerspectiveTransform(roi_points, dst_points)
        bev = cv2.warpPerspective(frame, M, (400, 600))
        
        preview_path = output_dir / "이벤트 5_bev_preview.jpg"
        cv2.imwrite(str(preview_path), bev)
        print(f"✅ BEV preview saved: {preview_path}")
        
        print("\n완료! 이제 interactive_roi_selector.py를 실행하세요.")
