# 🚗 DrivingCoach - AI 기반 운전 코칭 시스템

> 졸업과제 프로젝트: AI를 활용한 실시간 운전 습관 분석 및 피드백 시스템

## 📋 프로젝트 소개

**DrivingCoach**는 차량 블랙박스 영상과 음성을 실시간으로 분석하여 위험 운전 행동을 감지하고, 운전자에게 즉각적인 피드백을 제공하는 시스템입니다.

### 주요 기능
- 🎥 **영상 분석**: YOLO 기반 객체 인식 (보행자, 차량, 횡단보도 표지판)
- 🛣️ **차선 인식**: 딥러닝 기반 차선 변경 감지
- 🔊 **음성 분석**: CNN 기반 특수 소리 감지 (경적, 깜박이, 와이퍼)
- ⚠️ **위험 운전 감지**: 11가지 운전 시나리오 자동 판별
- 📱 **모바일 앱**: React Native 기반 실시간 운행 기록 및 피드백

## 🏗️ 시스템 아키텍처

```
DrivingCoach/
├── model/          # AI 모델 및 분석 엔진
├── dev/            # Spring Boot 백엔드 서버
└── front/          # React Native 모바일 앱
```

## 🚀 빠른 시작 가이드

### 🐳 가장 쉬운 방법: Docker (권장)

**비전공자도 5분 안에 실행!**

1. [Docker Desktop](https://www.docker.com/products/docker-desktop) 설치
2. 프로젝트 다운로드
3. **Windows**: `run_all.bat` 더블클릭 | **Mac**: `./run_all.sh` 실행

그게 전부입니다! ✨

상세 가이드: [**DOCKER_GUIDE.md**](DOCKER_GUIDE.md)

---

### 📚 수동 설치 (고급 사용자)

#### 1️⃣ AI 모델 실행
```bash
cd model
pip install -r requirements.txt
python src/main.py --videos Data/이벤트\ 4.mp4
```
상세 가이드: [model/README.md](model/README.md)

#### 2️⃣ 백엔드 서버 실행
```bash
cd dev
./gradlew bootRun
```
서버 주소: http://localhost:8080  
상세 가이드: [dev/README.md](dev/README.md)

#### 3️⃣ 프론트엔드 앱 실행
```bash
cd front
npm install
npm start
```
상세 가이드: [front/README.md](front/README.md)

## 🎯 감지 가능한 운전 시나리오

| ID | 시나리오 | 설명 |
|---|---|---|
| 4 | 차선 변경 후 방향지시등 미해제 | 차선 변경 완료 후 깜박이를 끄지 않음 |
| 5 | 방향지시등 없이 차선 변경 | 깜박이 없이 차선을 변경 |
| 7 | 악천후 전조등 미점등 | 와이퍼+비상등 감지 시 전조등 권장 |
| 8 | 우회전 보행자 구간 경적 | 보행자 없는데 경적 사용 |
| 9 | 보행자 근처 경적 | 보행자 위협 운전 |
| 10 | 급정거 중 경적 | 위협 운전 |
| 11 | 비상등 남용 | 비 오는 날 비상등 과다 사용 |

## 📁 프로젝트 구조

```
DrivingCoach/
├── model/                      # AI 모델 및 분석 엔진
│   ├── src/                   # 분석 파이프라인
│   │   ├── main.py           # 메인 실행 파일
│   │   ├── AudioCNN.py       # 음성 분석 모델
│   │   ├── lane_detect.py    # 차선 인식 모델
│   │   └── yolo.py           # 객체 인식
│   ├── models/               # 학습된 모델 가중치 (.pt 파일)
│   └── Data/                 # 입력 비디오
│
├── dev/                       # Spring Boot 백엔드
│   ├── src/main/java/        # Java 소스 코드
│   ├── src/main/resources/   # 설정 파일
│   │   ├── application.yml
│   │   ├── application-dev.yml
│   │   └── application-prod.yml
│   └── build.gradle          # 의존성 관리
│
├── front/                     # React Native 앱
│   ├── screens/              # 화면 컴포넌트
│   ├── navigation/           # 네비게이션 설정
│   ├── Driving/              # 운전 기록 기능
│   └── package.json          # npm 의존성
│
└── .gitignore                # Git 제외 파일 설정
```

## 🔧 개발 환경 설정

### AI 모델 개발
```bash
# Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
cd model
pip install torch torchvision ultralytics librosa opencv-python numpy
```

### 백엔드 개발
```bash
# Gradle 빌드
cd dev
./gradlew build

# 테스트 실행
./gradlew test
```

### 프론트엔드 개발
```bash
# Expo 개발 서버
cd front
npm install
npm start

# iOS 시뮬레이터
npm run ios

# Android 에뮬레이터
npm run android
```

## 📚 API 문서

백엔드 서버 실행 후 Swagger UI에서 확인:
- **로컬**: http://localhost:8080/swagger-ui/index.html
- **API Docs**: http://localhost:8080/v3/api-docs

## 🛠️ 기술 스택

### AI/ML
- **PyTorch**: 딥러닝 프레임워크
- **YOLO (Ultralytics)**: 객체 인식
- **U-Net**: 차선 세그멘테이션
- **CNN**: 음성 분류

### 백엔드
- **Spring Boot 3.3.3**: REST API 서버
- **Spring Security**: 인증/인가
- **JWT**: 토큰 기반 인증
- **MySQL / H2**: 데이터베이스
- **AWS S3**: 파일 저장소

### 프론트엔드
- **React Native**: 크로스 플랫폼 앱
- **Expo**: 개발 프레임워크
- **React Navigation**: 화면 네비게이션
- **Socket.IO**: 실시간 통신

## 🎓 교수님/평가자를 위한 가이드

### 1. 데모 영상 확인
`model/Outputs/` 폴더에서 분석 결과 영상 확인 가능

### 2. 로컬 실행 (권장)
각 폴더의 README.md 참고하여 순차 실행:
1. AI 모델 테스트 → `model/README.md`
2. 백엔드 서버 실행 → `dev/README.md`
3. 모바일 앱 실행 → `front/README.md`

### 3. 설정 파일
- 백엔드: `dev/src/main/resources/application.yml`
- 프론트엔드 환경변수: GitHub 저장소 설명 참고

## ⚠️ 문제 해결

### AI 모델 실행 오류
```bash
# CUDA 사용 불가 시
python src/main.py --device cpu

# 모델 파일 없음
# → models/ 폴더에 .pt 파일 확인 필요
```

### 백엔드 실행 오류
```bash
# Java 버전 확인
java -version  # Java 17 이상 필요

# 포트 충돌 시
# application.yml에서 server.port 변경
```

### 프론트엔드 실행 오류
```bash
# node_modules 재설치
rm -rf node_modules package-lock.json
npm install

# Expo 캐시 삭제
expo start -c
```

## 📊 프로젝트 성과

- ✅ 11가지 위험 운전 시나리오 자동 감지
- ✅ 실시간 영상/음성 분석 파이프라인 구축
- ✅ 풀스택 모바일 앱 개발
- ✅ RESTful API 설계 및 구현
- ✅ 딥러닝 모델 통합 (YOLO, U-Net, CNN)

## 👥 팀 정보

- **프로젝트명**: DrivingCoach
- **기간**: 2024년 졸업과제
- **저장소**: https://github.com/junwest/DrivingCoach

## 📝 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.

---

**📧 문의사항이 있으시면 GitHub Issues를 이용해주세요!**
