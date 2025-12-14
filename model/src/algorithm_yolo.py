#!/usr/bin/env python3
"""
YOLO 객체 탐지 모델 학습 및 분석 파이프라인

algorithm_lane.py와 유사한 구조로 YOLO 모델의 학습, 검증, 추론을 담당합니다.
"""

from __future__ import annotations

import argparse
import csv
import random
import time
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
import torch
from tqdm import tqdm
from ultralytics import YOLO


# 기본 설정
DEFAULT_H_MATRIX = np.array(
    [
        [-3.15065240e-01, -1.26569312e00, 5.03555735e02],
        [3.34373052e-16, -1.33275615e00, 4.06490626e02],
        [1.22865515e-18, -3.62399344e-03, 1.00000000e00],
    ],
    dtype=np.float32,
)


def set_seed(seed: int) -> None:
    """재현 가능한 결과를 위한 시드 설정"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class YOLOObjectDetector:
    """YOLO 기반 객체 탐지 및 추적 분석기"""
    
    def __init__(
        self,
        model_path: str | Path,
        device: str = 'auto',
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ):
        """
        Args:
            model_path: YOLO 모델 파일 경로 (.pt 또는 .engine)
            device: 디바이스 ('cuda', 'cpu', 또는 'auto')
            conf_threshold: 신뢰도 임계값
            iou_threshold: IoU 임계값
        """
        if device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
        
        self.model = YOLO(str(model_path))
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        print(f"모델 로드 완료: {model_path}")
        print(f"디바이스: {self.device}")
        print(f"신뢰도 임계값: {conf_threshold}")
        print(f"IoU 임계값: {iou_threshold}")
    
    def detect(self, image: np.ndarray, conf: float | None = None) -> dict:
        """
        단일 이미지에서 객체 탐지
        
        Args:
            image: BGR 형식의 numpy array
            conf: 신뢰도 임계값 (None이면 self.conf_threshold 사용)
            
        Returns:
            dict: 탐지 결과
                - boxes: 바운딩 박스 좌표 [[x1, y1, x2, y2], ...]
                - classes: 클래스 ID 리스트
                - confidences: 신뢰도 리스트
                - class_names: 클래스 이름 리스트
        """
        if conf is None:
            conf = self.conf_threshold
        
        results = self.model(
            image,
            conf=conf,
            iou=self.iou_threshold,
            verbose=False,
            device=self.device,
        )
        
        result = results[0]
        boxes = []
        classes = []
        confidences = []
        class_names = []
        
        if result.boxes is not None:
            boxes_data = result.boxes.cpu().numpy()
            for box in boxes_data:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                conf_val = float(box.conf[0])
                
                boxes.append([x1, y1, x2, y2])
                classes.append(cls)
                confidences.append(conf_val)
                class_names.append(result.names.get(cls, "Unknown"))
        
        return {
            'boxes': boxes,
            'classes': classes,
            'confidences': confidences,
            'class_names': class_names,
            'image': image,
        }
    
    def track(self, image: np.ndarray, persist: bool = True, conf: float | None = None) -> dict:
        """
        객체 추적 (트래킹 ID 포함)
        
        Args:
            image: BGR 형식의 numpy array
            persist: 트래킹 히스토리 유지 여부
            conf: 신뢰도 임계값
            
        Returns:
            dict: 추적 결과
                - boxes: 바운딩 박스 좌표
                - track_ids: 트래킹 ID 리스트
                - classes: 클래스 ID 리스트
                - confidences: 신뢰도 리스트
                - class_names: 클래스 이름 리스트
        """
        if conf is None:
            conf = self.conf_threshold
        
        results = self.model.track(
            image,
            persist=persist,
            conf=conf,
            iou=self.iou_threshold,
            verbose=False,
            device=self.device,
        )
        
        result = results[0]
        boxes = []
        track_ids = []
        classes = []
        confidences = []
        class_names = []
        
        if result.boxes is not None and result.boxes.id is not None:
            boxes_data = result.boxes.cpu().numpy()
            for box in boxes_data:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                conf_val = float(box.conf[0])
                tid = int(box.id[0])
                
                boxes.append([x1, y1, x2, y2])
                track_ids.append(tid)
                classes.append(cls)
                confidences.append(conf_val)
                class_names.append(result.names.get(cls, "Unknown"))
        
        return {
            'boxes': boxes,
            'track_ids': track_ids,
            'classes': classes,
            'confidences': confidences,
            'class_names': class_names,
            'image': image,
        }
    
    def draw_detections(
        self,
        image: np.ndarray,
        boxes: list,
        class_names: list,
        confidences: list,
        track_ids: list | None = None,
    ) -> np.ndarray:
        """
        탐지 결과를 이미지에 그리기
        
        Args:
            image: 원본 이미지
            boxes: 바운딩 박스 리스트
            class_names: 클래스 이름 리스트
            confidences: 신뢰도 리스트
            track_ids: 트래킹 ID 리스트 (선택)
            
        Returns:
            overlay: 박스가 그려진 이미지
        """
        overlay = image.copy()
        
        for i, (box, name, conf) in enumerate(zip(boxes, class_names, confidences)):
            x1, y1, x2, y2 = box
            
            # 박스 그리기
            color = (0, 255, 0)  # 초록색
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            
            # 레이블 생성
            if track_ids is not None and i < len(track_ids):
                label = f"ID{track_ids[i]} {name} {conf:.2f}"
            else:
                label = f"{name} {conf:.2f}"
            
            # 레이블 배경
            (label_w, label_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(
                overlay,
                (x1, y1 - label_h - 10),
                (x1 + label_w, y1),
                color,
                -1,
            )
            
            # 레이블 텍스트
            cv2.putText(
                overlay,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )
        
        return overlay
    
    def process_video(
        self,
        video_path: str | Path,
        output_path: str | Path,
        use_tracking: bool = True,
        max_frames: int | None = None,
    ) -> None:
        """
        영상 파일 처리 및 결과 저장
        
        Args:
            video_path: 입력 영상 경로
            output_path: 출력 영상 경로
            use_tracking: 트래킹 사용 여부
            max_frames: 처리할 최대 프레임 수 (None이면 전체)
        """
        video_path = Path(video_path)
        output_path = Path(output_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"영상을 열 수 없습니다: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frame_count = 0
        start_time = time.time()
        
        print(f"영상 처리 시작: {video_path}")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if use_tracking:
                    result = self.track(frame)
                    track_ids = result['track_ids']
                else:
                    result = self.detect(frame)
                    track_ids = None
                
                overlay = self.draw_detections(
                    frame,
                    result['boxes'],
                    result['class_names'],
                    result['confidences'],
                    track_ids,
                )
                
                writer.write(overlay)
                frame_count += 1
                
                if max_frames and frame_count >= max_frames:
                    break
                
                if frame_count % 100 == 0:
                    print(f"처리 중... {frame_count} 프레임")
        
        finally:
            cap.release()
            writer.release()
        
        elapsed = time.time() - start_time
        fps_result = frame_count / elapsed if elapsed > 0 else 0
        
        print(f"완료! 총 {frame_count} 프레임, 평균 FPS: {fps_result:.2f}")
        print(f"결과 저장: {output_path}")


def train_yolo_model(
    data_yaml: str | Path,
    model_name: str = "yolov8n.pt",
    epochs: int = 100,
    imgsz: int = 640,
    batch: int = 16,
    project: str | Path = "./runs/detect",
    name: str = "exp",
    device: str = "0",
    seed: int = 42,
    **kwargs,
) -> Path:
    """
    YOLO 모델 학습
    
    Args:
        data_yaml: 데이터셋 YAML 파일 경로
        model_name: 시작 모델 이름 (예: yolov8n.pt, yolov8s.pt)
        epochs: 학습 에포크 수
        imgsz: 이미지 크기
        batch: 배치 크기
        project: 프로젝트 디렉터리
        name: 실험 이름
        device: 디바이스 ('0', 'cpu' 등)
        seed: 랜덤 시드
        **kwargs: 추가 학습 파라미터
        
    Returns:
        Path: 학습 결과 디렉터리 경로
    """
    data_yaml = Path(data_yaml)
    if not data_yaml.exists():
        raise FileNotFoundError(f"데이터셋 YAML을 찾을 수 없습니다: {data_yaml}")
    
    project = Path(project)
    project.mkdir(parents=True, exist_ok=True)
    
    set_seed(seed)
    
    print(f"YOLO 모델 학습 시작")
    print(f"  - 모델: {model_name}")
    print(f"  - 데이터: {data_yaml}")
    print(f"  - 에포크: {epochs}")
    print(f"  - 배치 크기: {batch}")
    print(f"  - 이미지 크기: {imgsz}")
    print(f"  - 결과 디렉터리: {project / name}")
    
    model = YOLO(model_name)
    
    train_params = {
        'data': str(data_yaml),
        'epochs': epochs,
        'imgsz': imgsz,
        'batch': batch,
        'project': str(project),
        'name': name,
        'device': device,
        'seed': seed,
        **kwargs,
    }
    
    model.train(**train_params)
    
    result_dir = project / name
    print(f"학습 완료! 결과: {result_dir}")
    return result_dir


def export_to_tensorrt(
    weights_path: str | Path,
    device: str = "0",
    half: bool = True,
    dynamic: bool = True,
    batch: int = 40,
) -> Path:
    """
    YOLO 모델을 TensorRT 엔진으로 변환
    
    Args:
        weights_path: 학습된 가중치 파일 경로 (.pt)
        device: GPU 디바이스
        half: FP16 사용 여부
        dynamic: 동적 배치 사용 여부
        batch: 배치 크기 힌트
        
    Returns:
        Path: 생성된 .engine 파일 경로
    """
    weights_path = Path(weights_path)
    if not weights_path.exists():
        raise FileNotFoundError(f"가중치 파일을 찾을 수 없습니다: {weights_path}")
    
    if device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("TensorRT 변환에는 CUDA GPU가 필요합니다.")
    
    model = YOLO(str(weights_path))
    
    print(f"TensorRT 변환 시작: {weights_path}")
    print(f"  - 정밀도: {'FP16' if half else 'FP32'}")
    print(f"  - 동적 배치: {dynamic}")
    print(f"  - 배치 크기: {batch}")
    
    engine_path = model.export(
        format="tensorrt",
        device=device,
        half=half,
        dynamic=dynamic,
        batch=batch,
    )
    
    print(f"변환 완료: {engine_path}")
    return Path(engine_path)


def validate_model(
    model_path: str | Path,
    data_yaml: str | Path,
    batch: int = 40,
    device: str = "0",
) -> dict:
    """
    모델 검증 및 정확도 측정
    
    Args:
        model_path: 모델 파일 경로 (.pt 또는 .engine)
        data_yaml: 데이터셋 YAML 파일 경로
        batch: 배치 크기
        device: 디바이스
        
    Returns:
        dict: 검증 메트릭
    """
    model_path = Path(model_path)
    data_yaml = Path(data_yaml)
    
    if not model_path.exists():
        raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
    if not data_yaml.exists():
        raise FileNotFoundError(f"데이터셋 YAML을 찾을 수 없습니다: {data_yaml}")
    
    model = YOLO(str(model_path))
    
    print(f"모델 검증 시작: {model_path}")
    
    metrics = model.val(
        data=str(data_yaml),
        batch=batch,
        device=device,
        verbose=True,
    )
    
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"mAP50: {metrics.box.map50:.4f}")
    
    return {
        'map': metrics.box.map,
        'map50': metrics.box.map50,
        'map75': metrics.box.map75,
    }


def parse_args() -> argparse.Namespace:
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="YOLO 모델 학습 및 분석 파이프라인"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # 학습 명령
    train_parser = subparsers.add_parser("train", help="YOLO 모델 학습")
    train_parser.add_argument("--data", required=True, help="데이터셋 YAML 경로")
    train_parser.add_argument("--model", default="yolov8n.pt", help="시작 모델")
    train_parser.add_argument("--epochs", type=int, default=100)
    train_parser.add_argument("--imgsz", type=int, default=640)
    train_parser.add_argument("--batch", type=int, default=16)
    train_parser.add_argument("--project", default="./runs/detect")
    train_parser.add_argument("--name", default="exp")
    train_parser.add_argument("--device", default="0")
    train_parser.add_argument("--seed", type=int, default=42)
    
    # TensorRT 변환 명령
    export_parser = subparsers.add_parser("export", help="TensorRT로 변환")
    export_parser.add_argument("--weights", required=True, help="가중치 파일 경로")
    export_parser.add_argument("--device", default="0")
    export_parser.add_argument("--half", action="store_true", help="FP16 사용")
    export_parser.add_argument("--static", action="store_true", help="정적 배치")
    export_parser.add_argument("--batch", type=int, default=40)
    
    # 검증 명령
    val_parser = subparsers.add_parser("validate", help="모델 검증")
    val_parser.add_argument("--model", required=True, help="모델 파일 경로")
    val_parser.add_argument("--data", required=True, help="데이터셋 YAML 경로")
    val_parser.add_argument("--batch", type=int, default=40)
    val_parser.add_argument("--device", default="0")
    
    # 영상 처리 명령
    video_parser = subparsers.add_parser("process-video", help="영상 처리")
    video_parser.add_argument("--model", required=True, help="모델 파일 경로")
    video_parser.add_argument("--input", required=True, help="입력 영상 경로")
    video_parser.add_argument("--output", required=True, help="출력 영상 경로")
    video_parser.add_argument("--conf", type=float, default=0.25)
    video_parser.add_argument("--device", default="auto")
    video_parser.add_argument("--no-tracking", action="store_true")
    video_parser.add_argument("--max-frames", type=int, help="최대 프레임 수")
    
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_args()
    
    if args.command == "train":
        train_yolo_model(
            data_yaml=args.data,
            model_name=args.model,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            project=args.project,
            name=args.name,
            device=args.device,
            seed=args.seed,
        )
    
    elif args.command == "export":
        export_to_tensorrt(
            weights_path=args.weights,
            device=args.device,
            half=args.half,
            dynamic=not args.static,
            batch=args.batch,
        )
    
    elif args.command == "validate":
        validate_model(
            model_path=args.model,
            data_yaml=args.data,
            batch=args.batch,
            device=args.device,
        )
    
    elif args.command == "process-video":
        detector = YOLOObjectDetector(
            model_path=args.model,
            device=args.device,
            conf_threshold=args.conf,
        )
        detector.process_video(
            video_path=args.input,
            output_path=args.output,
            use_tracking=not args.no_tracking,
            max_frames=args.max_frames,
        )


if __name__ == "__main__":
    main()