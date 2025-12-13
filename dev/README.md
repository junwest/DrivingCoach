# 🖥️ DrivingCoach 백엔드 (Spring Boot)

> Spring Boot 3.3.3 기반 RESTful API 서버

## 📋 개요

이 백엔드는 DrivingCoach 모바일 앱의 API 서버로, 사용자 인증, 운행 기록 관리, 피드백 저장 등의 기능을 제공합니다.

## ⚡ 빠른 시작

### 필수 요구사항
- **Java 17 이상**
- **Gradle 7.x** (Gradle Wrapper 포함)
- **MySQL 8.x** (운영 환경) 또는 **H2** (개발 환경)

### 로컬 실행 방법

#### 1️⃣ Java 버전 확인
```bash
java -version
# Java 17 이상이어야 함
```

#### 2️⃣ 프로젝트 빌드
```bash
cd dev
./gradlew build
```

Windows에서는:
```cmd
gradlew.bat build
```

#### 3️⃣ 서버 실행
```bash
./gradlew bootRun
```

서버가 실행되면:
- **서버 주소**: http://localhost:8080
- **Swagger UI**: http://localhost:8080/swagger-ui/index.html
- **API Docs**: http://localhost:8080/v3/api-docs

## 🔧 설정 파일

### application.yml 구조

```
src/main/resources/
├── application.yml          # 기본 설정
├── application-dev.yml      # 개발 환경 (H2 DB)
└── application-prod.yml     # 운영 환경 (MySQL)
```

### 개발 환경 (H2 사용)
```bash
./gradlew bootRun --args='--spring.profiles.active=dev'
```

- **H2 콘솔**: http://localhost:8080/h2-console
- **JDBC URL**: `jdbc:h2:mem:testdb`
- **Username**: `sa`
- **Password**: (비워둠)

### 운영 환경 (MySQL 사용)
```bash
./gradlew bootRun --args='--spring.profiles.active=prod'
```

**MySQL 설정 필요**:
1. MySQL 서버 설치 및 실행
2. 데이터베이스 생성:
```sql
CREATE DATABASE drivingcoach CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. `application-prod.yml`에서 DB 정보 설정:
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/drivingcoach
    username: root
    password: your_password
```

## 📦 주요 의존성

| 기술 | 용도 |
|---|---|
| Spring Boot Web | REST API |
| Spring Security | 인증/인가 |
| Spring Data JPA | 데이터베이스 ORM |
| JWT (jjwt 0.12.x) | 토큰 기반 인증 |
| MySQL / H2 | 데이터베이스 |
| AWS SDK v2 | S3 파일 저장소 |
| Springdoc OpenAPI | Swagger UI |
| Lombok | 보일러플레이트 코드 감소 |

## 🗂️ 프로젝트 구조

```
dev/
├── src/main/java/com/drivingcoach/backend/
│   ├── domain/
│   │   ├── driving/          # 운행 기록 도메인
│   │   ├── user/             # 사용자 도메인
│   │   └── feedback/         # 피드백 도메인
│   ├── global/
│   │   ├── config/           # 설정 클래스
│   │   ├── security/         # Security 설정
│   │   └── common/           # 공통 유틸
│   └── BackendApplication.java
│
├── src/main/resources/
│   ├── application.yml
│   ├── application-dev.yml
│   └── application-prod.yml
│
└── build.gradle              # Gradle 빌드 설정
```

## 🔐 보안 설정

### JWT 토큰 발급
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "test",
  "password": "password"
}
```

**응답**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiresIn": 3600
}
```

### 인증이 필요한 API 호출
```http
GET /api/driving/records
Authorization: Bearer {token}
```

## 🧪 테스트

### 단위 테스트 실행
```bash
./gradlew test
```

### 빌드 + 테스트
```bash
./gradlew clean build
```

테스트 결과는 `build/reports/tests/test/index.html`에서 확인 가능

## 📡 주요 API 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|---|---|---|
| POST | /api/auth/login | 로그인 |
| POST | /api/auth/register | 회원가입 |
| GET | /api/driving/records | 운행 기록 조회 |
| POST | /api/driving/start | 운행 시작 |
| POST | /api/driving/end | 운행 종료 |
| GET | /api/feedback/{id} | 피드백 조회 |

전체 API 문서: http://localhost:8080/swagger-ui/index.html

## 🛠️ 개발 도구

### IntelliJ IDEA 설정
1. `File` → `Open` → `dev` 폴더 선택
2. Gradle 프로젝트로 인식되면 자동 빌드
3. `BackendApplication.java` 우클릭 → `Run`

### VS Code 설정
1. Extension Pack for Java 설치
2. Spring Boot Extension Pack 설치
3. `Ctrl+Shift+P` → `Spring Boot Dashboard` 실행

## 🐳 Docker 실행 (선택)

### Docker 이미지 빌드
```bash
docker build -t drivingcoach-backend .
```

### 컨테이너 실행
```bash
docker run -p 8080:8080 drivingcoach-backend
```

## ⚠️ 문제 해결

### 1. Java 버전 오류
```
ERROR: JAVA_HOME is not set
```
**해결**: Java 17 설치 및 JAVA_HOME 환경변수 설정

### 2. Gradle 권한 오류 (Mac/Linux)
```bash
chmod +x gradlew
```

### 3. 포트 충돌
`application.yml`에서 포트 변경:
```yaml
server:
  port: 8081
```

### 4. MySQL 연결 오류
- MySQL 서버 실행 확인: `sudo service mysql status`
- DB 이름/사용자명/비밀번호 확인
- 방화벽 설정 확인

### 5. H2 콘솔 접근 불가
`application-dev.yml` 확인:
```yaml
spring:
  h2:
    console:
      enabled: true
      path: /h2-console
```

## 📊 성능 모니터링

### Actuator 엔드포인트
- **Health Check**: http://localhost:8080/actuator/health
- **Metrics**: http://localhost:8080/actuator/metrics
- **Environment**: http://localhost:8080/actuator/env

## 🚀 배포 가이드

### JAR 파일 생성
```bash
./gradlew bootJar
```

생성된 JAR: `build/libs/backend-0.0.1-SNAPSHOT.jar`

### 서버 실행
```bash
java -jar build/libs/backend-0.0.1-SNAPSHOT.jar --spring.profiles.active=prod
```

## 📝 추가 자료

- [Spring Boot 공식 문서](https://spring.io/projects/spring-boot)
- [Spring Security 가이드](https://spring.io/guides/topicals/spring-security-architecture)
- [JWT 토큰 설명](https://jwt.io/)

---

**🔙 [메인 README로 돌아가기](../README.md)**
