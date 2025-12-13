# 🤖 DrivingCoach AI 모델 (Python)

> YOLO, U-Net, CNN 기반 운전 상황 분석 엔진

## 📋 개요

이 모듈은 블랙박스 영상을 분석하여 위험 운전 행동을 자동으로 감지하는 AI 파이프라인입니다.

**주요 기능**:
- 🎥 **YOLO**: 보행자, 차량, 표지판 인식
- 🛣️ **U-Net**: 차선 감지 및 변경 추적
- 🔊 **AudioCNN**: 경적, 깜박이, 와이퍼 소리 분류
- ⚠️ **시나리오 엔진**: 11가지 위험 운전 감지

## ⚡ 빠른 시작

### 필수 요구사항
- **Python 3.8 이상**
- **PyTorch 1.10+**
- **(선택) CUDA** (GPU 가속)

### 설치

#### 1️⃣ Python 가상환경 생성
```bash
cd model
python -m venv venv

# 활성화 (Mac/Linux)
source venv/bin/activate

# 활성화 (Windows)
venv\Scripts\activate
```

#### 2️⃣ 의존성 설치
```bash
pip install torch torchvision ultralytics librosa opencv-python numpy
```

또는 `requirements.txt` 사용:
```bash
pip install -r requirements.txt
```

#### 3️⃣ 모델 파일 확인
`models/` 폴더에 다음 파일이 있어야 합니다:
- `YOLO.pt` (객체 인식 모델)
- `lane_detect.pt` (차선 인식 모델)
- `AudioCNN.pt` (음성 분류 모델)

### 실행

#### 기본 실행 (전체 이벤트)
```bash
python src/main.py
```

#### 특정 비디오 분석
```bash
python src/main.py --videos Data/이벤트\ 4.mp4 Data/이벤트\ 5.mp4
```

#### CPU 모드 (GPU 없을 때)
```bash
python src/main.py --device cpu
```

## 📁 프로젝트 구조

```
model/
├── src/                        # 소스 코드
│   ├── main.py                # 메인 실행 파일 ⭐
│   ├── AudioCNN.py            # 음성 분석 모델
│   ├── lane_detect.py         # 차선 인식 모델
│   ├── yolo.py                # YOLO 래퍼
│   ├── algorithm_yolo.py      # YOLO 알고리즘 (참고용)
│   └── algorithm_lane.py      # 차선 알고리즘 (참고용)
│
├── models/                     # 학습된 모델 가중치
│   ├── YOLO.pt
│   ├── lane_detect.pt
│   └── AudioCNN.pt
│
├── Data/                       # 입력 비디오
│   ├── 이벤트 4.mp4
│   ├── 이벤트 5.mp4
│   ├── 이벤트 7.mp4
│   ├── 이벤트 8.mp4
│   ├── 이벤트 9.mp4
│   ├── 이벤트 10.mp4
│   └── 이벤트 11.mp4
│
├── Outputs/                    # 분석 결과 비디오
│   ├── 이벤트 4_annotated.mp4
│   └── ...
│
└── find_lane/                  # 차선 감지 실험 코드
```

## 🎯 감지 시나리오

| ID | 시나리오 | 감지 로직 |
|---|---|---|
| **4** | 차선 변경 후 깜박이 미해제 | 차선 변경 + 방향지시등 2초 이상 유지 |
| **5** | 깜박이 없이 차선 변경 | 차선 변경 감지 + 방향지시등 미작동 |
| **7** | 악천후 전조등 권장 | 와이퍼 + 비상등 동시 감지 |
| **8** | 우회전 보행자 구간 경적 | 횡단보도 표지판 + 경적 (보행자 없음) |
| **9** | 보행자 위협 운전 | 보행자 감지 + 경적 |
| **10** | 급정거 위협 운전 | 급정거 감지 + 경적 |
| **11** | 비상등 남용 | 와이퍼+비상등 반복 (3청크 이내) |

## 🔧 주요 파라미터

### main.py 실행 옵션

```bash
python src/main.py \
  --videos Data/이벤트\ 4.mp4 \
  --output-dir Outputs \
  --device cuda \
  --chunk-seconds 2.0 \
  --audio-threshold 0.7 \
  --lane-change-threshold 40.0
```

| 파라미터 | 설명 | 기본값 |
|---|---|---|
| `--videos` | 분석할 비디오 경로 | 전체 이벤트 |
| `--output-dir` | 결과 저장 경로 | `Outputs/` |
| `--device` | 디바이스 (cuda/cpu) | cuda (가능 시) |
| `--chunk-seconds` | 청크 길이 (초) | 2.0 |
| `--sampled-frames` | 청크당 샘플링 프레임 수 | 20 |
| `--audio-threshold` | 음성 감지 임계값 | 0.7 |
| `--lane-change-threshold` | 차선 변경 임계값 (픽셀) | 40.0 |
| `--yolo-conf` | YOLO 신뢰도 임계값 | 0.2 |

## 📊 분석 프로세스

### 1. 비디오 청크 분할
- 2초 단위로 영상 분할
- 각 청크마다 독립적으로 분석

### 2. 객체 인식 (YOLO)
```python
results = yolo.track(frames, persist=True, conf=0.2)
# 보행자, 차량, 표지판 감지
```

### 3. 차선 감지 (U-Net)
```python
lane_change, offset = lane_monitor.process(frame)
# 차선 중심 추적 및 변경 감지
```

