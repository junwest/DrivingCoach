import cv2
import numpy as np
import torch
import torch.nn as nn
import librosa
import os
from ultralytics import YOLO
from typing import List, Dict, Tuple
from google.colab import drive
from IPython.display import HTML, display
from base64 import b64encode
import subprocess

# ---------------------------------------------------------------------------
# 1. ⚙️ [설정]
# ---------------------------------------------------------------------------
print("🚀 청크별 테스트 환경 초기화 중...")

try:
    drive.mount('/content/drive')
except:
    pass

# 경로 설정
PT_MODEL_PATH = "/content/drive/MyDrive/Capstone/지호/YOLO_RESULTS2/Final_Training_Run2/weights/best2.pt"
AUDIO_MODEL_PATH = "/content/drive/MyDrive/Capstone/음성모델/another.pth"

# ---------------------------------------------------------------------------
# 2. 🧠 Audio Logic
# ---------------------------------------------------------------------------

class Config:
    sr = 16000
    n_mels = 64
    n_fft = 1024
    hop_length = 256
    duration = 1.0

CLASS_NAMES = ['blinker', 'horn', 'normal']

class AudioCNN(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1), nn.BatchNorm2d(32), nn.LeakyReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1), nn.BatchNorm2d(64), nn.LeakyReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1), nn.BatchNorm2d(128), nn.LeakyReLU(), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Dropout(0.2), nn.Linear(128, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))

