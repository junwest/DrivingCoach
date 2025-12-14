# 🚗 DrivingCoach - AI 운전 코칭 시스템

> **졸업 과제 프로젝트** | AI로 운전 습관을 분석하고 피드백을 제공하는 시스템

[![GitHub](https://img.shields.io/badge/GitHub-DrivingCoach-blue)](https://github.com/junwest/DrivingCoach)

---

## 🌐 라이브 데모 사이트

**✨ 지금 바로 체험해보세요!**

- **데모 URL**: https://c5666e306007.ngrok-free.app
- **로그인 정보**:
  - 아이디: `1234`
  - 비밀번호: `12345678`

> **📱 배포 방식 안내**  
> 본 앱은 원래 **Android 에뮬레이터**에서 실행되도록 개발되었으나, 실제 주행 영상 촬영이 불가능하여 **웹 버전으로 배포**하였습니다. 주행 중 실시간 AI 판별 등 자세한 기능은 **발표 영상** 및 **보고서**를 참고해주시기 바랍니다.

> **⚠️ 중요**: 이 데모 사이트는 개발자의 노트북이 켜져있을 때만 작동합니다.

---

## 📺 바로 보기

아래 3단계만 따라하면 프로젝트를 바로 실행할 수 있습니다!

### ⚡ 빠른 시작 (3단계)

#### 1단계: Docker Desktop 설치 (5분 소요)

**Docker가 뭔가요?** 
- 프로그램을 자동으로 실행해주는 도구입니다
- Java, Python 등을 하나하나 설치할 필요가 없습니다

**설치 방법:**
1. https://www.docker.com/products/docker-desktop 접속
2. 본인 컴퓨터에 맞는 버전 다운로드
   - Windows: "Download for Windows" 클릭
   - Mac (M1/M2): "Download for Mac with Apple silicon" 클릭
   - Mac (Intel): "Download for Mac with Intel chip" 클릭
3. 다운로드된 파일 실행하고 설치
4. **Docker Desktop 앱을 실행** (아주 중요!)
   - 맥: 런치패드 → Docker 아이콘
   - 윈도우: 시작 메뉴 → Docker Desktop

✅ Docker Desktop 앱이 열리면 준비 완료!

---

#### 2단계: 프로젝트 다운로드 (1분 소요)

**방법 A: ZIP 다운로드 (추천 - 더 쉬움)**
1. 이 페이지 위쪽 초록색 "Code" 버튼 클릭
2. "Download ZIP" 클릭
3. 다운로드된 ZIP 파일 압축 해제
4. 압축 푼 폴더 열기

**방법 B: Git 사용 (Git이 설치되어 있다면)**
```bash
git clone https://github.com/junwest/DrivingCoach.git
cd DrivingCoach
```

---

#### 3단계: 실행하기 (30초 소요)

압축 푼 폴더에서:

**Windows 사용자:**
1. `run_all.bat` 파일 찾기
2. **더블 클릭** (그게 전부입니다!)

**Mac 사용자:**
1. 터미널 열기 (Cmd + Space → "터미널" 검색)
2. 다음 명령어 입력:
```bash
cd DrivingCoach폴더경로  # 폴더를 터미널에 드래그하면 경로가 자동입력됩니다
./run_all.sh
```

---

### 🎉 실행 완료!

서버가 시작되면 브라우저를 열고 이 주소들로 접속하세요:

| 무엇을 볼까요? | 주소 | 설명 |
|---|---|---|
| 🌐 **앱 화면 (로컬)** | http://localhost:8081 | 실제 애플리케이션 (웹 버전) |
| 🚀 **앱 화면 (배포)** | [Vercel 배포 가이드](DEPLOYMENT.md) | 인터넷 URL로 접근 가능 |
| 📚 AI API 문서 | http://localhost:5001/docs | AI 분석 기능 테스트 |
| 📊 백엔드 API | http://localhost:8080/swagger-ui/index.html | 서버 API 테스트 |

> **처음이신가요?** 먼저 http://localhost:8081 로 접속해서 앱을 확인해보세요!
> 
> **외부에서 접속하려면?** [Vercel 배포 가이드](DEPLOYMENT.md)를 참고하세요.

---

## 🤔 문제가 생겼나요?

### "Docker가 실행되지 않습니다"
→ Docker Desktop 앱이 실행 중인지 확인하세요 (상단 메뉴바나 시스템 트레이에 고래 아이콘이 보여야 함)

### "포트가 이미 사용 중입니다"
→ 터미널에서 실행:
```bash
docker-compose down
```
그리고 다시 `run_all.bat` 또는 `run_all.sh` 실행

### "주소에 접속이 안 돼요"
→ 서버가 시작되는 데 1-2분 정도 걸릴 수 있습니다. 조금 기다린 후 새로고침하세요.

### 그래도 안 되나요?
→ GitHub Issues에 질문을 남겨주세요: https://github.com/junwest/DrivingCoach/issues

---

## 📱 모바일 앱도 실행하고 싶다면?

### 준비물
- 스마트폰
- Expo Go 앱 설치
  - [iOS App Store](https://apps.apple.com/app/expo-go/id982107779)
  - [Google Play](https://play.google.com/store/apps/details?id=host.exp.exponent)

### 실행 방법
1. 터미널에서:
```bash
cd front
npm install
npm start
```

2. QR 코드가 나타나면 Expo Go 앱으로 스캔

---

## 🎯 프로젝트 소개

### 이게 무엇인가요?

DrivingCoach는 **AI를 이용해 운전 습관을 분석**하는 시스템입니다.

**주요 기능:**
- 🎥 블랙박스 영상 분석 (YOLO AI 사용)
- 🛣️ 차선 변경 감지 (딥러닝)
- 🔊 소리 분석 (경적, 깜박이, 와이퍼)
- ⚠️ 위험 운전 자동 감지 (11가지 시나리오)
- 📱 모바일 앱으로 기록 확인

### 어떤 위험 운전을 감지하나요?

| 번호 | 감지 내용 |
|---|---|
| 4 | 차선 변경 후 깜박이를 끄지 않음 |
| 5 | 깜박이 없이 차선 변경 |
| 7 | 비 오는데 전조등 미점등 |
| 8 | 우회전 시 불필요한 경적 |
| 9 | 보행자 근처에서 경적 |
| 10 | 급정거 중 경적 (위협 운전) |
| 11 | 비상등 남용 |

---

## 🏗️ 시스템 아키텍처

### 전체 구조

```mermaid
graph TB
    subgraph "클라이언트"
        Mobile["📱 모바일 앱<br/>(React Native + Expo)"]
        Web["🌐 웹 앱<br/>(React Native Web)"]
    end
    
    subgraph "백엔드 서버<br/>(포트 8080)"
        API["🔧 REST API<br/>(Spring Boot)"]
        WS["🔌 WebSocket<br/>(실시간 통신)"]
        DB[("💾 데이터베이스<br/>(H2/MySQL)")]
    end
    
    subgraph "AI 분석 서버<br/>(포트 5001)"
        FastAPI["⚡ FastAPI<br/>(비동기)"]
        YOLO["🎯 YOLO<br/>(객체 감지)"]
        UNet["🛣️ U-Net<br/>(차선 감지)"]
        AudioCNN["🔊 AudioCNN<br/>(소리 분석)"]
    end
    
    subgraph "저장소"
        S3["☁️ AWS S3<br/>(영상 저장)"]
    end
    
    Mobile --> API
    Web --> API
    Mobile -.WebSocket.-> WS
    Web -.WebSocket.-> WS
    
    API --> DB
    WS --> DB
    WS -- "영상 업로드" --> S3
    WS -- "AI 분석 요청" --> FastAPI
    
    FastAPI --> YOLO
    FastAPI --> UNet
    FastAPI --> AudioCNN
    FastAPI -- "분석 결과" --> WS
    
    style Mobile fill:#e1f5ff
    style Web fill:#e1f5ff
    style API fill:#fff3e0
    style WS fill:#fff3e0
    style FastAPI fill:#f3e5f5
    style S3 fill:#e8f5e9
```

### 데이터 흐름

```mermaid
sequenceDiagram
    participant U as 👤 사용자
    participant M as 📱 모바일/웹
    participant B as 🔧 백엔드
    participant A as 🤖 AI 서버
    participant S as ☁️ S3
    
    U->>M: 주행 시작
    M->>B: WebSocket 연결
    B-->>M: 연결 확인 + RecordID
    
    loop 2초마다
        M->>M: 영상 녹화 (2초)
        M->>B: 영상 전송 (WS)
        B->>S: 영상 저장
        B->>A: AI 분석 요청
        A->>A: YOLO + Lane + Audio 분석
        A-->>B: 분석 결과
        B-->>M: 실시간 피드백 (TTS)
    end
    
    U->>M: 주행 종료
    M->>B: 종료 신호
    B->>B: 데이터 저장
    B-->>M: 완료 확인
```

### 배포 아키텍처

```mermaid
graph LR
    subgraph "Docker Compose"
        subgraph "Backend Container"
            SB[Spring Boot<br/>:8080]
        end
        
        subgraph "AI Container"
            FA[FastAPI<br/>:5001]
        end
        
        SB <--> FA
    end
    
    User[👤 사용자] --> SB
    User --> FA
    
    subgraph "로컬 개발"
        FE[React Native<br/>:8081<br/>npm run web]
    end
    
    FE --> SB
    FE --> FA
    
    style SB fill:#ff9800
    style FA fill:#9c27b0
    style FE fill:#2196f3
```

### 기술 스택 상세

| 계층 | 기술 | 역할 |
|---|---|---|
| **프론트엔드** | React Native + Expo | 크로스 플랫폼 모바일/웹 앱 |
| **백엔드** | Spring Boot 3.3 + JWT | RESTful API, 인증, WebSocket |
| **AI 서버** | FastAPI + Uvicorn | 비동기 AI 모델 서빙 |
| **AI 모델** | YOLO v8, U-Net, CNN | 객체/차선/소리 분석 |
| **데이터베이스** | H2 (개발), MySQL (프로덕션) | 사용자 및 주행 기록 |
| **스토리지** | AWS S3 | 영상 파일 저장 |
| **배포** | Docker + Docker Compose | 컨테이너 오케스트레이션 |

---

## 💻 기술 스택 (참고용)

궁금하신 분들을 위해:

- **AI/ML**: PyTorch, YOLO, U-Net, CNN
- **백엔드**: Spring Boot, FastAPI
- **프론트엔드**: React Native (Expo)
- **데이터베이스**: MySQL / H2
- **배포**: Docker, Docker Compose

---

## 📂 프로젝트 구조

```
DrivingCoach/
├── 🐳 run_all.bat        # Windows에서 더블클릭하면 실행
├── 🐳 run_all.sh          # Mac/Linux 실행 스크립트
├── 📖 README.md           # 이 파일
├── 📖 DOCKER_GUIDE.md     # Docker 상세 가이드
│
├── dev/                   # 백엔드 (Spring Boot)
├── model/                 # AI 서버 (FastAPI)
└── front/                 # 모바일/웹 앱 (React Native)
```

---

## 🔧 서버 제어 명령어

### 서버 중지
```bash
docker-compose down
```

### 서버 재시작
```bash
docker-compose restart
```

### 로그 확인
```bash
docker-compose logs -f
```

### 완전히 처음부터 다시
```bash
docker-compose down -v
docker-compose up --build
```

---

## 📚 더 자세한 가이드

각 폴더별로 상세한 README가 있습니다:

- [Docker 상세 가이드](DOCKER_GUIDE.md) - Docker 사용법
- [백엔드 가이드](dev/README.md) - Spring Boot 서버
- [AI 서버 가이드](model/README.md) - FastAPI 서버
- [프론트엔드 가이드](front/README.md) - React Native 앱
- [AI 모델 설치 가이드](model/SETUP_GUIDE.md) - 수동 설치 방법

---

## 🎓 교수님/평가자를 위한 가이드

### 빠른 데모 확인
1. Docker Desktop 실행
2. `run_all.bat` (Windows) 또는 `./run_all.sh` (Mac) 실행
3. http://localhost:8081 접속 → 앱 확인
4. http://localhost:5001/docs 접속 → AI API 테스트

### 예상 소요 시간
- Docker 설치: 5분
- 첫 실행 (이미지 빌드): 5-10분
- 이후 실행: 30초

### 시스템 요구사항
- **OS**: Windows 10+, macOS 10.15+, Linux
- **메모리**: 최소 4GB RAM (권장 8GB)
- **디스크**: 약 5GB 여유 공간
- **Docker Desktop**: 최신 버전

---

## 🏆 프로젝트 성과

- ✅ AI 기반 실시간 운전 분석
- ✅ 11가지 위험 운전 시나리오 자동 감지
- ✅ 풀스택 모바일 애플리케이션
- ✅ Docker를 통한 원클릭 배포
- ✅ 완벽한 문서화


---

## 📄 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

---

## 💬 질문이 있으신가요?

- 🐛 버그 제보: [GitHub Issues](https://github.com/junwest/DrivingCoach/issues)
- 💡 기능 제안: [GitHub Issues](https://github.com/junwest/DrivingCoach/issues)
- 📧 문의: GitHub Issues를 이용해주세요

---

<div align="center">

**⭐ 이 프로젝트가 도움이 되셨다면 Star를 눌러주세요! ⭐**

Made with ❤️ by DrivingCoach Team

</div>