### 4. 음성 분석 (AudioCNN)
```python
audio_label, score = audio_detector.predict(audio_chunk)
# horn, blinker, wiper 분류
```

### 5. 시나리오 판별
```python
scenario_id, message = scenario_evaluator.evaluate(features)
# 종합 분석 후 시나리오 ID 반환
```

### 6. 결과 오버레이
- 감지된 객체 바운딩 박스
- 시나리오 메시지 텍스트
- 차선 변경 상태
- 오디오 분류 결과

## 🧪 테스트 실행

### 단일 이벤트 테스트
```bash
# 이벤트 4: 차선 변경 후 깜박이 미해제
python src/main.py --videos Data/이벤트\ 4.mp4

# 결과: Outputs/이벤트 4_annotated.mp4
```

### 전체 이벤트 일괄 처리
```bash
python src/main.py
# 7개 이벤트 모두 분석
```

### 디버그 모드
```python
# main.py 실행 중 출력 예시
Chunk 01: event=0 '정상 운행' | horn=False ped=False stop=False
Chunk 02: event=5 '방향지시등 없이 차선을 변경했습니다.' | horn=False ped=False stop=False
```

## 📈 성능 최적화

### GPU 가속 (권장)
```bash
# CUDA 사용 가능 확인
python -c "import torch; print(torch.cuda.is_available())"

# GPU 메모리 사용량 확인
nvidia-smi
```

### 배치 처리
- YOLO tracking: `batch_size` 조정 가능
- 청크당 프레임 수 줄이기: `--sampled-frames 10`

### 메모리 관리
```python
# 대용량 비디오 처리 시
# chunk-seconds를 작게 설정 (1.0초)
python src/main.py --chunk-seconds 1.0
```

## 🔍 출력 결과 분석

### 콘솔 출력
```
🎥 분석 시작: 이벤트 4.mp4
Chunk 01: event=0 '정상 운행' | horn=False ped=False stop=False lane_change=False
Chunk 05: event=4 '차선 변경 후 방향지시등을 끄지 않았습니다.' | horn=False ped=False stop=False lane_change=True
✅ 결과 저장: Outputs/이벤트 4_annotated.mp4
```

### 저장된 비디오
- 원본 프레임에 분석 결과 오버레이
- 빨간색 텍스트: 위험 시나리오 감지
- 초록색 텍스트: 정상 운행
- 바운딩 박스:
  - 🟢 초록: 일반 객체
  - 🔴 빨강: 보행자
  - 🟣 보라: 기타 객체

## ⚠️ 문제 해결

### 1. CUDA 오류
```bash
# CPU 모드로 전환
python src/main.py --device cpu
```

### 2. 모델 파일 없음
```
FileNotFoundError: models/YOLO.pt not found
```
**해결**: `models/` 폴더에 `.pt` 파일 배치 필요

### 3. 메모리 부족
```bash
# 청크 크기 줄이기
python src/main.py --chunk-seconds 1.0 --sampled-frames 10
```

### 4. 비디오 코덱 오류
```bash
# OpenCV 재설치
pip uninstall opencv-python
pip install opencv-python-headless
```

### 5. librosa 설치 오류 (Mac M1/M2)
```bash
# Conda 사용 권장
conda install -c conda-forge librosa
```

## 🚀 고급 사용법

### 커스텀 시나리오 추가
`src/main.py`의 `SCENARIO_MESSAGES` 딕셔너리 수정:
```python
SCENARIO_MESSAGES = {
    4: "차선 변경 후 방향지시등을 끄지 않았습니다.",
    5: "방향지시등 없이 차선을 변경했습니다.",
    # ... 기존 시나리오
    12: "새로운 시나리오",  # 추가
}
```

### ROI (관심 영역) 조정
깜박이 감지 영역 변경:
```bash
python src/main.py \
  --left-signal-roi 170 390 25 25 \
  --right-signal-roi 240 390 25 25
```

### 차선 감지 민감도 조절
```bash
# 더 민감하게 (작은 변화도 감지)
python src/main.py --lane-change-threshold 20.0

# 덜 민감하게 (큰 변화만 감지)
python src/main.py --lane-change-threshold 60.0
```

## 📦 의존성 상세

```txt
torch>=1.10.0
torchvision>=0.11.0
ultralytics>=8.0.0  # YOLO
librosa>=0.9.0      # 음성 분석
opencv-python>=4.5.0
numpy>=1.21.0
```

## 🎓 교수님/평가자를 위한 가이드

### 빠른 데모
```bash
# 1. 가상환경 활성화
source venv/bin/activate  # 또는 venv\Scripts\activate

# 2. 단일 이벤트 실행
python src/main.py --videos Data/이벤트\ 4.mp4 --device cpu

# 3. 결과 확인
# Outputs/이벤트 4_annotated.mp4 재생
```

### 예상 실행 시간
- **CPU 모드**: 이벤트 1개당 ~5-10분
- **GPU 모드**: 이벤트 1개당 ~1-2분

### 결과 해석
- **빨간색 메시지**: 위험 운전 감지
- **청크 번호**: 2초 단위 구간
- **Audio 텍스트**: 감지된 소리 종류

## 🔗 참고 자료

- [Ultralytics YOLO](https://docs.ultralytics.com/)
- [PyTorch 공식 문서](https://pytorch.org/docs/)
- [librosa 가이드](https://librosa.org/doc/latest/)

---

**🔙 [메인 README로 돌아가기](../README.md)**