def predict_chunk(model: AudioCNN, audio_chunk: np.ndarray, config: Config, device: str) -> Tuple[str, float, torch.Tensor]:
    target_len = int(config.sr * config.duration)
    if len(audio_chunk) < target_len:
        audio_chunk = np.pad(audio_chunk, (0, target_len - len(audio_chunk)))
    else:
        audio_chunk = audio_chunk[:target_len]

    mel_spec = librosa.feature.melspectrogram(
        y=audio_chunk,
        sr=config.sr,
        n_fft=config.n_fft,
        hop_length=config.hop_length,
        n_mels=config.n_mels
    )
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    mel_spec_db = (mel_spec_db - mel_spec_db.mean()) / (mel_spec_db.std() + 1e-6)

    tensor = torch.tensor(mel_spec_db, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        score, pred_idx = torch.max(probs, dim=1)

    return CLASS_NAMES[pred_idx.item()], score.item(), probs.squeeze(0).cpu()

# ---------------------------------------------------------------------------
# 3. 🚗 영상 분석 설정
# ---------------------------------------------------------------------------

VEHICLE_CLASSES = ['car', 'truck', 'bus', 'motorcycle']
PEDESTRIAN_CLASS = 'pedestrian'
VEHICLE_LIGHT_CLASS = 'horizontal traffic sign'
PED_LIGHT_CLASS = 'crosswalk sign'

# EBS & BEV Config
LANE_WIDTH_THRESHOLD = 1.8
EMERGENCY_DIST_THRESHOLD = 0.0
H_MATRIX = np.array([[-3.97727273e-02, -3.24810606e-01,  1.00492424e+02],
                      [ 4.37257068e-16, -2.54829545e-00,  7.89971591e+02],
                      [ 1.16574774e-18, -3.69318182e-03,  1.00000000e+00]])
PIXELS_PER_METER_Y = 20.0
PIXELS_PER_METER_X = 20.0
MY_CAR_BEV_X = 105
MY_CAR_BEV_Y = 400
CALIBRATION_Y_FAR = 310.0
DST_HEIGHT = 300

# Color & Signal Config
L_ROI_RECT = (170, 390, 25, 25)
R_ROI_RECT = (240, 390, 25, 25)
MASK_RANGE_RED = (
    (np.array([0, 100, 100]), np.array([10, 255, 255])),
    (np.array([170, 100, 100]), np.array([180, 255, 255]))
)
MASK_RANGE_YELLOW = ((np.array([20, 100, 100]), np.array([30, 255, 255])),)
MASK_RANGE_GREEN = ((np.array([40, 100, 100]), np.array([90, 255, 255])),)
LOWER_GREEN_SIGNAL = np.array([35, 80, 80])
UPPER_GREEN_SIGNAL = np.array([100, 255, 255])
PIXEL_THRESHOLD_SIGNAL = 10

class EmergencyBrakingSystem:
    def __init__(self):
        self.history = {}
        self.last_warning = {}
        self.frame_counter = 0

    def check(self, current_objects: List[Dict]) -> bool:
        self.frame_counter += 1
        is_danger_detected = False
        present_ids = set()

        for obj in current_objects:
            if obj['class_name'] not in VEHICLE_CLASSES:
                continue
            if abs(obj['distance_lateral_m']) < LANE_WIDTH_THRESHOLD:
                tid = obj['track_id']
                dist = obj['distance_forward_m']
                present_ids.add(tid)

                if tid not in self.history:
                    self.history[tid] = []
                self.history[tid].append((self.frame_counter, dist))
                self.history[tid] = [h for h in self.history[tid] if self.frame_counter - h[0] <= 15]

                if len(self.history[tid]) >= 10:
                    curr_dist = dist
                    mid_dist = self.history[tid][-5][1]
                    old_dist = self.history[tid][-10][1]
                    velocity_recent = mid_dist - curr_dist

                    if (velocity_recent >= 2.0 and velocity_recent > (0.0 * 1.5)) or (velocity_recent >= 2.5):
                        if dist < EMERGENCY_DIST_THRESHOLD:
                            last_warn = self.last_warning.get(tid, -999)
                            if self.frame_counter - last_warn > 20:
                                is_danger_detected = True
                                self.last_warning[tid] = self.frame_counter

        for tid in list(self.history.keys()):
            if tid not in present_ids:
                del self.history[tid]
        return is_danger_detected

def find_traffic_light_color(roi):
    if roi.size == 0:
        return "UNKNOWN"
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    masks = {
        "R": cv2.inRange(hsv_roi, MASK_RANGE_RED[0][0], MASK_RANGE_RED[0][1]) +
             cv2.inRange(hsv_roi, MASK_RANGE_RED[1][0], MASK_RANGE_RED[1][1]),
        "Y": cv2.inRange(hsv_roi, MASK_RANGE_YELLOW[0][0], MASK_RANGE_YELLOW[0][1]),
        "G": cv2.inRange(hsv_roi, MASK_RANGE_GREEN[0][0], MASK_RANGE_GREEN[0][1])
    }

    detected_color = "UNKNOWN"
    max_area = 0
    for c, m in masks.items():
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for ct in cnts:
            area = cv2.contourArea(ct)
            if area > 10:
                if c == "G":
                    hull = cv2.convexHull(ct)
                    if cv2.contourArea(hull) == 0:
                        continue
                    current_color = "GL" if (area / cv2.contourArea(hull)) < 0.85 else "GC"
                else:
                    current_color = c
                if area > max_area:
                    max_area = area
                    detected_color = current_color
    return detected_color

def check_signal_status(hsv, rect):
    x, y, w, h = rect
    roi = hsv[y:y+h, x:x+w]
    if roi.size == 0:
        return "OFF"
    return "ON" if cv2.countNonZero(cv2.inRange(roi, LOWER_GREEN_SIGNAL, UPPER_GREEN_SIGNAL)) > PIXEL_THRESHOLD_SIGNAL else "OFF"

def show_video_in_colab(video_path):
    output_mp4 = video_path.replace('.avi', '_converted.mp4')
    subprocess.call(['ffmpeg', '-y', '-i', video_path, '-vcodec', 'libx264', output_mp4])
    mp4 = open(output_mp4, 'rb').read()
    data_url = "data:video/mp4;base64," + b64encode(mp4).decode()
    return HTML(f"""<video width=640 controls><source src="{data_url}" type="video/mp4"></video>""")

# ---------------------------------------------------------------------------
# 4. 🎬 실행 및 분석 로직
# ---------------------------------------------------------------------------

device = 'cuda' if torch.cuda.is_available() else 'cpu'
config = Config()

try:
    yolo_model = YOLO(PT_MODEL_PATH)
    audio_model = AudioCNN(len(CLASS_NAMES)).to(device)
    audio_model.load_state_dict(torch.load(AUDIO_MODEL_PATH, map_location=device), strict=False)
    audio_model.eval()
    print(f"✅ 모델 로드 완료 ({device})")
except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")

def test_video_by_chunks(file_path: str):
    filename = os.path.basename(file_path)
    print(f"\n🎥 [분석 시작] {filename}")

    if not os.path.exists(file_path):
        print("❌ 파일 없음")
        return

    output_path = f"/content/result_{filename.split('.')[0]}.avi"
    cap = cv2.VideoCapture(file_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*'MJPG'),
        10,
        (width, height)
    )

    try:
        y_full, sr = librosa.load(file_path, sr=config.sr)
    except:
        y_full = []
        sr = config.sr

    CHUNK_DURATION_SEC = 2.0
    frames_per_chunk = int(fps * CHUNK_DURATION_SEC)
    chunk_id = 1
    stop_sustain_frames = 0

    # 꼬리물기 프레임 카운터
    tailgating_frame_counter = 0

    # lane departed 는 항상 NA
    lane_departed_text = "NA"

    while True:
        frames = []
        for _ in range(frames_per_chunk):
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        if not frames:
            break

        # --- A. Audio Logic ---
        start_sample = int((chunk_id - 1) * CHUNK_DURATION_SEC * sr)
        end_sample = int(chunk_id * CHUNK_DURATION_SEC * sr)
        is_horn_detected = False
        audio_event_vis = "Audio: Normal"
        audio_log_str = "normal"

        if len(y_full) > start_sample:
            audio_chunk = y_full[start_sample:end_sample]
            if len(audio_chunk) > 0:
                pred_label, pred_score, probs = predict_chunk(audio_model, audio_chunk, config, device)
                if pred_label == 'horn' and pred_score > 0.7:
                    is_horn_detected = True
                    audio_event_vis = f"Audio: HORN ({pred_score:.2f})"
                    audio_log_str = f"Horn({pred_score:.2f})"
                elif pred_label == 'blinker' and pred_score > 0.7:
                    audio_event_vis = f"Audio: BLINKER ({pred_score:.2f})"
                    audio_log_str = f"Blinker({pred_score:.2f})"

        # --- B. Video Analysis ---
        indices = np.linspace(0, len(frames)-1, 20, dtype=int)
        sampled = [frames[i] for i in indices]

        results = yolo_model.track(sampled, persist=True, conf=0.15, augment=False, verbose=False, device=device)
        ebs = EmergencyBrakingSystem()

        is_sudden_stop = False
        is_pedestrian_in_chunk = False
        is_crosswalk_sign_in_chunk = False
        is_signal_violation_in_chunk = False

        is_tailgating_confirmed = False

        chunk_l_signal_counts = 0
        chunk_r_signal_counts = 0

        for idx, res in enumerate(results):
            vis_frame = sampled[idx].copy()
            curr_hsv = cv2.cvtColor(vis_frame, cv2.COLOR_BGR2HSV)

            l_stat = check_signal_status(curr_hsv, L_ROI_RECT)
            r_stat = check_signal_status(curr_hsv, R_ROI_RECT)
            if l_stat == "ON":
                chunk_l_signal_counts += 1
            if r_stat == "ON":
                chunk_r_signal_counts += 1

            cv2.rectangle(
                vis_frame,
                (L_ROI_RECT[0], L_ROI_RECT[1]),
                (L_ROI_RECT[0]+L_ROI_RECT[2], L_ROI_RECT[1]+L_ROI_RECT[3]),
                (0, 255, 0) if l_stat=="ON" else (100,100,100),
                2
            )
            cv2.rectangle(
                vis_frame,
                (R_ROI_RECT[0], R_ROI_RECT[1]),
                (R_ROI_RECT[0]+R_ROI_RECT[2], R_ROI_RECT[1]+R_ROI_RECT[3]),
                (0, 255, 0) if r_stat=="ON" else (100,100,100),
                2
            )

            current_objects = []
            frame_has_close_vehicle = False

            if res.boxes is not None and res.boxes.id is not None:
                boxes = res.boxes.cpu().numpy()
                for box in boxes:
                    cls = int(box.cls[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    tid = int(box.id[0])
                    name = res.names.get(cls, "Unknown")

                    if name == PEDESTRIAN_CLASS:
                        is_pedestrian_in_chunk = True
                    if name == PED_LIGHT_CLASS:
                        is_crosswalk_sign_in_chunk = True

                    t_color_text = ""
                    t_color = "UNKNOWN"
                    if name == VEHICLE_LIGHT_CLASS:
                        light_roi = vis_frame[y1:y2, x1:x2]
                        t_color = find_traffic_light_color(light_roi)
                        if t_color != "UNKNOWN":
                            t_color_text = f" [{t_color}]"

                    if name != PEDESTRIAN_CLASS and y2 > 525:
                        continue

                    bcx = (x1+x2)/2
                    obj = {"class_name": name, "track_id": tid}

                    dist_fwd = 0.0
                    if name == VEHICLE_LIGHT_CLASS:
                        pts = cv2.perspectiveTransform(
                            np.array([[[bcx, CALIBRATION_Y_FAR]]], dtype=np.float32),
                            H_MATRIX
                        )
                        by = int(
                            np.interp(
                                np.clip(y1,0,CALIBRATION_Y_FAR),
                                [0,CALIBRATION_Y_FAR],
                                [DST_HEIGHT-1,0]
                            )
                        )
                        dist_fwd = round((MY_CAR_BEV_Y - by) / PIXELS_PER_METER_Y, 2)
                        if t_color == 'R' and dist_fwd <= 5.0:
                            is_signal_violation_in_chunk = True
                            cv2.putText(
                                vis_frame,
                                "SIGNAL VIOLATION!",
                                (x1, y1-30),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 0, 255),
                                2
                            )
                    else:
                        pts = cv2.perspectiveTransform(
                            np.array([[[bcx, y2]]], dtype=np.float32),
                            H_MATRIX
                        )
                        by = int(pts[0][0][1])
                        if by < 0:
                            by = 0
                        dist_fwd = round((MY_CAR_BEV_Y - by) / PIXELS_PER_METER_Y, 2)
                        if dist_fwd < 0:
                            dist_fwd = 0.0

                    # 꼬리물기 체크 (3m 이하 감지)
                    if name in VEHICLE_CLASSES and dist_fwd <= 3.0:
                        frame_has_close_vehicle = True

                    obj['distance_forward_m'] = dist_fwd
                    obj['distance_lateral_m'] = round(
                        (pts[0][0][0] - MY_CAR_BEV_X) / PIXELS_PER_METER_X,
                        2
                    )
                    current_objects.append(obj)

                    color = (0, 255, 255)
                    if name == VEHICLE_LIGHT_CLASS:
                        color = (255, 0, 255)
                    elif name == PEDESTRIAN_CLASS:
                        color = (0, 0, 255)

                    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{tid} {name} {dist_fwd}m{t_color_text}"
                    cv2.putText(
                        vis_frame,
                        label,
                        (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2
                    )

            # 꼬리물기 연속 감지 카운트
            if frame_has_close_vehicle:
                tailgating_frame_counter += 1
            else:
                tailgating_frame_counter = 0

            is_tailgating_now = (tailgating_frame_counter >= 30)
            if is_tailgating_now:
                is_tailgating_confirmed = True

            chunk_stop_warning = ebs.check(current_objects)
            if chunk_stop_warning:
                stop_sustain_frames = 40
            if stop_sustain_frames > 0:
                chunk_stop_warning = True
                is_sudden_stop = True
                stop_sustain_frames -= 1

            # [Overlay Logic]
            if chunk_stop_warning:
                status_color = (0, 0, 255)  # RED
                ebs_text = "WARNING: RECKLESS DRIVING!!"
            elif is_horn_detected and is_tailgating_now:
                status_color = (0, 0, 255)  # RED
                ebs_text = "WARNING: TAILGATING!"
            elif is_horn_detected and is_pedestrian_in_chunk:
                status_color = (0, 0, 255)  # RED
                ebs_text = "WARNING: PEDESTRIAN THREAT!!"
            elif is_horn_detected and is_crosswalk_sign_in_chunk and not is_pedestrian_in_chunk and (chunk_r_signal_counts > 0 or r_stat == "ON"):
                status_color = (0, 0, 255)  # RED (요청하신 색상)
                ebs_text = "WARNING: YOU CAN GO RIGHT"
            else:
                status_color = (0, 255, 0)  # GREEN
                ebs_text = "Driving: Normal"

            # ---------- HUD ----------
            # 1줄: EBS 상태
            cv2.putText(
                vis_frame, ebs_text,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                status_color,
                2
            )
            # 2줄: Audio
            cv2.putText(
                vis_frame, audio_event_vis,
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 0),
                2
            )
            # 3줄: Lane departed (항상 N, 초록색)
            cv2.putText(
            vis_frame, "lane_departed: N",  # 텍스트를 고정된 문자열로 변경
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),  # 색상을 흰색(255,255,255)에서 초록색(0,255,0)으로 변경 (BGR 방식)
            2
            )
            # 4줄: Chunk ID
            # 텍스트 크기를 계산해서 오른쪽 끝에 맞춤
            chunk_text = f"Chunk: {chunk_id}"
            text_size, _ = cv2.getTextSize(chunk_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            text_w = text_size[0]

            # (전체너비 - 글자너비 - 20) 위치에 표시
            cv2.putText(vis_frame, chunk_text, (width - text_w - 20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            out_writer.write(vis_frame)

        # --- C. Summary ---
        final_l_signal = "ON" if chunk_l_signal_counts >= 3 else "OFF"
        final_r_signal = "ON" if chunk_r_signal_counts >= 3 else "OFF"

        event_id = 0
        desc = "정상"

        if is_signal_violation_in_chunk:
            event_id = 1; desc = "신호위반"
        elif is_horn_detected and is_sudden_stop:
            event_id = 4; desc = "차선 변경 방향지시등 미점등"
        elif is_horn_detected and is_tailgating_confirmed:
            event_id = 5; desc = "방향지시등 미점등 차선 변경"
        elif is_horn_detected and is_pedestrian_in_chunk:
            event_id = 7; desc = "잘못된 비상깜빡이 오류(우천 시 안개등이 아니라 비상깜빡이 점등)"
        elif is_horn_detected and is_sudden_stop:
            event_id = 10; desc = "위협운전"
        elif is_horn_detected and is_tailgating_confirmed:
            event_id = 11; desc = "꼬리물기+경적"
        elif is_horn_detected and is_pedestrian_in_chunk:
            event_id = 9; desc = "보행자 위협(경적)"
        elif is_horn_detected and is_crosswalk_sign_in_chunk and not is_pedestrian_in_chunk and final_r_signal == "ON":
            event_id = 8; desc = "보행자신호 위협(보행자X)"

        print(
            f"Chunk {chunk_id}: Event {event_id} ({desc}) | "
            f"Audio: {audio_log_str}, Stop: {is_sudden_stop}, "
            f"Tail Frames: {tailgating_frame_counter}, "
            f"Dash: L:{final_l_signal} R:{final_r_signal}, "
            f"Lane:{lane_departed_text}"
        )
        chunk_id += 1

    cap.release()
    out_writer.release()
    print("✅ 분석 및 영상 저장 종료")
    display(show_video_in_colab(output_path))

# ---------------------------------------------------------------------------
# 5. 🏃 실행부
# ---------------------------------------------------------------------------

TEST_FILES = [
    '/content/drive/MyDrive/Capstone/최종시연 540/이벤트 11.mp4',
]

for f in TEST_FILES:
    test_video_by_chunks(f)