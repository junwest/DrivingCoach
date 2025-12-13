#!/usr/bin/env python3
"""
개선된 ROI 선택 도구 - 시각적 가이드 포함
"""
import cv2
import numpy as np
from pathlib import Path
import json

points = []
frame_display = None
video_name = ""

def mouse_callback(event, x, y, flags, param):
    """마우스 클릭 이벤트"""
    global points, frame_display
    
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append([x, y])
        
        # 화면 업데이트
        frame_display = param['frame'].copy()
        
        # 점 그리기
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]  # 각 점마다 다른 색
        labels = ["1:좌상", "2:우상", "3:우하", "4:좌하"]
        
        for i, pt in enumerate(points):
            cv2.circle(frame_display, tuple(pt), 8, colors[i], -1)
            cv2.circle(frame_display, tuple(pt), 10, (255, 255, 255), 2)
            cv2.putText(
                frame_display,
                labels[i],
                (pt[0] + 15, pt[1] - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                colors[i],
                2
            )
        
        # 선 그리기
        if len(points) > 1:
            for i in range(len(points) - 1):
                cv2.line(frame_display, tuple(points[i]), tuple(points[i+1]), (0, 255, 0), 2)
        
        if len(points) == 4:
            cv2.line(frame_display, tuple(points[3]), tuple(points[0]), (0, 255, 0), 2)
            
            # 완료 메시지
            cv2.rectangle(frame_display, (10, 10), (frame_display.shape[1]-10, 80), (0, 0, 0), -1)
            cv2.rectangle(frame_display, (10, 10), (frame_display.shape[1]-10, 80), (0, 255, 0), 3)
            cv2.putText(
                frame_display,
                "ROI Selection Complete!",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2
            )
            cv2.putText(
                frame_display,
                "Press ENTER to continue or 'R' to reset",
                (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1
            )
        
        cv2.imshow("ROI Selection", frame_display)

def select_roi_with_guide(frame, video_name_param):
    """가이드가 있는 ROI 선택"""
    global points, frame_display, video_name
    
    video_name = video_name_param
    points = []
    frame_display = frame.copy()
    
    # 가이드 박스 그리기
    h, w = frame.shape[:2]
    
    # 상단 가이드
    cv2.rectangle(frame_display, (0, 0), (w, 120), (0, 0, 0), -1)
    cv2.rectangle(frame_display, (0, 0), (w, 120), (255, 255, 255), 2)
    
    cv2.putText(frame_display, "ROI Selection Guide", (20, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(frame_display, "Click 4 points in order:", (20, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    cv2.putText(frame_display, "1:Top-Left  2:Top-Right  3:Bottom-Right  4:Bottom-Left", (20, 90),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 255), 1)
    
    # 예시 사각형 (오른쪽 하단)
    example_rect = np.array([
        [w-200, h-150],  # 좌상
        [w-50, h-150],   # 우상
        [w-50, h-50],    # 우하
        [w-200, h-50]    # 좌하
    ])
    
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    for i in range(4):
        pt1 = tuple(example_rect[i])
        pt2 = tuple(example_rect[(i + 1) % 4])
        cv2.line(frame_display, pt1, pt2, colors[i], 2)
        cv2.circle(frame_display, pt1, 5, colors[i], -1)
        cv2.putText(frame_display, str(i+1), 
                   (pt1[0] + 10, pt1[1] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[i], 2)
    
    cv2.namedWindow("ROI Selection")
    cv2.setMouseCallback("ROI Selection", mouse_callback, {'frame': frame})
    cv2.imshow("ROI Selection", frame_display)
    
    print("\n" + "="*70)
    print("ROI 선택 - 차선이 잘 보이는 사다리꼴 영역을 선택하세요")
    print("="*70)
    print("순서: 1.좌상단 → 2.우상단 → 3.우하단 → 4.좌하단")
    print("TIP: 차선 양쪽보다 약간 넓게 선택하세요")
    print("="*70)
    
    while True:
        key = cv2.waitKey(100)
        
        if key == 13 and len(points) == 4:  # Enter
            break
        elif key == ord('r') or key == ord('R'):  # Reset
            points = []
            frame_display = frame.copy()
            # 가이드 다시 그리기
            cv2.rectangle(frame_display, (0, 0), (w, 120), (0, 0, 0), -1)
            cv2.rectangle(frame_display, (0, 0), (w, 120), (255, 255, 255), 2)
            cv2.putText(frame_display, "ROI Selection Guide", (20, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(frame_display, "Click 4 points in order:", (20, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
            cv2.putText(frame_display, "1:Top-Left  2:Top-Right  3:Bottom-Right  4:Bottom-Left", (20, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 255), 1)
            cv2.imshow("ROI Selection", frame_display)
            print("ROI 초기화됨")
        elif key == 27:  # ESC
            cv2.destroyAllWindows()
            return None
    
    cv2.destroyAllWindows()
    
    if len(points) == 4:
        print(f"\n선택된 ROI 포인트:")
        for i, pt in enumerate(points):
            print(f"  {i+1}. {pt}")
        return np.float32(points)
    
    return None

def main():
    print("="*70)
    print(" 개선된 ROI 선택 도구")
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
        
        # 비디오 로드
        cap = cv2.VideoCapture(str(video_info['path']))
        
        # 차선이 잘 보이는 프레임 선택 (5초)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(5.0 * 30))
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print(f"❌ Failed to read video")
            continue
        
        # 기존 설정 확인
        config_path = output_dir / f"{video_info['name']}_roi_config.json"
        if config_path.exists():
            choice = input(f"\n기존 ROI 설정이 있습니다. 다시 선택하시겠습니까? (y/n, 기본 n): ").strip().lower()
            if choice != 'y':
                print("스킵됨")
                continue
        
        # ROI 선택
        roi_points = select_roi_with_guide(frame, video_info['name'])
        
        if roi_points is not None:
            # 저장
            config = {
                "video_name": video_info['name'],
                "roi_points": roi_points.tolist(),
                "description": "ROI points: top-left, top-right, bottom-right, bottom-left"
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n💾 ROI config saved: {config_path}")
            
            # BEV 미리보기
            dst_points = np.float32([[0, 0], [400, 0], [400, 600], [0, 600]])
            M = cv2.getPerspectiveTransform(roi_points, dst_points)
            bev = cv2.warpPerspective(frame, M, (400, 600))
            
            preview_path = output_dir / f"{video_info['name']}_bev_preview.jpg"
            cv2.imwrite(str(preview_path), bev)
            print(f"📸 BEV preview saved: {preview_path}")
            
            # BEV 미리보기 창 표시
            cv2.imshow(f"BEV Preview - {video_info['name']}", bev)
            print("\nBEV 변환 결과를 확인하세요. 아무 키나 누르면 계속됩니다...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    
    print("\n" + "="*70)
    print("✅ ROI 선택 완료!")
    print("="*70)
    print("\n이제 interactive_roi_selector.py를 실행하세요:")
    print("  python find_lane/interactive_roi_selector.py")

if __name__ == "__main__":
    main()
