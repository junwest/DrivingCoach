#!/usr/bin/env python3
"""
시나리오 메모
-------------
4 차선 변경 후 깜빡이 안 끔
5 깜빡이 없이 차선 변경
-6 제대로 된 차선 변경인데 삭제하기로 함-
7 와이퍼(비온다 가정) + 비상깜빡이 → 전조등(안개등) 키라고 안내
8 우회전 보행자도로인데 보행자가 없고 뒤에서 클락션 울릴때
9 보행자 있는데 클락션 울림 (위협운전)
10 위협운전(갑자기 급정거 + 클락션)
11 와이퍼 + 비상깜빡이 → 비오는날 비깜 키는걸로 인지해서 피드백
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import librosa
import numpy as np
import torch
from ultralytics import YOLO  # type: ignore

from AudioCNN import CLASS_NAMES as AUDIO_CLASS_NAMES  # type: ignore
from AudioCNN import AudioCNN  # type: ignore
from lane_detect import UNet as LaneUNet  # type: ignore
from lane_detect import predict_mask as lane_predict_mask  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_YOLO_MODEL = MODELS_DIR / "YOLO.pt"
DEFAULT_LANE_MODEL = MODELS_DIR / "lane_detect.pt"
DEFAULT_AUDIO_MODEL = MODELS_DIR / "AudioCNN.pt"

VEHICLE_CLASSES_DEFAULT = ["car", "truck", "bus", "motorcycle"]
PEDESTRIAN_CLASS = "pedestrian"
CROSSWALK_SIGN_CLASS = "crosswalk sign"

LANE_IMAGE_SIZE = (256, 256)
LANE_MASK_THRESHOLD = 0.5
LANE_CHANGE_THRESHOLD_PX = 40.0

H_MATRIX = np.array(
    [
        [-3.97727273e-02, -3.24810606e-01, 1.00492424e02],
        [4.37257068e-16, -2.54829545e00, 7.89971591e02],
        [1.16574774e-18, -3.69318182e-03, 1.00000000e00],
    ]
)
PIXELS_PER_METER_Y = 20.0
PIXELS_PER_METER_X = 20.0
MY_CAR_BEV_X = 105
MY_CAR_BEV_Y = 400
CALIBRATION_Y_FAR = 310.0
DST_HEIGHT = 300
TAILGATING_DISTANCE_M = 3.0

LOWER_SIGNAL = np.array([35, 80, 80])
UPPER_SIGNAL = np.array([100, 255, 255])
SIGNAL_PIXEL_THRESHOLD = 10

SCENARIO_MESSAGES: Dict[int, str] = {
    4: "차선 변경 후 방향지시등을 끄지 않았습니다.",
    5: "방향지시등 없이 차선을 변경했습니다.",
    7: "와이퍼+비상등 감지: 전조등/안개등을 켜 주세요.",
    8: "우회전 보행자 구간에서 경적이 울렸습니다 (보행자 없음).",
    9: "보행자 근처에서 경적이 울렸습니다.",
    10: "급정거 중 경적 감지: 위협 운전입니다.",
    11: "비 오는 날 비상등 남용이 감지되었습니다.",
}


@dataclass
class AudioInferenceConfig:
    sr: int = 16000
    duration: float = 2.0
    n_mels: int = 64
    n_fft: int = 1024
    hop_length: int = 256


@dataclass
class ChunkFeatures:
    chunk_id: int
    horn: bool = False
    blinker_audio: bool = False
    wiper_audio: bool = False
    left_signal_on: bool = False
    right_signal_on: bool = False
    hazard_on: bool = False
    lane_change: bool = False
    lane_offset: float = 0.0
    tailgating: bool = False
    sudden_stop: bool = False
    pedestrian_present: bool = False
    crosswalk_sign_present: bool = False


@dataclass
class ChunkResult:
    chunk_id: int
    scenario_id: int
    message: str
    features: ChunkFeatures
    audio_text: str


@dataclass
class ScenarioState:
    last_lane_change_chunk: Optional[int] = None
    last_lane_change_used_blinker: bool = False
    blinker_still_on_chunks: int = 0
    last_wiper_hazard_chunk: Optional[int] = None


class AudioEventDetector:
    def __init__(self, model_path: Path, device: torch.device, config: AudioInferenceConfig):
        self.config = config
        self.device = device
        self.model = AudioCNN(num_classes=len(AUDIO_CLASS_NAMES)).to(device)
        checkpoint = torch.load(model_path, map_location=device)
        if isinstance(checkpoint, dict) and "model" in checkpoint:
            checkpoint = checkpoint["model"]
        self.model.load_state_dict(checkpoint, strict=False)
        self.model.eval()

    def predict(self, chunk: np.ndarray) -> Tuple[Optional[str], float, Dict[str, float]]:
        if chunk.size == 0:
            return None, 0.0, {}
        target_len = int(self.config.sr * self.config.duration)
        if len(chunk) < target_len:
            chunk = np.pad(chunk, (0, target_len - len(chunk)))
        else:
            chunk = chunk[:target_len]
        mel = librosa.feature.melspectrogram(
            y=chunk,
            sr=self.config.sr,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            n_mels=self.config.n_mels,
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)
        mel_db = (mel_db - mel_db.mean()) / (mel_db.std() + 1e-6)
        tensor = torch.tensor(mel_db, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0).cpu().numpy()
        top_idx = int(np.argmax(probs))
        top_prob = float(probs[top_idx])
        top_label = AUDIO_CLASS_NAMES[top_idx]
        prob_map = {AUDIO_CLASS_NAMES[i]: float(p) for i, p in enumerate(probs)}
        return top_label, top_prob, prob_map


class LaneChangeMonitor:
    def __init__(
        self,
        model_path: Path,
        device: torch.device,
        image_size: Tuple[int, int],
        threshold_px: float,
    ):
        self.device = device
        self.image_size = image_size
        self.threshold_px = threshold_px
        self.prev_center: Optional[float] = None
        self.model = LaneUNet(n_channels=3, n_classes=1, bilinear=True).to(device)
        checkpoint = torch.load(model_path, map_location=device)
        if isinstance(checkpoint, dict) and "model" in checkpoint:
            checkpoint = checkpoint["model"]
        self.model.load_state_dict(checkpoint, strict=False)
        self.model.eval()

    def process(self, frame: np.ndarray) -> Tuple[bool, float]:
        tensor = self._frame_to_tensor(frame)
        mask = lane_predict_mask(self.model, tensor, self.device, LANE_MASK_THRESHOLD).squeeze()
        center = self._estimate_center(mask)
        lane_change = False
        offset = 0.0
        if center is not None:
            offset = center - (mask.shape[1] / 2)
            if self.prev_center is not None and abs(center - self.prev_center) >= self.threshold_px:
                lane_change = True
            self.prev_center = center
        return lane_change, offset

    def _frame_to_tensor(self, frame: np.ndarray) -> torch.Tensor:
        resized = cv2.resize(frame, self.image_size)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        tensor = torch.from_numpy(rgb.transpose(2, 0, 1)).unsqueeze(0)
        return tensor

    def _estimate_center(self, mask: np.ndarray) -> Optional[float]:
        if mask.ndim != 2:
            return None
        h = mask.shape[0]
        lower = mask[int(h * 0.7) :]
        coords = np.column_stack(np.where(lower > 0.5))
        if coords.size == 0:
            return None
        return float(coords[:, 1].mean())


class EmergencyBrakingSystem:
    def __init__(self, vehicle_classes: Sequence[str]):
        self.history: Dict[int, List[Tuple[int, float]]] = {}
        self.last_warning: Dict[int, int] = {}
        self.frame_counter = 0
        self.vehicle_classes = set(vehicle_classes)

    def check(self, current_objects: List[Dict[str, float]]) -> bool:
        self.frame_counter += 1
        is_danger_detected = False
        present_ids = set()
        for obj in current_objects:
            if obj["class_name"] not in self.vehicle_classes:
                continue
            if abs(obj["distance_lateral_m"]) > 1.8:
                continue
            tid = obj["track_id"]
            dist = obj["distance_forward_m"]
            present_ids.add(tid)
            if tid not in self.history:
                self.history[tid] = []
            self.history[tid].append((self.frame_counter, dist))
            self.history[tid] = [h for h in self.history[tid] if self.frame_counter - h[0] <= 15]
            if len(self.history[tid]) >= 10:
                curr_dist = dist
                mid_dist = self.history[tid][-5][1]
                velocity_recent = mid_dist - curr_dist
                if velocity_recent >= 2.0 and dist <= 1.0:
                    last_warn = self.last_warning.get(tid, -999)
                    if self.frame_counter - last_warn > 20:
                        is_danger_detected = True
                        self.last_warning[tid] = self.frame_counter
        for tid in list(self.history.keys()):
            if tid not in present_ids:
                del self.history[tid]
        return is_danger_detected


class ScenarioEvaluator:
    def __init__(self, wiper_repeat_window: int):
        self.state = ScenarioState()
        self.wiper_repeat_window = wiper_repeat_window

    def evaluate(self, features: ChunkFeatures) -> Tuple[int, str]:
        blinker_used = features.left_signal_on or features.right_signal_on or features.blinker_audio
        if features.lane_change:
            self.state.last_lane_change_chunk = features.chunk_id
            self.state.last_lane_change_used_blinker = blinker_used
            self.state.blinker_still_on_chunks = 0
        scenario_id = 0
        
        # Priority order for event detection
        # 1. Event 10: Sudden stop with horn (급정거 위협운전)
        if features.horn and features.sudden_stop and not features.tailgating:
            scenario_id = 10
        # 2. Event 11: Tailgating with horn (꼬리물기 위협운전)
        elif features.horn and features.tailgating:
            scenario_id = 11
        # 3. Event 9: Horn with pedestrian (보행자 위협운전)
        elif features.horn and features.pedestrian_present:
            scenario_id = 9
        # 4. Event 8: Horn at crosswalk without pedestrian (우회전 보행자 없음)
        elif features.horn and features.crosswalk_sign_present and not features.pedestrian_present and features.right_signal_on:
            scenario_id = 8
        # 5. Event 5: Lane change without blinker (방향지시등 미점등 후 차선 변경)
        elif features.lane_change and not blinker_used:
            scenario_id = 5
        # 6. Event 4: Blinker stuck after lane change (차선 변경 후 방향지시등 끄지 않음)
        elif self._is_blinker_stuck(features):
            scenario_id = 4
        
        # 7. Wiper-related events (7, 11)
        scenario_id = self._evaluate_wiper(features, scenario_id)
        message = SCENARIO_MESSAGES.get(scenario_id, "정상 운행")
        return scenario_id, message

    def _is_blinker_stuck(self, features: ChunkFeatures) -> bool:
        lane_change_chunk = self.state.last_lane_change_chunk
        if lane_change_chunk is None or not self.state.last_lane_change_used_blinker:
            return False
        if features.chunk_id - lane_change_chunk > 2:
            self.state.blinker_still_on_chunks = 0
            return False
        if features.left_signal_on or features.right_signal_on or features.blinker_audio:
            self.state.blinker_still_on_chunks += 1
            return self.state.blinker_still_on_chunks >= 2
        self.state.blinker_still_on_chunks = 0
        return False

    def _evaluate_wiper(self, features: ChunkFeatures, current_id: int) -> int:
        """Evaluate wiper+hazard events (Event 7 and Event 11)"""
        wiper_event = features.wiper_audio and features.hazard_on
        if not wiper_event:
            return current_id
        last_chunk = self.state.last_wiper_hazard_chunk
        scenario_id = current_id
        # Event 11: Repeated wiper+hazard within window
        if last_chunk is not None and features.chunk_id - last_chunk <= self.wiper_repeat_window:
            scenario_id = scenario_id or 11
        # Event 7: First wiper+hazard detection
        else:
            scenario_id = scenario_id or 7
        self.state.last_wiper_hazard_chunk = features.chunk_id
        return scenario_id


def check_signal_status(hsv: np.ndarray, rect: Tuple[int, int, int, int]) -> bool:
    x, y, w, h = rect
    roi = hsv[y : y + h, x : x + w]
    if roi.size == 0:
        return False
    mask = cv2.inRange(roi, LOWER_SIGNAL, UPPER_SIGNAL)
    return cv2.countNonZero(mask) > SIGNAL_PIXEL_THRESHOLD


def perspective_distance(x: float, y: float) -> Tuple[float, float]:
    pts = cv2.perspectiveTransform(np.array([[[x, y]]], dtype=np.float32), H_MATRIX)
    bx, by = pts[0][0]
    dist_forward = round(max(0.0, (MY_CAR_BEV_Y - by) / PIXELS_PER_METER_Y), 2)
    dist_lat = round((bx - MY_CAR_BEV_X) / PIXELS_PER_METER_X, 2)
    return dist_forward, dist_lat


def overlay_text(
    frame: np.ndarray,
    scenario_text: str,
    audio_text: str,
    chunk_id: int,
    features: ChunkFeatures,
    status_color: Tuple[int, int, int],
) -> None:
    cv2.putText(frame, scenario_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    cv2.putText(frame, audio_text, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    lane_text = f"lane_change:{'Y' if features.lane_change else 'N'} offset:{features.lane_offset:.1f}"
    cv2.putText(frame, lane_text, (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    chunk_text = f"Chunk {chunk_id}"
    text_size, _ = cv2.getTextSize(chunk_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.putText(
        frame,
        chunk_text,
        (frame.shape[1] - text_size[0] - 20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2,
    )


class ScenarioEngine:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.device = torch.device(args.device)
        self.yolo = YOLO(str(args.yolo_model))
        self.audio_detector = AudioEventDetector(args.audio_model, self.device, AudioInferenceConfig())
        self.lane_monitor = LaneChangeMonitor(args.lane_model, self.device, LANE_IMAGE_SIZE, args.lane_change_threshold)
        self.scenario_evaluator = ScenarioEvaluator(args.wiper_repeat_window)
        self.ebs = EmergencyBrakingSystem(args.vehicle_classes)
        self.tailgating_frames = 0
        self.stop_sustain_frames = 0

    def process_video(self, video_path: Path) -> List[ChunkResult]:
        print(f"\n🎥 분석 시작: {video_path.name}")
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"비디오를 열 수 없습니다: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frames_per_chunk = max(1, int(fps * self.args.chunk_seconds))
        output_path = self.args.output_dir / f"{video_path.stem}{self.args.output_suffix}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps / (frames_per_chunk / max(1, min(frames_per_chunk, self.args.sampled_frames))),
            (width, height),
        )
        try:
            waveform, _ = librosa.load(str(video_path), sr=self.audio_detector.config.sr)
        except Exception:
            waveform = np.array([])
        chunk_id = 1
        results: List[ChunkResult] = []
        while True:
            frames = []
            for _ in range(frames_per_chunk):
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
            if not frames:
                break
            audio_chunk = self._slice_audio(waveform, chunk_id)
            audio_label, audio_score, _ = self.audio_detector.predict(audio_chunk)
            audio_text = "Audio: Normal"
            features = ChunkFeatures(chunk_id=chunk_id)
            if audio_label:
                audio_text = f"Audio: {audio_label} ({audio_score:.2f})"
                if audio_label == "horn" and audio_score >= self.args.audio_threshold:
                    features.horn = True
                if audio_label == "blinker" and audio_score >= self.args.audio_threshold:
                    features.blinker_audio = True
                if audio_label == "wiper" and audio_score >= self.args.audio_threshold:
                    features.wiper_audio = True
            lane_frame = frames[len(frames) // 2]
            lane_change, lane_offset = self.lane_monitor.process(lane_frame)
            features.lane_change = lane_change
            features.lane_offset = lane_offset
            sampled_frames = self._sample_frames(frames)
            chunk_l_counts = 0
            chunk_r_counts = 0
            chunk_stop_warning = False
            chunk_pedestrian = False
            chunk_crosswalk = False
            chunk_frames: List[np.ndarray] = []
            for vis_frame, res in zip(sampled_frames, self.yolo.track(sampled_frames, persist=True, conf=self.args.yolo_conf, iou=self.args.yolo_iou, device=self.args.device, verbose=False)):
                hsv = cv2.cvtColor(vis_frame, cv2.COLOR_BGR2HSV)
                if check_signal_status(hsv, self.args.left_signal_roi):
                    chunk_l_counts += 1
                if check_signal_status(hsv, self.args.right_signal_roi):
                    chunk_r_counts += 1
                current_objects: List[Dict[str, float]] = []
                frame_has_close_vehicle = False
                if res.boxes is not None:
                    boxes = res.boxes
                    for box in boxes:
                        cls_idx = int(box.cls[0])
                        name = res.names.get(cls_idx, "unknown")
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        tid = int(box.id[0]) if box.id is not None else -1
                        if name == self.args.pedestrian_class:
                            chunk_pedestrian = True
                        if name == self.args.crosswalk_class:
                            chunk_crosswalk = True
                        color = (0, 255, 0)
                        if name == self.args.pedestrian_class:
                            color = (0, 0, 255)
                        elif name not in self.args.vehicle_classes:
                            color = (255, 0, 255)
                        dist_forward, dist_lat = perspective_distance((x1 + x2) / 2, y2)
                        if name in self.args.vehicle_classes and dist_forward <= TAILGATING_DISTANCE_M:
                            frame_has_close_vehicle = True
                        if name in self.args.vehicle_classes:
                            current_objects.append(
                                {
                                    "class_name": name,
                                    "track_id": tid,
                                    "distance_forward_m": dist_forward,
                                    "distance_lateral_m": dist_lat,
                                }
                            )
                        cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
                        label = f"{name} {dist_forward:.1f}m"
                        cv2.putText(vis_frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                if frame_has_close_vehicle:
                    self.tailgating_frames += 1
                else:
                    self.tailgating_frames = max(0, self.tailgating_frames - 1)
                warning = self.ebs.check(current_objects)
                if warning:
                    self.stop_sustain_frames = max(self.stop_sustain_frames, 40)
                if self.stop_sustain_frames > 0:
                    warning = True
                    self.stop_sustain_frames -= 1
                chunk_stop_warning = chunk_stop_warning or warning
                chunk_frames.append(vis_frame)
            features.left_signal_on = chunk_l_counts >= self.args.signal_threshold
            features.right_signal_on = chunk_r_counts >= self.args.signal_threshold
            features.hazard_on = features.left_signal_on and features.right_signal_on
            features.sudden_stop = chunk_stop_warning
            features.tailgating = self.tailgating_frames >= self.args.tailgating_frames
            features.pedestrian_present = chunk_pedestrian
            features.crosswalk_sign_present = chunk_crosswalk
            scenario_id, scenario_text = self.scenario_evaluator.evaluate(features)
            status_color = (0, 0, 255) if scenario_id else (0, 255, 0)
            for frame in chunk_frames:
                overlay_text(frame, scenario_text, audio_text, chunk_id, features, status_color)
                writer.write(frame)
            results.append(ChunkResult(chunk_id, scenario_id, scenario_text, features, audio_text))
            print(
                f"Chunk {chunk_id:02d}: event={scenario_id} '{scenario_text}' | "
                f"horn={features.horn} ped={features.pedestrian_present} stop={features.sudden_stop} "
                f"lane_change={features.lane_change} hazard={features.hazard_on}"
            )
            chunk_id += 1
        writer.release()
        cap.release()
        print(f"✅ 결과 저장: {output_path}")
        return results

    def _slice_audio(self, waveform: np.ndarray, chunk_id: int) -> np.ndarray:
        if waveform.size == 0:
            return np.array([])
        sr = self.audio_detector.config.sr
        start = int((chunk_id - 1) * self.args.chunk_seconds * sr)
        end = int(chunk_id * self.args.chunk_seconds * sr)
        if start >= len(waveform):
            return np.array([])
        return waveform[start:end]

    def _sample_frames(self, frames: Sequence[np.ndarray]) -> List[np.ndarray]:
        if not frames:
            return []
        count = min(len(frames), self.args.sampled_frames)
        indices = np.linspace(0, len(frames) - 1, count, dtype=int)
        return [frames[i].copy() for i in indices]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="시나리오 기반 통합 분석 파이프라인")
    
    # Default videos to process (events 4, 5, 7, 8, 9, 10, 11)
    default_videos = [
        str(PROJECT_ROOT / "Data" / "이벤트 4.mp4"),
        str(PROJECT_ROOT / "Data" / "이벤트 5.mp4"),
        str(PROJECT_ROOT / "Data" / "이벤트 7.mp4"),
        str(PROJECT_ROOT / "Data" / "이벤트 8.mp4"),
        str(PROJECT_ROOT / "Data" / "이벤트 9.mp4"),
        str(PROJECT_ROOT / "Data" / "이벤트 10.mp4"),
        str(PROJECT_ROOT / "Data" / "이벤트 11.mp4"),
    ]
    
    parser.add_argument("--videos", nargs="+", default=default_videos, help="처리할 비디오 경로 목록")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "Outputs", help="결과 비디오 저장 경로")
    parser.add_argument("--yolo-model", type=Path, default=DEFAULT_YOLO_MODEL)
    parser.add_argument("--lane-model", type=Path, default=DEFAULT_LANE_MODEL)
    parser.add_argument("--audio-model", type=Path, default=DEFAULT_AUDIO_MODEL)
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--chunk-seconds", type=float, default=2.0)
    parser.add_argument("--sampled-frames", type=int, default=20)
    parser.add_argument("--audio-threshold", type=float, default=0.7)
    parser.add_argument("--lane-change-threshold", type=float, default=LANE_CHANGE_THRESHOLD_PX)
    parser.add_argument("--signal-threshold", type=int, default=3)
    parser.add_argument("--tailgating-frames", type=int, default=7)
    parser.add_argument("--wiper-repeat-window", type=int, default=3)
    parser.add_argument("--yolo-conf", type=float, default=0.2)
    parser.add_argument("--yolo-iou", type=float, default=0.5)
    parser.add_argument("--left-signal-roi", type=int, nargs=4, default=(170, 390, 25, 25))
    parser.add_argument("--right-signal-roi", type=int, nargs=4, default=(240, 390, 25, 25))
    parser.add_argument("--crosswalk-class", type=str, default=CROSSWALK_SIGN_CLASS)
    parser.add_argument("--pedestrian-class", type=str, default=PEDESTRIAN_CLASS)
    parser.add_argument("--vehicle-classes", nargs="+", default=VEHICLE_CLASSES_DEFAULT)
    parser.add_argument("--output-suffix", type=str, default="_annotated.mp4")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.left_signal_roi = tuple(int(v) for v in args.left_signal_roi)
    args.right_signal_roi = tuple(int(v) for v in args.right_signal_roi)
    args.pedestrian_class = args.pedestrian_class or PEDESTRIAN_CLASS
    args.crosswalk_class = args.crosswalk_class or CROSSWALK_SIGN_CLASS
    args.vehicle_classes = [v.strip() for v in args.vehicle_classes]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    engine = ScenarioEngine(args)
    for video in args.videos:
        engine.process_video(Path(video).expanduser())


if __name__ == "__main__":
    main()