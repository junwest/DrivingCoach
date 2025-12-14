#!/usr/bin/env python3
"""
YOLOv8 학습/배포/추론 파이프라인을 한 곳에서 다룰 수 있는 CLI 스크립트입니다.

Google Colab 예시
-----------------
1) 런타임 준비
    %pip install --upgrade ultralytics[export] opencv-python lap numpy
    # (Colab 저장소를 쓰고 싶다면) from google.colab import drive; drive.mount('/content/drive')

2) 학습
    !python src/yolo.py train \
        --data /content/drive/MyDrive/dataset.yaml \
        --project /content/drive/MyDrive/YOLO_RESULTS \
        --name Final_Training_Run

3) TensorRT 변환
    !python src/yolo.py export-engine \
        --weights /content/drive/MyDrive/YOLO_RESULTS/Final_Training_Run/weights/best.pt

4) 벤치마크 / 검증 / 추론 역시 동일한 스크립트에서 실행할 수 있습니다.
"""

from __future__ import annotations

import argparse
import random
import time
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
from ultralytics import YOLO

try:
    import cv2
except ImportError:  # pragma: no cover - Colab 또는 로컬에서 opencv 미설치 시 안내
    cv2 = None


DEFAULT_H_MATRIX = np.array(
    [
        [-3.15065240e-01, -1.26569312e00, 5.03555735e02],
        [3.34373052e-16, -1.33275615e00, 4.06490626e02],
        [1.22865515e-18, -3.62399344e-03, 1.00000000e00],
    ],
    dtype=np.float32,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _is_cuda_device(device: str) -> bool:
    return device.lower() != "cpu" and torch.cuda.is_available()


def _sync_device(device: str) -> None:
    if _is_cuda_device(device):
        torch.cuda.synchronize()


def _ensure_file(path: Path, description: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{description} 경로를 찾을 수 없습니다: {path}")
    return path


def _ensure_opencv() -> None:
    if cv2 is None:
        raise ImportError("이 명령은 opencv-python(또는 opencv-python-headless)이 필요합니다.")


def run_train(args: argparse.Namespace) -> None:
    data_path = _ensure_file(Path(args.data).expanduser(), "data.yaml")
    project_dir = Path(args.project).expanduser()
    project_dir.mkdir(parents=True, exist_ok=True)

    set_seed(args.seed)
    print(f"[Train] YOLOv8 '{args.model}' -> '{project_dir / args.name}'")

    model = YOLO(args.model)
    train_params = dict(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str(project_dir),
        name=args.name,
        patience=args.patience,
        lr0=args.lr0,
        device=args.device,
        seed=args.seed,
    )
    if args.cache:
        train_params["cache"] = args.cache
    if args.workers is not None:
        train_params["workers"] = args.workers

    model.train(**train_params)
    print(f"[Train] 완료! 결과 디렉터리: {project_dir / args.name}")


def run_export(args: argparse.Namespace) -> None:
    weights = _ensure_file(Path(args.weights).expanduser(), "학습 가중치(.pt)")
    if not _is_cuda_device(args.device):
        raise RuntimeError("TensorRT 변환에는 CUDA GPU가 필요합니다. Colab GPU 런타임을 선택하세요.")

    model = YOLO(str(weights))
    print(f"[Export] TensorRT 변환 시작: {weights}")
    engine_path = model.export(
        format="tensorrt",
        device=args.device,
        half=args.precision == "fp16",
        dynamic=not args.static,
        batch=args.batch,
    )
    print(f"[Export] 변환 완료 → {engine_path}")


def _load_images(image_paths: Sequence[Path]) -> list[np.ndarray]:
    frames = []
    for path in image_paths:
        frame = cv2.imread(str(path))
        if frame is None:
            raise ValueError(f"이미지를 읽을 수 없습니다: {path}")
        frames.append(frame)
    return frames


def run_benchmark(args: argparse.Namespace) -> None:
    _ensure_opencv()
    engine = _ensure_file(Path(args.engine).expanduser(), ".engine 파일")
    image_dir = _ensure_file(Path(args.image_dir).expanduser(), "이미지 폴더")

    image_paths = [
        p for p in image_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]
    if len(image_paths) < args.batch_size:
        raise ValueError(f"폴더 내 이미지 수({len(image_paths)})가 배치 크기보다 적습니다.")

    random.seed(args.seed)
    batch_paths = random.sample(image_paths, args.batch_size)
    frames = _load_images(batch_paths)

    model = YOLO(str(engine))
    print(f"[Benchmark] Warm-up {args.warmup}회 진행 중...")
    for _ in range(args.warmup):
        model(frames, device=args.device, verbose=False)
        _sync_device(args.device)

    print(f"[Benchmark] {args.batch_size}장 배치 추론 시간 측정...")
    _sync_device(args.device)
    start = time.time()
    model(frames, device=args.device, verbose=False)
    _sync_device(args.device)
    elapsed_ms = (time.time() - start) * 1000
    print(f"[Benchmark] 총 소요 시간: {elapsed_ms:.2f} ms")
    print(f"[Benchmark] 1장당 평균: {elapsed_ms / args.batch_size:.2f} ms")


def run_validate(args: argparse.Namespace) -> None:
    engine = _ensure_file(Path(args.engine).expanduser(), ".engine 파일")
    data_path = _ensure_file(Path(args.data).expanduser(), "data.yaml")

    model = YOLO(str(engine))
    metrics = model.val(
        data=str(data_path),
        batch=args.batch,
        half=args.precision == "fp16",
        device=args.device,
        verbose=True,
    )
    print(f"[Validate] mAP50-95: {metrics.box.map:.4f}")
    print(f"[Validate] mAP50: {metrics.box.map50:.4f}")


def _load_homography(path: str | None) -> np.ndarray:
    if not path:
        return DEFAULT_H_MATRIX
    matrix_path = _ensure_file(Path(path).expanduser(), "Homography(.npy)")
    matrix = np.load(matrix_path)
    if matrix.shape != (3, 3):
        raise ValueError(f"Homography 행렬 shape가 (3, 3)이 아닙니다: {matrix.shape}")
    return matrix.astype(np.float32)


def run_track_video(args: argparse.Namespace) -> None:
    _ensure_opencv()
    engine = _ensure_file(Path(args.engine).expanduser(), ".engine 파일")
    video_in = _ensure_file(Path(args.video_in).expanduser(), "입력 비디오")
    video_out = Path(args.video_out_original).expanduser()
    video_out.parent.mkdir(parents=True, exist_ok=True)

    bev_out = Path(args.video_out_bev).expanduser() if args.video_out_bev else None
    if bev_out:
        bev_out.parent.mkdir(parents=True, exist_ok=True)

    H = _load_homography(args.homography)
    model = YOLO(str(engine))

    cap = cv2.VideoCapture(str(video_in))
    if not cap.isOpened():
        raise RuntimeError(f"비디오를 열 수 없습니다: {video_in}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer_original = cv2.VideoWriter(str(video_out), fourcc, fps, (width, height))
    writer_bev = None
    if bev_out:
        writer_bev = cv2.VideoWriter(str(bev_out), fourcc, fps, (args.dst_width, args.dst_height))

    frame_count = 0
    start_time = time.time()
    print(f"[Track] '{video_in}' 처리 시작...")

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame_count += 1
        results = model.track(frame, persist=True, verbose=False, device=args.device)
        bev_canvas = np.zeros((args.dst_height, args.dst_width, 3), dtype=np.uint8)

        if results and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy()
            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"ID {track_id}",
                    (x1, max(0, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

                bottom_center = np.array([[[((x1 + x2) / 2), y2]]], dtype=np.float32)
                bev_point = cv2.perspectiveTransform(bottom_center, H)[0][0]
                bev_x, bev_y = int(bev_point[0]), int(bev_point[1])
                if 0 <= bev_x < args.dst_width and 0 <= bev_y < args.dst_height:
                    cv2.circle(bev_canvas, (bev_x, bev_y), 5, (0, 0, 255), -1)

        writer_original.write(frame)
        if writer_bev is not None:
            writer_bev.write(bev_canvas)

        if frame_count % 100 == 0:
            print(f"[Track] ... {frame_count} 프레임 처리 중")

    total_time = time.time() - start_time
    fps_result = frame_count / total_time if frame_count else 0.0
    print(f"[Track] 총 프레임: {frame_count}, 평균 FPS: {fps_result:.2f}")
    print(f"[Track] 저장 완료 → {video_out}")
    if writer_bev:
        print(f"[Track] BEV 비디오 저장 완료 → {bev_out}")

    cap.release()
    writer_original.release()
    if writer_bev:
        writer_bev.release()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="YOLOv8 학습/배포/추론 도우미 (train/export/benchmark/validate/track)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="YOLOv8 학습")
    train_parser.add_argument("--data", required=True, help="YOLO 데이터셋 YAML 경로")
    train_parser.add_argument("--model", default="yolov8s.pt", help="시작 가중치 (.pt)")
    train_parser.add_argument("--epochs", type=int, default=100)
    train_parser.add_argument("--imgsz", type=int, default=640)
    train_parser.add_argument("--batch", type=int, default=16)
    train_parser.add_argument("--project", default="./runs/detect", help="실험 결과 상위 디렉터리")
    train_parser.add_argument("--name", default="exp", help="실험 이름 (하위 폴더)")
    train_parser.add_argument("--patience", type=int, default=50)
    train_parser.add_argument("--lr0", type=float, default=0.01)
    train_parser.add_argument("--device", default="0", help="'0' 또는 'cpu' 등, YOLO device 인자")
    train_parser.add_argument("--cache", choices=["ram", "disk"], help="데이터셋 캐시 옵션")
    train_parser.add_argument("--workers", type=int, help="DataLoader workers 수")
    train_parser.add_argument("--seed", type=int, default=42)
    train_parser.set_defaults(func=run_train)

    export_parser = subparsers.add_parser("export-engine", help="TensorRT 엔진으로 변환")
    export_parser.add_argument("--weights", required=True, help="학습 완료 .pt 경로")
    export_parser.add_argument("--batch", type=int, default=40, help="최적화 배치 사이즈 힌트")
    export_parser.add_argument("--precision", choices=["fp16", "fp32"], default="fp16")
    export_parser.add_argument(
        "--static",
        action="store_true",
        help="dynamic=False 로 고정 (기본: dynamic=True)",
    )
    export_parser.add_argument("--device", default="0")
    export_parser.set_defaults(func=run_export)

    bench_parser = subparsers.add_parser("benchmark", help=".engine 성능 측정")
    bench_parser.add_argument("--engine", required=True, help="TensorRT .engine 경로")
    bench_parser.add_argument("--image-dir", required=True, help="이미지 폴더 경로")
    bench_parser.add_argument("--batch-size", type=int, default=40)
    bench_parser.add_argument("--device", default="0")
    bench_parser.add_argument("--warmup", type=int, default=1)
    bench_parser.add_argument("--seed", type=int, default=42)
    bench_parser.set_defaults(func=run_benchmark)

    val_parser = subparsers.add_parser("validate", help=".engine 정확도 검증")
    val_parser.add_argument("--engine", required=True)
    val_parser.add_argument("--data", required=True)
    val_parser.add_argument("--batch", type=int, default=40)
    val_parser.add_argument("--precision", choices=["fp16", "fp32"], default="fp16")
    val_parser.add_argument("--device", default="0")
    val_parser.set_defaults(func=run_validate)

    track_parser = subparsers.add_parser("track-video", help="TensorRT 엔진 기반 다중 객체 추적 + BEV 투영")
    track_parser.add_argument("--engine", required=True)
    track_parser.add_argument("--video-in", required=True)
    track_parser.add_argument("--video-out-original", required=True, help="박스가 그려진 출력 비디오")
    track_parser.add_argument(
        "--video-out-bev",
        help="BEV 캔버스 출력 비디오 (옵션)",
    )
    track_parser.add_argument("--dst-width", type=int, default=710)
    track_parser.add_argument("--dst-height", type=int, default=246)
    track_parser.add_argument("--homography", help=".npy 형태의 3x3 행렬 경로 (미입력 시 기본값 사용)")
    track_parser.add_argument("--device", default="0")
    track_parser.set_defaults(func=run_track_video)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

