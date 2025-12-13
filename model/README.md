# 🤖 DrivingCoach AI Server

> Flask API 서버로 AI 모델을 서빙하고 ngrok로 외부 접근 제공

## 📋 개요

DrivingCoach AI 모델을 REST API로 제공하는 서버입니다. 모바일 앱에서 이미지, 오디오를 전송하면 AI 분석 결과를 반환합니다.

**주요 기능**:
- 🎥 **이미지 분석**: YOLO 객체 인식 + 차선 감지
- 🔊 **음성 분석**: 경적, 깜박이, 와이퍼 소리 분류
- ⚠️ **시나리오 판별**: 위험 운전 상황 감지
- 🌐 **ngrok 통합**: 외부에서 접근 가능한 Public URL 자동 생성

## ⚡ 빠른 시작

> 📘 **처음 사용하시나요?** 자세한 단계별 가이드는 [**SETUP_GUIDE.md**](./SETUP_GUIDE.md)를 참고하세요!

### 필수 요구사항
- **Python 3.8+**
- **ngrok** 계정 및 설치 (https://ngrok.com)

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
pip install -r requirements.txt
```

#### 3️⃣ ngrok 설치 및 인증
```bash
# Mac (Homebrew)
brew install ngrok

# Windows/Linux
# https://ngrok.com/download 에서 다운로드

# ngrok 인증 (무료 계정 생성 후)
ngrok authtoken YOUR_AUTH_TOKEN
```

#### 4️⃣ 모델 파일 확인
`models/` 폴더에 다음 파일이 있어야 합니다:
- `YOLO.pt`
- `lane_detect.pt`
- `AudioCNN.pt`

### 서버 실행

#### 방법 1: ngrok 자동 실행 (권장)
```bash
python start_server.py
```

출력 예시:
```
============================================================
🚗 DrivingCoach AI Server with ngrok
============================================================

1️⃣ Starting Flask server...
2️⃣ Starting ngrok tunnel...

✅ Server is running!
============================================================
📍 Local URL:  http://localhost:5000
🌐 Public URL: https://abc123.ngrok.io
============================================================

📱 Use the Public URL in your mobile app!

API Endpoints:
  GET  https://abc123.ngrok.io/
  POST https://abc123.ngrok.io/api/analyze/image
  POST https://abc123.ngrok.io/api/analyze/audio
  POST https://abc123.ngrok.io/api/analyze/scenario
```

#### 방법 2: Flask만 실행 (로컬 테스트)
```bash
python src/server.py
```

## 🗂️ 프로젝트 구조

```
model/
├── src/
│   ├── server.py              # Flask API 서버 ⭐
│   ├── AudioCNN.py            # 음성 분석 모델
│   ├── lane_detect.py         # 차선 인식 모델
│   └── yolo.py                # YOLO 래퍼
│
├── models/                    # 학습된 모델 가중치
│   ├── YOLO.pt
│   ├── lane_detect.pt
│   └── AudioCNN.pt
│
├── Data/                      # (선택) 테스트용 비디오
├── start_server.py            # ngrok 자동 실행 스크립트 ⭐
└── requirements.txt           # Python 의존성
```

## 📡 API 엔드포인트

### 1. Health Check
```http
GET /
```

**응답**:
```json
{
  "service": "DrivingCoach AI Server",
  "status": "running",
  "device": "cuda",
  "models": {
    "yolo": true,
    "lane": true,
    "audio": true
  }
}
```

### 2. 이미지 분석 (객체 인식 + 차선 감지)
```http
POST /api/analyze/image
Content-Type: application/json

{
  "image": "base64_encoded_image"
}
```

**응답**:
```json
{
  "success": true,
  "results": {
    "objects": [
      {
        "class": "pedestrian",
        "confidence": 0.94,
        "bbox": [120, 200, 180, 350]
      }
    ],
    "lane": {
      "detected": true,
      "center": 128.5,
      "offset": 2.5
    }
  }
}
```

### 3. 음성 분석
```http
POST /api/analyze/audio
Content-Type: application/json

{
  "audio": "base64_encoded_wav",
  "sample_rate": 16000
}
```

**응답**:
```json
{
  "success": true,
  "results": {
    "label": "horn",
    "confidence": 0.87,
    "all_predictions": {
      "horn": 0.87,
      "blinker": 0.08,
      "wiper": 0.05
    }
  }
}
```

### 4. 시나리오 판별
```http
POST /api/analyze/scenario
Content-Type: application/json

{
  "features": {
    "horn": true,
    "pedestrian": true,
    "lane_change": false,
    "blinker": false
  }
}
```

**응답**:
```json
{
  "success": true,
  "scenario": {
    "id": 9,
    "message": "보행자 근처에서 경적이 울렸습니다."
  }
}
```

## 🧪 API 테스트

### cURL 테스트
```bash
# Health check
curl http://localhost:5000/

# 이미지 분석 (base64 인코딩 필요)
curl -X POST http://localhost:5000/api/analyze/image \
  -H "Content-Type: application/json" \
  -d '{"image": "YOUR_BASE64_IMAGE"}'
```

### Python 테스트
```python
import requests
import base64

# 이미지 인코딩
with open("test.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

# API 호출
response = requests.post(
    "http://localhost:5000/api/analyze/image",
    json={"image": img_base64}
)

print(response.json())
```

## 🌐 ngrok 사용법

### ngrok Public URL
- 서버를 시작하면 **Public URL**이 자동 생성됩니다
- 이 URL을 모바일 앱의 API 설정에 입력하세요
- 예: `https://abc123.ngrok.io`

### ngrok Dashboard
- http://localhost:4040 접속
- 실시간 요청/응답 모니터링 가능

### ngrok 무료 제한
- URL은 서버 재시작 시 매번 변경됨
- 유료 플랜 사용 시 고정 도메인 가능

## ⚙️ 설정

### GPU 사용
```bash
# CUDA 사용 가능 확인
python -c "import torch; print(torch.cuda.is_available())"
```

서버가 자동으로 GPU를 감지하여 사용합니다.

### 포트 변경
`src/server.py` 마지막 줄 수정:
```python
app.run(host='0.0.0.0', port=8080, debug=False)
```

ngrok 명령도 변경:
```bash
ngrok http 8080
```

## ⚠️ 문제 해결

### 1. ngrok 실행 오류
```
ERROR: authentication failed
```
**해결**:
```bash
ngrok authtoken YOUR_AUTH_TOKEN
```

### 2. 포트 충돌
```
OSError: [Errno 48] Address already in use
```
**해결**: 다른 포트 사용 또는 기존 프로세스 종료

### 3. 모델 로드 실패
```
FileNotFoundError: models/YOLO.pt not found
```
**해결**: `models/` 폴더에 `.pt` 파일 배치

### 4. CUDA 메모리 부족
```bash
# CPU 모드로 전환 (server.py 수정)
device = torch.device("cpu")
```

### 5. CORS 오류
Flask-CORS가 자동으로 처리합니다. 문제 발생 시:
```bash
pip install --upgrade flask-cors
```

## 📱 모바일 앱 연동

### React Native에서 사용
```javascript
// API 설정
const API_BASE_URL = 'https://abc123.ngrok.io';

// 이미지 분석
const analyzeImage = async (imageBase64) => {
  const response = await fetch(`${API_BASE_URL}/api/analyze/image`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ image: imageBase64 }),
  });
  return await response.json();
};

// 음성 분석
const analyzeAudio = async (audioBase64, sampleRate) => {
  const response = await fetch(`${API_BASE_URL}/api/analyze/audio`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
      audio: audioBase64,
      sample_rate: sampleRate 
    }),
  });
  return await response.json();
};
```

## 🚀 배포

### 로컬 개발
```bash
python start_server.py
```

### 클라우드 배포 (선택)
- **Heroku**: `Procfile` 추가
- **AWS EC2**: 인스턴스에서 직접 실행
- **Docker**: Dockerfile 생성

## 📊 성능

### 예상 응답 시간
- **이미지 분석** (GPU): ~200ms
- **이미지 분석** (CPU): ~1-2초
- **음성 분석** (GPU): ~100ms
- **음성 분석** (CPU): ~500ms
- **시나리오 판별**: ~10ms

### 동시 요청
- Flask는 기본적으로 단일 스레드
- 프로덕션 환경에서는 Gunicorn 사용 권장

## 📦 의존성

```txt
flask               # Web framework
flask-cors          # CORS support
torch               # PyTorch
ultralytics         # YOLO
librosa             # Audio processing
opencv-python       # Image processing
Pillow              # Image handling
pyngrok             # ngrok integration
requests            # HTTP client
```

## 🔗 참고 자료

- [Flask 공식 문서](https://flask.palletsprojects.com/)
- [ngrok 가이드](https://ngrok.com/docs)
- [REST API 설계](https://restfulapi.net/)

---

**🔙 [메인 README로 돌아가기](../README.md)**
