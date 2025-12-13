# 🤖 DrivingCoach AI Server 실행 가이드

> **타인도 쉽게 따라할 수 있는 단계별 매뉴얼**

## 📋 목차
1. [준비사항 확인](#1-준비사항-확인)
2. [Python 설치 및 확인](#2-python-설치-및-확인)
3. [프로젝트 다운로드](#3-프로젝트-다운로드)
4. [가상환경 설정](#4-가상환경-설정)
5. [의존성 설치](#5-의존성-설치)
6. [ngrok 설정](#6-ngrok-설정)
7. [서버 실행](#7-서버-실행)
8. [API 테스트](#8-api-테스트)
9. [문제 해결](#9-문제-해결)

---

## 1. 준비사항 확인

### 필수 요구사항
- ✅ **Python 3.8 이상** (Python 3.10 권장)
- ✅ **인터넷 연결**
- ✅ **약 2GB 디스크 공간** (모델 파일 + 의존성)

### 선택 사항
- GPU 사용 시: NVIDIA GPU + CUDA 11.8+

---

## 2. Python 설치 및 확인

### 2-1. Python 버전 확인
터미널을 열고 다음 명령어 실행:

```bash
python --version
```

**예상 출력**:
```
Python 3.10.x
```

### 2-2. Python 없는 경우 설치

**Mac**:
```bash
# Homebrew 사용
brew install python@3.10
```

**Windows**:
1. https://www.python.org/downloads/ 접속
2. Python 3.10.x 다운로드
3. 설치 시 "Add Python to PATH" 체크 ☑️

**Linux (Ubuntu)**:
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip
```

---

## 3. 프로젝트 다운로드

### 3-1. Git으로 클론
```bash
git clone https://github.com/junwest/DrivingCoach.git
cd DrivingCoach/model
```

### 3-2. 또는 ZIP 다운로드
1. https://github.com/junwest/DrivingCoach 접속
2. 초록색 "Code" 버튼 → "Download ZIP"
3. 압축 해제 후 `model` 폴더로 이동

---

## 4. 가상환경 설정

### 4-1. 가상환경 생성
```bash
# model 폴더에서 실행
python -m venv venv
```

**실행 결과**: `venv` 폴더가 생성됨

### 4-2. 가상환경 활성화

**Mac/Linux**:
```bash
source venv/bin/activate
```

**Windows (CMD)**:
```cmd
venv\Scripts\activate
```

**Windows (PowerShell)**:
```powershell
venv\Scripts\Activate.ps1
```

**성공 확인**: 터미널 앞에 `(venv)` 표시됨
```
(venv) user@computer:~/model$
```

---

## 5. 의존성 설치

### 5-1. pip 업그레이드
```bash
pip install --upgrade pip
```

### 5-2. 패키지 설치
```bash
pip install -r requirements.txt
```

**예상 시간**: 5-10분 (네트워크 속도에 따라 다름)

### 5-3. 설치 확인
```bash
pip list
```

**확인할 패키지**:
- `fastapi`
- `uvicorn`
- `torch`
- `ultralytics`
- `librosa`

---

## 6. ngrok 설정

### 6-1. ngrok 설치

**Mac**:
```bash
brew install ngrok
```

**Windows/Linux**:
1. https://ngrok.com/download 접속
2. OS에 맞는 버전 다운로드
3. 압축 해제 후 PATH에 추가

### 6-2. ngrok 계정 생성
1. https://dashboard.ngrok.com/signup 가입
2. 무료 플랜 선택

### 6-3. ngrok 인증
1. https://dashboard.ngrok.com/get-started/your-authtoken 접속
2. 토큰 복사
3. 터미널에서 실행:

```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

**예시**:
```bash
ngrok config add-authtoken 2abc123def456ghi789jkl
```

### 6-4. ngrok 설치 확인
```bash
ngrok --version
```

---

## 7. 서버 실행

### 7-1. 모델 파일 확인 (선택)
`models/` 폴더에 다음 파일이 있는지 확인:
- `YOLO.pt`
- `lane_detect.pt`
- `AudioCNN.pt`

> **없어도 됨**: 테스트만 하려면 모델 없이도 서버 실행 가능

### 7-2. 서버 시작

**ngrok 자동 실행 (권장)**:
```bash
python start_server.py
```

**또는 서버만 실행**:
```bash
python -m uvicorn src.server:app --host 0.0.0.0 --port 5000
```

### 7-3. 성공 확인

다음과 같은 출력이 나오면 성공:

```
============================================================
🚗 DrivingCoach FastAPI Server with ngrok
============================================================

1️⃣ Starting FastAPI server with uvicorn...
   ✅ Server is running!

2️⃣ Starting ngrok tunnel...

✅ Server is running!
============================================================
📍 Local URL:  http://localhost:5000
🌐 Public URL: https://abc123.ngrok.io
============================================================

📱 Use the Public URL in your mobile app!

📚 API Documentation:
  Swagger UI: https://abc123.ngrok.io/docs
  ReDoc:      https://abc123.ngrok.io/redoc
```

> **중요**: `https://abc123.ngrok.io` 같은 Public URL을 복사해두세요!

### 7-4. API 문서 확인
브라우저에서 접속:
- **Swagger UI**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc

---

## 8. API 테스트

### 8-1. 브라우저에서 테스트
1. http://localhost:5000/docs 접속
2. `GET /` 클릭 → "Try it out" 버튼 → "Execute"
3. 응답 확인:
```json
{
  "service": "DrivingCoach AI Server",
  "status": "running",
  "device": "cpu",
  "models": {
    "yolo": false,
    "lane": false,
    "audio": false
  }
}
```

### 8-2. 터미널에서 테스트

**새 터미널 창 열고**:
```bash
cd DrivingCoach/model
source venv/bin/activate  # 가상환경 활성화
python test_api.py
```

**예상 출력**:
```
🧪 DrivingCoach API Test Suite
============================================================
Testing server at: http://localhost:5000
============================================================

1️⃣ Testing Health Check
============================================================
Status: 200
Response: {
  "service": "DrivingCoach AI Server",
  "status": "running"
}

...

📊 Test Results Summary
============================================================
Health Check              ✅ PASS
Image Analysis            ✅ PASS
Audio Analysis            ✅ PASS
Scenario Analysis         ✅ PASS
============================================================
Total: 4/4 tests passed

🎉 All tests passed!
```

### 8-3. cURL로 테스트
```bash
curl http://localhost:5000/
```

---

## 9. 문제 해결

### 문제 1: Python 버전 오류
```
SyntaxError: invalid syntax
```

**해결**:
```bash
python --version  # 3.8 이상인지 확인
python3 --version  # python3 사용
```

### 문제 2: pip 명령어 없음
```
command not found: pip
```

**해결**:
```bash
# Mac/Linux
python -m pip install --upgrade pip

# Windows
python -m pip install --upgrade pip
```

### 문제 3: 가상환경 활성화 안 됨 (Windows PowerShell)
```
cannot be loaded because running scripts is disabled
```

**해결**:
```powershell
# PowerShell을 관리자 권한으로 실행
Set-ExecutionPolicy RemoteSigned
```

### 문제 4: ngrok 인증 실패
```
ERROR: authentication failed
```

**해결**:
1. https://dashboard.ngrok.com/get-started/your-authtoken 재확인
2. 토큰 다시 설정:
```bash
ngrok config add-authtoken YOUR_NEW_TOKEN
```

### 문제 5: 포트 이미 사용 중
```
OSError: [Errno 48] Address already in use
```

**해결**:
```bash
# Mac/Linux: 포트 5000 사용 프로세스 종료
lsof -ti:5000 | xargs kill -9

# Windows: 포트 5000 사용 프로세스 찾기
netstat -ano | findstr :5000
# 해당 PID 종료
taskkill /PID <PID번호> /F
```

### 문제 6: 모델 로드 실패
```
FileNotFoundError: models/YOLO.pt not found
```

**해결**:
- 모델 파일이 없어도 서버는 실행됩니다
- API 테스트는 가능하지만 실제 분석은 불가
- 모델 파일 필요 시 별도 제공

### 문제 7: CUDA 오류 (GPU)
```
CUDA error: no kernel image is available
```

**해결**:
1. CPU 모드로 전환 (자동):
   - 서버가 자동으로 CPU 사용
2. 또는 PyTorch 재설치:
```bash
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 문제 8: 패키지 충돌
```
ERROR: pip's dependency resolver does not currently take into account all the packages
```

**해결**:
```bash
# 가상환경 삭제 후 재생성
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🎉 완료!

서버가 정상적으로 실행되면:

### 로컬 환경에서 사용
- Swagger UI: http://localhost:5000/docs 에서 API 테스트

### 모바일 앱에서 사용
- ngrok Public URL (`https://xxx.ngrok.io`)을 앱 설정에 입력
- 앱에서 이 URL로 API 호출

### 서버 중지
터미널에서 `Ctrl + C` 누르기

---

## 📱 다음 단계

1. **모바일 앱 연동**: `front/` 폴더의 README 참고
2. **백엔드 연동**: `dev/` 폴더의 README 참고
3. **커스터마이징**: `src/server.py` 수정

---

## 🔗 도움말 링크

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [ngrok 가이드](https://ngrok.com/docs)
- [GitHub 저장소](https://github.com/junwest/DrivingCoach)

---

**문제가 있나요?** GitHub Issues에 질문을 남겨주세요!
