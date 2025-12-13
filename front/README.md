# 📱 DrivingCoach 프론트엔드 (React Native)

> Expo 기반 크로스 플랫폼 모바일 앱

## 📋 개요

DrivingCoach의 모바일 애플리케이션으로, 실시간 운행 기록, AI 피드백 조회, 운전 통계 확인 기능을 제공합니다.

## ⚡ 빠른 시작

### 필수 요구사항
- **Node.js 16 이상**
- **npm** 또는 **yarn**
- **Expo CLI**
- **(선택) iOS Simulator / Android Emulator**

### 설치 및 실행

#### 1️⃣ 의존성 설치
```bash
cd front
npm install
```

또는 yarn 사용:
```bash
yarn install
```

#### 2️⃣ Expo 개발 서버 실행
```bash
npm start
```

또는:
```bash
npx expo start
```

#### 3️⃣ 앱 실행

**QR 코드로 실행 (가장 간단)**:
1. 스마트폰에 **Expo Go** 앱 설치
   - [iOS App Store](https://apps.apple.com/app/expo-go/id982107779)
   - [Google Play Store](https://play.google.com/store/apps/details?id=host.exp.exponent)
2. 터미널에 표시된 QR 코드 스캔
3. 앱 자동 로드

**iOS 시뮬레이터**:
```bash
npm run ios
```

**Android 에뮬레이터**:
```bash
npm run android
```

## 🏗️ 프로젝트 구조

```
front/
├── screens/                     # 화면 컴포넌트
│   ├── HomeScreen.tsx          # 홈 화면
│   ├── DrivingScreen.tsx       # 운전 기록 화면
│   ├── RecordScreen.tsx        # 기록 조회
│   ├── MyPageScreen.tsx        # 마이페이지
│   └── SettingScreen.tsx       # 설정
│
├── navigation/                  # 네비게이션
│   ├── AppNavigator.tsx        # 메인 네비게이터
│   └── BottomTabNavigator.tsx  # 하단 탭 바
│
├── Driving/                     # 운전 관련 컴포넌트
│   ├── VideoRecorder.tsx       # 비디오 녹화
│   ├── AudioRecorder.tsx       # 음성 녹음
│   └── DrivingTimer.tsx        # 운전 타이머
│
├── Login/                       # 로그인 컴포넌트
├── HomeComponents/              # 홈 화면 컴포넌트
├── RecordScreenComponents/      # 기록 화면 컴포넌트
├── MyPageScreenComponents/      # 마이페이지 컴포넌트
├── SettingScreenComponents/     # 설정 화면 컴포넌트
│
├── auth/                        # 인증 관련
│   └── AuthContext.tsx         # JWT 토큰 관리
│
├── utils/                       # 유틸리티
│   └── api.ts                  # API 호출 함수
│
├── App.tsx                      # 앱 진입점
├── package.json                 # 의존성
└── app.json                     # Expo 설정
```

## 🔧 환경 설정

### API 서버 주소 설정

`utils/api.ts`에서 백엔드 서버 주소 설정:

```typescript
// 로컬 개발
const API_BASE_URL = 'http://localhost:8080/api';

// 실제 기기 테스트 (같은 Wi-Fi 네트워크)
const API_BASE_URL = 'http://192.168.0.100:8080/api';

// 운영 서버
const API_BASE_URL = 'https://api.drivingcoach.com/api';
```

### 개발 모드 vs 프로덕션 모드

**개발 모드** (기본):
```bash
npm start
```

**프로덕션 빌드**:
```bash
# Android APK
npx expo build:android

# iOS IPA
npx expo build:ios
```

## 📦 주요 의존성

| 패키지 | 용도 |
|---|---|
| expo | 개발 프레임워크 |
| react-navigation | 화면 네비게이션 |
| expo-camera | 카메라 접근 |
| expo-av | 오디오/비디오 재생 |
| socket.io-client | 실시간 통신 |
| @react-native-async-storage | 로컬 저장소 |
| expo-file-system | 파일 관리 |

## 📱 주요 화면

### 1. 홈 화면 (HomeScreen)
- 오늘의 운전 요약
- 최근 피드백
- 빠른 운행 시작

### 2. 운전 기록 화면 (DrivingScreen)
- 실시간 녹화
- 운행 타이머
- 긴급 정지 버튼

### 3. 기록 조회 (RecordScreen)
- 과거 운행 기록
- AI 피드백 조회
- 통계 차트

### 4. 마이페이지 (MyPageScreen)
- 프로필 관리
- 운전 통계
- 배지 시스템

### 5. 설정 (SettingScreen)
- 알림 설정
- 테마 변경
- 로그아웃

## 🔐 인증 흐름

### 로그인
```typescript
// Login.tsx
const handleLogin = async (username: string, password: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const { token } = await response.json();
  await AsyncStorage.setItem('authToken', token);
};
```

### API 요청 시 토큰 사용
```typescript
const token = await AsyncStorage.getItem('authToken');
const response = await fetch(`${API_BASE_URL}/driving/records`, {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
});
```

## 🎨 UI/UX 가이드

### 색상 테마
```javascript
const colors = {
  primary: '#007AFF',    // 메인 블루
  danger: '#FF3B30',     // 위험/경고
  success: '#34C759',    // 성공
  warning: '#FF9500',    // 주의
  background: '#F2F2F7', // 배경
  text: '#000000',       // 텍스트
};
```

### 폰트 사이즈
```javascript
const fontSizes = {
  small: 12,
  medium: 16,
  large: 20,
  xlarge: 24,
};
```

## 🧪 테스트

### 컴포넌트 테스트
```bash
npm test
```

### E2E 테스트 (Detox)
```bash
# iOS
npm run test:e2e:ios

# Android
npm run test:e2e:android
```

## 📷 카메라 권한 설정

### iOS (app.json)
```json
{
  "expo": {
    "ios": {
      "infoPlist": {
        "NSCameraUsageDescription": "운행 기록을 위해 카메라 권한이 필요합니다.",
        "NSMicrophoneUsageDescription": "음성 분석을 위해 마이크 권한이 필요합니다."
      }
    }
  }
}
```

### Android (app.json)
```json
{
  "expo": {
    "android": {
      "permissions": [
        "CAMERA",
        "RECORD_AUDIO",
        "READ_EXTERNAL_STORAGE",
        "WRITE_EXTERNAL_STORAGE"
      ]
    }
  }
}
```

## ⚠️ 문제 해결

### 1. Metro Bundler 오류
```bash
# 캐시 삭제
npx expo start -c

# node_modules 재설치
rm -rf node_modules package-lock.json
npm install
```

### 2. iOS 빌드 오류
```bash
# CocoaPods 재설치
cd ios
pod install
cd ..
```

### 3. Android 에뮬레이터 연결 안 됨
```bash
# ADB 재시작
adb kill-server
adb start-server

# 연결된 기기 확인
adb devices
```

### 4. Expo Go에서 앱이 로드 안 됨
- 스마트폰과 컴퓨터가 **같은 Wi-Fi 네트워크**에 연결되어 있는지 확인
- 방화벽 설정 확인
- Expo CLI 재시작

### 5. 카메라 권한 오류
```bash
# Expo 프로젝트 재빌드
npx expo prebuild --clean
```

## 🚀 배포 가이드

### Android APK 빌드
```bash
# EAS Build 사용
npx eas build --platform android --profile production

# 로컬 빌드
npx expo build:android
```

### iOS IPA 빌드
```bash
# Apple Developer 계정 필요
npx eas build --platform ios --profile production
```

### 앱 스토어 제출
```bash
# Android Play Store
npx eas submit --platform android

# iOS App Store
npx eas submit --platform ios
```

## 📊 성능 최적화

### 이미지 최적화
- `expo-image` 사용
- 캐싱 전략 적용
- 적절한 이미지 크기 사용

### 번들 크기 줄이기
```bash
# 사용하지 않는 의존성 제거
npm prune

# 번들 분석
npx expo export --dump-sourcemap
```

### 메모리 관리
- 큰 비디오 파일 스트리밍 처리
- 컴포넌트 언마운트 시 리스너 정리
- `useMemo`, `useCallback` 활용

## 🔗 유용한 링크

- [Expo 공식 문서](https://docs.expo.dev/)
- [React Native 가이드](https://reactnative.dev/docs/getting-started)
- [React Navigation](https://reactnavigation.org/)
- [Expo Camera](https://docs.expo.dev/versions/latest/sdk/camera/)

## 📝 개발 팁

### Hot Reload
코드 수정 시 자동 새로고침:
- **Expo Go**: 기본 활성화
- **수동 새로고침**: 앱에서 흔들기 → Reload

### 디버깅
```bash
# React Native Debugger
brew install --cask react-native-debugger

# Chrome DevTools
# Expo 앱에서 흔들기 → "Debug Remote JS"
```

### VS Code 확장 프로그램
- React Native Tools
- ESLint
- Prettier
- React Native Snippet

---

**🔙 [메인 README로 돌아가기](../README.md)**
