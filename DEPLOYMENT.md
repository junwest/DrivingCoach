# 🌐 DrivingCoach Vercel 배포 가이드

## 📋 목차

1. [준비 사항](#준비-사항)
2. [ngrok 설정](#ngrok-설정)
3. [Vercel 배포](#vercel-배포)
4. [환경 변수 설정](#환경-변수-설정)
5. [테스트](#테스트)
6. [문제 해결](#문제-해결)

---

## 준비 사항

### 1. 필요한 계정
- ✅ [Vercel 계정](https://vercel.com/signup) (무료)
- ✅ [ngrok 계정](https://ngrok.com/signup) (무료)
- ✅ GitHub 계정 (이미 있음)

### 2. 설치 필요
- Vercel CLI (선택사항)
- ngrok CLI (필수)

---

## ngrok 설정

### Step 1: ngrok 설치

**Mac:**
```bash
brew install ngrok
```

**Windows:**
1. https://ngrok.com/download 접속
2. Windows 버전 다운로드
3. 압축 해제 후 PATH에 추가 또는 프로젝트 폴더에 복사

### Step 2: ngrok 인증

1. https://dashboard.ngrok.com/get-started/your-authtoken 접속
2. Auth Token 복사
3. `ngrok.yml` 파일 열기
4. `YOUR_NGROK_AUTH_TOKEN` 부분을 복사한 토큰으로 교체

```yaml
version: "2"
authtoken: 2abc123def456...  # 👈 여기에 실제 토큰 붙여넣기
tunnels:
  backend:
    proto: http
    addr: 8080
  ai-server:
    proto: http
    addr: 5001
```

### Step 3: ngrok 테스트

```bash
# Docker 서버 먼저 시작
docker compose up -d

# ngrok 터널 시작
./start-ngrok.sh  # Mac/Linux
# 또는
start-ngrok.bat   # Windows
```

**성공하면 다음과 같은 화면이 나옵니다:**
```
Region        Asia Pacific (ap)
Forwarding    https://abc123.ngrok.io -> http://localhost:8080
Forwarding    https://def456.ngrok.io -> http://localhost:5001
```

**⚠️ 중요**: 
- `https://abc123.ngrok.io` ← 백엔드 URL (메모하세요!)
- `https://def456.ngrok.io` ← AI 서버 URL (메모하세요!)
- ngrok은 종료하지 말고 **계속 실행 중** 유지하세요

---

## Vercel 배포

### 방법 1: Vercel 웹사이트에서 배포 (추천)

1. https://vercel.com 접속 및 로그인

2. **"Add New Project"** 클릭

3. **"Import Git Repository"** 클릭

4. **DrivingCoach 저장소 선택**
   - GitHub에서 저장소 import

5. **프로젝트 설정**
   - **Framework Preset**: Other
   - **Root Directory**: `front` (중요!)
   - **Build Command**: `expo export:web`
   - **Output Directory**: `dist`

6. **Environment Variables 추가** (Step 4 참조)

7. **Deploy** 클릭!

### 방법 2: Vercel CLI로 배포

```bash
# Vercel CLI 설치
npm i -g vercel

# 프론트엔드 폴더로 이동
cd front

# 배포
vercel --prod
```

---

## 환경 변수 설정

Vercel 프로젝트 설정에서 환경 변수를 추가하세요:

### Vercel Dashboard에서:

1. 프로젝트 → **Settings** → **Environment Variables**

2. 다음 변수들 추가:

| Name | Value | 설명 |
|---|---|---|
| `REACT_APP_BACKEND_URL` | `https://abc123.ngrok.io/api` | ngrok 백엔드 URL + /api |
| `REACT_APP_AI_SERVER_URL` | `https://def456.ngrok.io` | ngrok AI 서버 URL |

**⚠️ 중요**: 
- ngrok URL은 **실행할 때마다 바뀝니다**!
- ngrok 무료 플랜은 URL이 변경되므로, 매번 Vercel 환경 변수를 업데이트해야 합니다
- ngrok Pro ($8/월)를 사용하면 고정 URL 사용 가능

3. **Redeploy** 클릭하여 환경 변수 적용

---

## 테스트

### 1. 로컬 Docker 서버 시작

```bash
docker compose up -d
```

### 2. ngrok 터널 시작

```bash
./start-ngrok.sh  # Mac
# 또는
start-ngrok.bat   # Windows
```

### 3. ngrok URL 복사

터미널에서 표시된 URL 복사:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:8080
Forwarding    https://def456.ngrok.io -> http://localhost:5001
```

### 4. Vercel 환경 변수 업데이트

1. Vercel Dashboard → Settings → Environment Variables
2. `REACT_APP_BACKEND_URL` 값 업데이트: `https://abc123.ngrok.io/api`
3. `REACT_APP_AI_SERVER_URL` 값 업데이트: `https://def456.ngrok.io`
4. **Deployments** → 최신 배포 → **"Redeploy"**

### 5. Vercel URL 접속

https://drivingcoach.vercel.app (실제 URL은 다를 수 있음)

### 6. 기능 테스트

1. 로그인
2. 주행 시작 클릭
3. 타이머 작동 확인
4. 주행 종료

---

## 문제 해결

### "백엔드에 연결할 수 없습니다"

**확인사항**:
1. ✅ Docker 서버가 실행 중인지: `docker compose ps`
2. ✅ ngrok이 실행 중인지: 터미널 확인
3. ✅ Vercel 환경 변수가 올바른지
4. ✅ ngrok URL이 최신인지 (재시작 시 변경됨)

### ngrok URL이 자주 바뀌는 문제

**해결책**:
- **옵션 1**: ngrok URL이 바뀔 때마다 Vercel 환경 변수 업데이트
- **옵션 2**: ngrok Pro 구독 ($8/월) - 고정 URL 사용
- **옵션 3**: 클라우드 서버 사용 (Railway, Render 등)

### Vercel 빌드 실패

**확인사항**:
1. Root Directory가 `front`로 설정되었는지
2. Build Command가 `expo export:web`인지
3. Output Directory가 `dist`인지

**로그 확인**:
```bash
cd front
npm run build  # 로컬에서 빌드 테스트
```

### WebSocket 연결 안됨

`config.js`에서 WebSocket URL 확인:
- HTTP ngrok URL → `wss://` 로 자동 변환되는지 확인
- 환경 변수가 올바른지 확인

---

## 💡 프로 팁

### ngrok 무료 플랜 한계점

- ✅ 동시 터널 2개까지 지원
- ⚠️ 세션당 8시간 제한
- ⚠️ URL이 재시작 시마다 변경
- ⚠️ 월 트래픽 제한 있음

### 비용 절감 방법

1. **개발/테스트 시에만 ngrok 실행**
   - 필요할 때만 Docker + ngrok 시작
   - Vercel 환경 변수만 업데이트

2. **ngrok 대신 Cloudflare Tunnel**
   - 무료 고정 URL 제공
   - 설정이 약간 복잡함

3. **프로덕션은 클라우드 호스팅**
   - Railway: $5/월부터
   - Render: 무료 플랜 있음 (슬립 모드)

---

## 🚀 운영 워크플로우

### 일상적인 사용

```bash
# 1. Docker 시작
docker compose up -d

# 2. ngrok 시작
./start-ngrok.sh

# 3. ngrok URL 확인 및 메모

# 4. (URL이 바뀌었다면) Vercel 환경 변수 업데이트

# 5. Vercel 앱 접속 및 사용

# 6. 종료 시
# - Ctrl+C (ngrok 종료)
# - docker compose down
```

### ngrok URL 고정하기 (Pro 플랜)

```yaml
# ngrok.yml
version: "2"
authtoken: YOUR_TOKEN
tunnels:
  backend:
    proto: http
    addr: 8080
    domain: myapp-backend.ngrok.io  # 고정 도메인
  ai-server:
    proto: http
    addr: 5001
    domain: myapp-ai.ngrok.io       # 고정 도메인
```

---

## 📞 지원

문제가 있나요?
- 🐛 [GitHub Issues](https://github.com/junwest/DrivingCoach/issues)
- 📧 GitHub Issues를 통해 문의하세요

---

**축하합니다! 🎉** 

이제 인터넷 어디서든 DrivingCoach에 접속할 수 있습니다!
