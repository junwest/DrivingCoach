# 🐳 Docker로 쉽게 시작하기

> **비전공자도 5분 안에 실행 가능!**

## 📋 준비사항

1. **Docker Desktop 설치** (한 번만 하면 됩니다)
   - Windows/Mac: https://www.docker.com/products/docker-desktop
   - 설치 후 Docker Desktop 실행 ✅

## 🚀 실행 방법 (3단계)

### 1️⃣ 프로젝트 다운로드
```bash
git clone https://github.com/junwest/DrivingCoach.git
cd DrivingCoach
```

### 2️⃣ 서버 자동 실행

**Windows**: `run_all.bat` 파일을 **더블 클릭**

**Mac/Linux**:
```bash
chmod +x run_all.sh
./run_all.sh
```

그게 전부입니다! ☕ 커피 한 잔 하는 동안 기다리면 서버가 시작됩니다.

### 3️⃣ 실행 확인

브라우저에서 접속:
- 백엔드: http://localhost:8080/swagger-ui/index.html
- AI 서버: http://localhost:5000/docs

✅ 화면이 보이면 성공!

---

## 📱 모바일 앱 연결

### 1. 내 컴퓨터 IP 주소 확인

**Windows**:
```cmd
ipconfig
```
→ `IPv4 주소`를 찾으세요 (예: 192.168.0.100)

**Mac/Linux**:
```bash
ifconfig | grep inet
```
→ `inet` 다음의 숫자를 찾으세요

### 2. 설정 파일 수정

`front/config.js` 파일을 열고:
```javascript
const API_HOST = '192.168.0.100';  // 👈 여기를 본인 IP로!
```

### 3. 앱 실행
```bash
cd front
npm install
npm start
```

---

## 🛑 서버 중지

```bash
docker-compose down
```

또는 Docker Desktop에서 중지 버튼 클릭

---

## 📊 상태 확인

### 실행 중인 컨테이너
```bash
docker-compose ps
```

### 로그 보기
```bash
# 전체 로그
docker-compose logs

# 실시간 로그
docker-compose logs -f

# 백엔드만
docker-compose logs backend

# AI 서버만
docker-compose logs ai-server
```

---

## ⚠️ 문제 해결

### Docker가 실행되지 않아요
→ Docker Desktop을 켜주세요

### 포트가 이미 사용 중이에요
```bash
# 기존 서버 중지
docker-compose down

# 또는 다른 포트 사용 (docker-compose.yml 수정)
ports:
  - "8081:8080"  # 8080 → 8081로 변경
```

### 빌드가 실패해요
```bash
# 캐시 없이 다시 빌드
docker-compose build --no-cache
docker-compose up -d
```

### 모든 것을 처음부터 다시 시작
```bash
docker-compose down -v  # 볼륨까지 삭제
docker-compose up --build
```

---

## 🎯 비전공자를 위한 체크리스트

- [ ] Docker Desktop 설치 완료
- [ ] Docker Desktop 실행 중
- [ ] `run_all.bat` (또는 `.sh`) 실행
- [ ] http://localhost:8080 접속 확인
- [ ] http://localhost:5000 접속 확인
- [ ] 내 IP 주소 확인 (ipconfig 또는 ifconfig)
- [ ] `front/config.js`에서 IP 수정
- [ ] 모바일 앱 실행 (npm start)

✅ 모두 체크되면 완료!

---

## 💡 장점

### Docker 사용 전
- ❌ Java 17 설치 필요
- ❌ Python 3.10 설치 필요
- ❌ Node.js 설치 필요
- ❌ 환경 변수 설정 필요
- ❌ 각 서버를 따로 실행

### Docker 사용 후
- ✅ Docker Desktop만 설치
- ✅ 한 번의 클릭으로 모든 서버 실행
- ✅ 환경 설정 자동화
- ✅ 팀원 모두 동일한 환경

---

## 🔗 상세 가이드

- 수동 설치: [model/SETUP_GUIDE.md](model/SETUP_GUIDE.md)
- 백엔드: [dev/README.md](dev/README.md)
- 프론트엔드: [front/README.md](front/README.md)

---

**어려운 점이 있나요?** 카카오톡으로 `run_all.bat` 파일을 공유하고 "이거 더블클릭!"이라고 알려주세요! 🎉
